"""Re-encrypt every BountyProfile.anthropic_api_key under the primary KEK.

Use this during a rotation window to drain ciphertext written under an
older key (or under the pre-0.25.0 SECRET_KEY-derived KEK) into the
current ``KEEL_ENCRYPTION_KEYS`` primary.

Rotation procedure
------------------

1. Generate a new key::

       python -c "from keel.security.encryption import generate_key; print(generate_key())"

2. Set ``KEEL_ENCRYPTION_KEYS=<NEW>,<OLD>`` (new key first). Redeploy.
   Reads work under either key; new writes use ``<NEW>``.

   For the FIRST rotation (off the SECRET_KEY-derived KEK), set
   ``KEEL_ENCRYPTION_LEGACY_SECRET_KEY_FALLBACK=true`` instead of listing
   an ``<OLD>`` — the keel.security.encryption fallback flag re-creates
   the legacy KEK on the fly for decrypt-only.

3. Run this command::

       python manage.py rotate_anthropic_keys

4. Drop the old key (or unset the legacy fallback) and redeploy.

The command is idempotent — rows already under the primary key are no-ops
because ``MultiFernet.rotate`` recognizes that case. Failures are logged
per-row and do not abort the run; the final summary reports the count.
"""

from django.core.management.base import BaseCommand

from cryptography.fernet import InvalidToken

from core.models import BountyProfile
from keel.security import encryption


class Command(BaseCommand):
    help = 'Re-encrypt every BountyProfile.anthropic_api_key under the primary KEEL_ENCRYPTION_KEYS.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report counts without writing.',
        )

    def handle(self, *args, **opts):
        dry_run = opts['dry_run']
        rotated = 0
        unchanged = 0
        failed = 0

        qs = BountyProfile.objects.exclude(anthropic_api_key='').only('id', 'user_id', 'anthropic_api_key')
        total = qs.count()
        self.stdout.write(f'Scanning {total} profile(s) with encrypted api_key…')

        for profile in qs.iterator():
            old = profile.anthropic_api_key
            try:
                new = encryption.rotate(old)
            except InvalidToken:
                failed += 1
                self.stderr.write(self.style.WARNING(
                    f'  user={profile.user_id}: ciphertext is not under any '
                    'configured key. Set KEEL_ENCRYPTION_LEGACY_SECRET_KEY_FALLBACK=true '
                    'or add the missing key to KEEL_ENCRYPTION_KEYS and re-run.'
                ))
                continue
            if new == old:
                unchanged += 1
                continue
            if not dry_run:
                BountyProfile.objects.filter(pk=profile.pk).update(anthropic_api_key=new)
            rotated += 1

        verb = 'would rotate' if dry_run else 'rotated'
        self.stdout.write(self.style.SUCCESS(
            f'{verb}: {rotated}; already under primary: {unchanged}; failed: {failed}; total: {total}'
        ))
        if failed and not dry_run:
            self.stderr.write(self.style.ERROR(
                f'{failed} row(s) could not be rotated — see warnings above.'
            ))
