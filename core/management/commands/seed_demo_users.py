"""Seed demo users for Bounty.

Creates one KeelUser + ProductAccess per DEMO_ROLES entry with username=role
so Keel's demo_login_view can sign them in. Demo users have unusable
passwords; the only entry path is the one-click `demo_login_view` buttons
at `/demo-login/`. See keel CLAUDE.md → "Demo authentication — passwordless
contract" for the full rationale.

Usage:
    python manage.py seed_demo_users
    python manage.py seed_demo_users --dry-run
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import BountyProfile
from keel.accounts.models import ProductAccess

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed Bounty demo users for one-click login.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        roles = getattr(settings, 'DEMO_ROLES', ['admin'])
        product = getattr(settings, 'KEEL_PRODUCT_NAME', 'bounty').lower()

        for role in roles:
            display = role.replace('_', ' ').title()
            is_admin = role == 'admin'

            if dry_run:
                self.stdout.write(f'  Would create: {role} ({display})')
                continue

            user, created = User.objects.get_or_create(
                username=role,
                defaults={
                    'email': f'{role}@docklabs.ai',
                    'first_name': 'Demo',
                    'last_name': display,
                    'is_staff': is_admin,
                    'is_superuser': is_admin,
                },
            )
            user.set_unusable_password()
            user.save()

            # Create or update ProductAccess
            ProductAccess.objects.update_or_create(
                user=user, product=product,
                defaults={'role': role, 'is_active': True},
            )

            BountyProfile.objects.get_or_create(
                user=user,
                defaults={'organization_name': 'Demo Agency'},
            )

            action = 'Created' if created else 'Updated'
            self.stdout.write(self.style.SUCCESS(f'  {action}: {role} ({display})'))

        self.stdout.write(self.style.SUCCESS('Done.'))
