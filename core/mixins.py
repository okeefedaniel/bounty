"""Permission mixins for Bounty role-based access control."""
from urllib.parse import quote

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models.expressions import BaseExpression


# Bounty role tiers. ``agency_admin`` is the customer-side admin: same
# operational powers as ``admin`` here (Bounty has no IT-only surface
# inside the product), but won't be able to grant other admin-tier roles
# in Keel. Pinning the role lists in module-level frozensets keeps every
# permission gate reading from one source of truth.
ADMIN_ROLES = frozenset({'admin', 'agency_admin'})
COORDINATOR_ROLES = ADMIN_ROLES | frozenset({'coordinator'})
ANALYST_ROLES = COORDINATOR_ROLES | frozenset({'analyst'})


class CoordinatorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restrict view to coordinators and admins."""

    def test_func(self):
        role = getattr(self.request.user, 'role', '')
        return role in COORDINATOR_ROLES


class AnalystRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restrict view to analysts, coordinators, and admins."""

    def test_func(self):
        role = getattr(self.request.user, 'role', '')
        return role in ANALYST_ROLES


class SortableListMixin:
    """Server-side column sorting for ListViews."""

    sortable_fields = {}
    default_sort = ''
    default_dir = 'asc'

    def get_sort_params(self):
        sort = self.request.GET.get('sort', self.default_sort)
        direction = self.request.GET.get('dir', self.default_dir)
        if sort not in self.sortable_fields:
            sort = self.default_sort
        if direction not in ('asc', 'desc'):
            direction = self.default_dir
        return sort, direction

    def apply_sorting(self, qs):
        sort, direction = self.get_sort_params()
        if not sort:
            return qs
        field = self.sortable_fields[sort]
        if isinstance(field, BaseExpression):
            alias = f'_sort_{sort}'
            qs = qs.annotate(**{alias: field})
            order_field = alias
        else:
            order_field = field
        if direction == 'desc':
            order_field = f'-{order_field}'
        return qs.order_by(order_field)

    def get_queryset(self):
        return self.apply_sorting(super().get_queryset())

    def _build_params(self, exclude):
        parts = []
        for key in self.request.GET:
            if key not in exclude:
                for val in self.request.GET.getlist(key):
                    parts.append(f'{quote(key)}={quote(val)}')
        return '&'.join(parts)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        sort, direction = self.get_sort_params()
        ctx['current_sort'] = sort
        ctx['current_dir'] = direction
        ctx['filter_params'] = self._build_params({'sort', 'dir', 'page'})
        ctx['pagination_params'] = self._build_params({'page'})
        return ctx
