"""
Send digest emails to users with new AI matches since their last digest.

Usage:
    python manage.py send_digest              # sends both daily and weekly
    python manage.py send_digest --daily      # daily digests only
    python manage.py send_digest --weekly     # weekly digests only
    python manage.py send_digest --dry-run    # preview without sending
    python manage.py send_digest --user jdoe  # single user
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.notifications import build_absolute_url
from matching.models import MatchPreference, OpportunityMatch

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send digest emails summarising new AI matches'

    def add_arguments(self, parser):
        parser.add_argument('--daily', action='store_true', help='Send daily digests only')
        parser.add_argument('--weekly', action='store_true', help='Send weekly digests only')
        parser.add_argument('--user', type=str, help='Send digest to a specific user only')
        parser.add_argument('--dry-run', action='store_true', help='Preview without sending')

    def handle(self, *args, **options):
        daily_only = options['daily']
        weekly_only = options['weekly']
        username = options.get('user')
        dry_run = options['dry_run']

        now = timezone.now()

        # Determine which frequencies to process
        frequencies = []
        if not daily_only and not weekly_only:
            frequencies = ['daily', 'weekly']
        else:
            if daily_only:
                frequencies.append('daily')
            if weekly_only:
                frequencies.append('weekly')

        prefs = MatchPreference.objects.filter(
            is_active=True,
            digest_frequency__in=frequencies,
        ).select_related('user').exclude(
            user__email='',
        )

        if username:
            prefs = prefs.filter(user__username=username)

        if not prefs.exists():
            self.stdout.write(self.style.WARNING('No users eligible for digest.'))
            return

        total_sent = 0
        total_skipped = 0

        for pref in prefs:
            user = pref.user

            if not user.email:
                self.stdout.write(f'  {user.username}: no email, skipping')
                total_skipped += 1
                continue

            # Determine the cutoff: since last digest, or fallback to frequency window
            if pref.last_digest_at:
                cutoff = pref.last_digest_at
            elif pref.digest_frequency == 'daily':
                cutoff = now - timedelta(days=1)
            else:
                cutoff = now - timedelta(weeks=1)

            # Check if it's too early to send again
            if pref.last_digest_at:
                if pref.digest_frequency == 'daily' and (now - pref.last_digest_at) < timedelta(hours=20):
                    self.stdout.write(f'  {user.username}: daily digest sent recently, skipping')
                    total_skipped += 1
                    continue
                if pref.digest_frequency == 'weekly' and (now - pref.last_digest_at) < timedelta(days=6):
                    self.stdout.write(f'  {user.username}: weekly digest sent recently, skipping')
                    total_skipped += 1
                    continue

            # Fetch new matches since cutoff
            matches = list(
                OpportunityMatch.objects.filter(
                    user=user,
                    created_at__gte=cutoff,
                ).exclude(
                    status=OpportunityMatch.Status.DISMISSED,
                ).select_related(
                    'federal_opportunity',
                ).order_by('-relevance_score')[:20]
            )

            if not matches:
                self.stdout.write(f'  {user.username}: no new matches since {cutoff:%Y-%m-%d %H:%M}')
                total_skipped += 1
                continue

            self.stdout.write(f'  {user.username}: {len(matches)} new matches')

            if dry_run:
                self.stdout.write(self.style.WARNING('    [DRY RUN] Would send digest'))
                continue

            # Send via Keel notify
            from django.urls import reverse
            recommendations_path = reverse('matching:recommendations')
            recommendations_url = build_absolute_url(recommendations_path)

            from keel.notifications import notify
            notify(
                event='grant_digest',
                recipients=[user],
                title=f'Bounty Digest: {len(matches)} New Matches',
                message=f'You have {len(matches)} new AI-matched grant opportunities.',
                link=recommendations_path,
                priority='low',
                channels=['email'],
                context={
                    'user': user,
                    'matches': matches,
                    'count': len(matches),
                    'frequency': pref.digest_frequency,
                    'recommendations_url': recommendations_url,
                },
            )

            pref.last_digest_at = now
            pref.save(update_fields=['last_digest_at'])
            total_sent += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nDone: {total_sent} digests sent, {total_skipped} skipped'
        ))
