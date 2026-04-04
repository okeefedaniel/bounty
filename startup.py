#!/usr/bin/env python
"""
Startup script for Railway deployment.
"""
import os
import subprocess
import sys
import time

# Force unbuffered output
os.environ['PYTHONUNBUFFERED'] = '1'


def log(msg):
    print(f"[startup] {msg}", flush=True)


def run(cmd, fatal=False):
    """Run a command, streaming output. Returns True on success."""
    log(f"Running: {cmd}")
    try:
        result = subprocess.run(
            cmd, shell=True,
            stdout=sys.stdout, stderr=sys.stderr,
        )
        if result.returncode != 0:
            log(f"Command exited with code {result.returncode}: {cmd}")
            if fatal:
                sys.exit(result.returncode)
            return False
        return True
    except Exception as e:
        log(f"Command failed with exception: {e}")
        if fatal:
            sys.exit(1)
        return False


def main():
    log("=" * 50)
    log("Bounty container starting")
    log("=" * 50)

    # Diagnostics
    port = os.environ.get('PORT', 'NOT SET')
    raw_db_url = os.environ.get('DATABASE_URL', '')
    if raw_db_url:
        if '://' in raw_db_url:
            scheme = raw_db_url.split('://')[0]
            db_url = f"SET ({scheme}://******, len={len(raw_db_url)})"
        else:
            db_url = f"SET but NO SCHEME (first 30 chars: {repr(raw_db_url[:30])})"
    else:
        db_url = 'NOT SET (empty)'
    secret = 'SET' if os.environ.get('DJANGO_SECRET_KEY') else 'NOT SET'
    log(f"PORT = {port}")
    log(f"DATABASE_URL = {db_url}")
    log(f"DJANGO_SECRET_KEY = {secret}")
    log(f"Python: {sys.executable} {sys.version}")

    manage_cmd = f"{sys.executable} manage.py"

    # Test that Django settings can be imported
    log("Testing Django settings import...")
    try:
        import django
        django.setup()
        log("Django settings loaded successfully")
    except Exception as e:
        log(f"ERROR: Django settings failed to load: {e}")
        import traceback
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()

    # Collect static files
    log("=== Collecting static files ===")
    run(f"{manage_cmd} collectstatic --noinput")

    # Start gunicorn EARLY so healthcheck passes
    if port == 'NOT SET':
        port = '8080'
        log(f"WARNING: PORT not set, defaulting to {port}")

    gunicorn_cmd = (
        f"gunicorn bounty.wsgi "
        f"--bind 0.0.0.0:{port} "
        f"--workers 2 "
        f"--access-logfile - "
        f"--error-logfile - "
        f"--timeout 120"
    )
    log(f"=== Starting gunicorn on port {port} ===")
    gunicorn_proc = subprocess.Popen(
        gunicorn_cmd, shell=True,
        stdout=sys.stdout, stderr=sys.stderr,
    )
    log(f"Gunicorn started (PID {gunicorn_proc.pid})")

    # Wait a moment for gunicorn to bind
    time.sleep(3)

    # Check if gunicorn is still running
    if gunicorn_proc.poll() is not None:
        log(f"ERROR: Gunicorn exited with code {gunicorn_proc.returncode}")
        import json
        from http.server import BaseHTTPRequestHandler, HTTPServer

        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'error',
                    'message': 'Gunicorn failed to start. Check logs.',
                }).encode())

        server = HTTPServer(('0.0.0.0', int(port)), HealthHandler)
        log(f"Fallback health server listening on port {port}")
        server.serve_forever()
        return

    # Run migrations
    log("=== Running migrations ===")
    # Fix InconsistentMigrationHistory if needed (one-time, idempotent)
    run(f"{manage_cmd} fix_migration_history")
    run(f"{manage_cmd} migrate --fake-initial --noinput")

    # Post-migration tasks
    log("=== Running background startup tasks ===")

    # Bootstrap superuser from env vars (idempotent, always resets password)
    if os.environ.get('CREATE_SUPERUSER', '').lower() in ('true', '1', 'yes'):
        run(f"{manage_cmd} ensure_superuser")

    # Demo mode: seed demo users
    if os.environ.get('DEMO_MODE', '').lower() in ('true', '1', 'yes'):
        run(f"{manage_cmd} seed_demo_users")
    if os.environ.get('SEED_ON_DEPLOY', '').lower() in ('true', '1', 'yes'):
        run(f"{manage_cmd} shell < seed_data.py")
    run(f"{manage_cmd} sync_federal_grants --limit 100")
    log("=== Background tasks complete ===")

    # Start background scheduler for periodic tasks (digest emails, grant sync)
    import threading

    def _scheduler():
        """Run periodic tasks in a loop. Each command handles its own throttling."""
        interval = int(os.environ.get('SCHEDULER_INTERVAL_SECONDS', 3600))  # default 1 hour
        match_interval = int(os.environ.get('MATCH_INTERVAL_HOURS', 24))  # default once daily
        cycles_per_match = max(1, match_interval * 3600 // interval)
        cycle = 0
        log(f"Scheduler started (interval={interval}s, match every {match_interval}h)")
        while True:
            time.sleep(interval)
            cycle += 1
            log("=== Scheduler: running periodic tasks ===")
            run(f"{manage_cmd} send_digest")
            run(f"{manage_cmd} sync_federal_grants --limit 100")
            # AI matching is expensive — only run on the configured interval
            if cycle % cycles_per_match == 0:
                log("=== Scheduler: running AI matching ===")
                run(f"{manage_cmd} match_opportunities")
            log("=== Scheduler: periodic tasks complete ===")

    scheduler_thread = threading.Thread(target=_scheduler, daemon=True, name='scheduler')
    scheduler_thread.start()

    log("=== Startup complete, waiting for gunicorn ===")
    gunicorn_proc.wait()
    log(f"Gunicorn exited with code {gunicorn_proc.returncode}")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        time.sleep(30)
        sys.exit(1)
