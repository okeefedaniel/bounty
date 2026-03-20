"""
Run AI matching for all users with active preferences.

Usage:
    python manage.py match_opportunities
    python manage.py match_opportunities --user jdoe
    python manage.py match_opportunities --dry-run
"""
import logging

from django.core.management.base import BaseCommand

from matching.matching import run_matching_for_user
from matching.models import MatchPreference

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run AI matching for users with active match preferences'

    def add_arguments(self, parser):
        parser.add_argument('--user', type=str, help='Match a specific user only')
        parser.add_argument('--dry-run', action='store_true', help='Print without saving')

    def handle(self, *args, **options):
        username = options.get('user')
        dry_run = options['dry_run']

        prefs = MatchPreference.objects.filter(is_active=True).select_related('user')
        if username:
            prefs = prefs.filter(user__username=username)

        if not prefs.exists():
            self.stdout.write(self.style.WARNING('No active preferences found.'))
            return

        total_scored = total_stored = total_notified = 0

        for pref in prefs:
            user = pref.user
            self.stdout.write(f'\nMatching for {user.username}...')

            if dry_run:
                self.stdout.write(self.style.WARNING('  [DRY RUN] Would score opportunities'))
                continue

            result = run_matching_for_user(user)
            total_scored += result['scored']
            total_stored += result['stored']
            total_notified += result['notified']

            self.stdout.write(
                f"  Scored: {result['scored']}, "
                f"Stored: {result['stored']}, "
                f"Notified: {result['notified']}"
            )

        self.stdout.write(self.style.SUCCESS(
            f'\nDone: {total_scored} scored, {total_stored} stored, {total_notified} notified'
        ))
