"""Seed demo users for Bounty.

Creates one user per DEMO_ROLES entry with username=role so Keel's
demo_login_view can authenticate them.

Usage:
    python manage.py seed_demo_users
    python manage.py seed_demo_users --dry-run
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import User

DEMO_PASSWORD = os.environ.get('DEMO_PASSWORD', 'demo2026!')


class Command(BaseCommand):
    help = 'Seed Bounty demo users for one-click login.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        roles = getattr(settings, 'DEMO_ROLES', ['admin'])

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
                    'role': role,
                    'is_staff': is_admin,
                    'is_superuser': is_admin,
                },
            )
            user.set_password(DEMO_PASSWORD)
            user.save()

            action = 'Created' if created else 'Updated'
            self.stdout.write(self.style.SUCCESS(f'  {action}: {role} ({display})'))

        self.stdout.write(self.style.SUCCESS('Done.'))
