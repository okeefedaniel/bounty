from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView

from matching.models import OpportunityMatch
from opportunities.models import FederalOpportunity, TrackedOpportunity


class DashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard for all Bounty users — tracked opportunities, deadlines, AI matches."""

    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        cutoff = timezone.now().date() + timedelta(days=14)

        # Open federal opportunities
        context['open_federal'] = FederalOpportunity.objects.filter(
            opportunity_status=FederalOpportunity.OpportunityStatus.POSTED,
        ).count()

        # Tracked opportunities (all users)
        tracked_qs = TrackedOpportunity.objects.filter(tracked_by=user)
        context['tracked_count'] = tracked_qs.count()
        context['tracked_opportunities'] = tracked_qs.select_related(
            'federal_opportunity',
        ).order_by('-updated_at')[:10]
        context['approaching_deadlines'] = tracked_qs.filter(
            federal_opportunity__close_date__lte=cutoff,
            federal_opportunity__close_date__gte=timezone.now().date(),
        ).select_related('federal_opportunity').order_by(
            'federal_opportunity__close_date',
        )[:5]

        # Recent federal opportunities
        context['recent_federal'] = FederalOpportunity.objects.filter(
            opportunity_status=FederalOpportunity.OpportunityStatus.POSTED,
        ).order_by('-synced_at')[:5]

        # AI matches
        context['recommended_matches'] = OpportunityMatch.objects.filter(
            user=user,
        ).exclude(
            status=OpportunityMatch.Status.DISMISSED,
        ).order_by('-relevance_score')[:5]
        context['new_match_count'] = OpportunityMatch.objects.filter(
            user=user, status=OpportunityMatch.Status.NEW,
        ).count()
        context['has_ai_access'] = user.has_ai_access

        return context
