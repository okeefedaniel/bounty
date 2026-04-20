from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView

import logging

from matching.models import OpportunityMatch
from opportunities.models import FederalOpportunity, TrackedOpportunity

logger = logging.getLogger(__name__)


def _safe(fn, default, label):
    try:
        return fn()
    except Exception:
        logger.exception('Bounty dashboard: %s failed, returning default', label)
        return default


class DashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard for all Bounty users — tracked opportunities, deadlines, AI matches."""

    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        cutoff = timezone.now().date() + timedelta(days=14)

        context['open_federal'] = _safe(
            lambda: FederalOpportunity.objects.filter(
                opportunity_status=FederalOpportunity.OpportunityStatus.POSTED,
            ).count(),
            0, 'open_federal',
        )

        tracked_qs = TrackedOpportunity.objects.filter(tracked_by=user)
        context['tracked_count'] = _safe(tracked_qs.count, 0, 'tracked_count')
        context['tracked_opportunities'] = _safe(
            lambda: list(tracked_qs.select_related('federal_opportunity').order_by('-updated_at')[:10]),
            [], 'tracked_opportunities',
        )
        context['approaching_deadlines'] = _safe(
            lambda: list(tracked_qs.filter(
                federal_opportunity__close_date__lte=cutoff,
                federal_opportunity__close_date__gte=timezone.now().date(),
            ).select_related('federal_opportunity').order_by(
                'federal_opportunity__close_date',
            )[:5]),
            [], 'approaching_deadlines',
        )

        context['recent_federal'] = _safe(
            lambda: list(FederalOpportunity.objects.filter(
                opportunity_status=FederalOpportunity.OpportunityStatus.POSTED,
            ).order_by('-synced_at')[:5]),
            [], 'recent_federal',
        )

        context['recommended_matches'] = _safe(
            lambda: list(OpportunityMatch.objects.filter(user=user).exclude(
                status=OpportunityMatch.Status.DISMISSED,
            ).order_by('-relevance_score')[:5]),
            [], 'recommended_matches',
        )
        context['new_match_count'] = _safe(
            lambda: OpportunityMatch.objects.filter(
                user=user, status=OpportunityMatch.Status.NEW,
            ).count(),
            0, 'new_match_count',
        )

        def _ai_access():
            from core.models import get_bounty_profile
            return get_bounty_profile(user).has_ai_access

        context['has_ai_access'] = _safe(_ai_access, False, 'has_ai_access')

        return context
