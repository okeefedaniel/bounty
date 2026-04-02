"""Backfill or refresh search vectors for all federal opportunities."""
from django.core.management.base import BaseCommand

from opportunities.search import GrantSearchEngine


class Command(BaseCommand):
    help = 'Update search vectors for all federal opportunities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--missing-only',
            action='store_true',
            help='Only update records with NULL search_vector',
        )

    def handle(self, *args, **options):
        engine = GrantSearchEngine()

        if options['missing_only']:
            qs = engine.model.objects.filter(search_vector__isnull=True)
            count = engine.update_search_vectors(queryset=qs)
        else:
            count = engine.update_search_vectors()

        self.stdout.write(self.style.SUCCESS(f'Updated {count} search vectors'))
