"""Federal grant search engine — powered by keel.search."""
from keel.search.engine import SearchEngine

from .models import FederalOpportunity


class GrantSearchEngine(SearchEngine):
    """PostgreSQL FTS search for federal grant opportunities."""

    model = FederalOpportunity
    search_fields = {
        'title': 'A',
        'agency_name': 'B',
        'description': 'C',
    }
    trigram_fields = ['title', 'agency_name']
    instant_display_fields = [
        'title', 'agency_name', 'opportunity_number',
        'opportunity_status', 'close_date',
        'award_floor', 'award_ceiling',
    ]

    def get_prefix_match(self, query, filter_clause, filter_params, limit):
        """Match opportunity numbers (e.g., 'PD-25', 'NOFO-', '26-503')."""
        q = query.strip().upper()
        # Detect opportunity number patterns (contains digits + dashes)
        has_digits = any(c.isdigit() for c in q)
        has_dash = '-' in q
        if not (has_digits and has_dash) and not q.startswith(('PD', 'NOFO', 'HHS', 'EPA')):
            return None

        table = self.model._meta.db_table
        sql = f"""
            SELECT id, title, agency_name, opportunity_number,
                   opportunity_status, close_date, award_floor, award_ceiling
            FROM {table}
            WHERE opportunity_number ILIKE %s
            {filter_clause}
            ORDER BY close_date DESC NULLS LAST
            LIMIT %s
        """
        prefix = query.strip() + '%'
        params = [prefix] + filter_params + [limit]
        return self._execute_instant(sql, params)

    def format_instant_result(self, row):
        """Format for typeahead: agency, title, funding, status."""
        close = row.get('close_date')
        floor = row.get('award_floor')
        ceiling = row.get('award_ceiling')

        funding = ''
        if floor and ceiling:
            funding = f"${float(floor):,.0f} - ${float(ceiling):,.0f}"
        elif ceiling:
            funding = f"Up to ${float(ceiling):,.0f}"

        return {
            'id': row['id'],
            'title': (row.get('title') or '')[:120],
            'agency': row.get('agency_name') or '',
            'opp_number': row.get('opportunity_number') or '',
            'status': (row.get('opportunity_status') or '').capitalize(),
            'close_date': str(close) if close else '',
            'funding': funding,
            'url': f"/opportunities/{row['id']}/",
        }

    def get_filter_kwargs(self, filters):
        """Map URL params to Django queryset kwargs."""
        kwargs = {}
        if filters.get('agency'):
            kwargs['agency_name'] = filters['agency']
        if filters.get('status'):
            kwargs['opportunity_status'] = filters['status']
        return kwargs
