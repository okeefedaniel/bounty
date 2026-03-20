from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView

from opportunities.models import FederalOpportunity, TrackedOpportunity


class DashboardView(LoginRequiredMixin, TemplateView):
    """Role-based dashboard for Bounty users."""

    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Open federal opportunities
        context['open_federal'] = FederalOpportunity.objects.filter(
            opportunity_status=FederalOpportunity.OpportunityStatus.POSTED,
        ).count()

        if user.is_coordinator:
            context.update(self._coordinator_context(user))
        else:
            context.update(self._viewer_context(user))

        return context

    def _coordinator_context(self, user):
        from datetime import timedelta
        from django.db.models import Sum
        from matching.models import OpportunityMatch

        tracked_qs = TrackedOpportunity.objects.filter(tracked_by=user)
        cutoff = timezone.now().date() + timedelta(days=14)

        return {
            'tracked_count': tracked_qs.count(),
            'tracked_opportunities': tracked_qs.select_related(
                'federal_opportunity',
            ).order_by('-updated_at')[:10],
            'recent_federal': FederalOpportunity.objects.filter(
                opportunity_status=FederalOpportunity.OpportunityStatus.POSTED,
            ).order_by('-synced_at')[:5],
            'approaching_deadlines': tracked_qs.filter(
                federal_opportunity__close_date__lte=cutoff,
                federal_opportunity__close_date__gte=timezone.now().date(),
            ).select_related('federal_opportunity').order_by(
                'federal_opportunity__close_date',
            )[:5],
            'recommended_matches': OpportunityMatch.objects.filter(
                user=user,
            ).exclude(
                status=OpportunityMatch.Status.DISMISSED,
            ).order_by('-relevance_score')[:5],
            'new_match_count': OpportunityMatch.objects.filter(
                user=user, status=OpportunityMatch.Status.NEW,
            ).count(),
        }

    def _viewer_context(self, user):
        from matching.models import OpportunityMatch

        return {
            'recommended_matches': OpportunityMatch.objects.filter(
                user=user,
            ).exclude(
                status=OpportunityMatch.Status.DISMISSED,
            ).order_by('-relevance_score')[:5],
            'new_match_count': OpportunityMatch.objects.filter(
                user=user, status=OpportunityMatch.Status.NEW,
            ).count(),
            'has_ai_access': user.has_ai_access,
        }
