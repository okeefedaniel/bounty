from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Exists, OuterRef
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import ListView, UpdateView

from core.mixins import CoordinatorRequiredMixin
from opportunities.models import TrackedOpportunity

from .forms import MatchPreferenceForm
from .matching import run_matching_async
from .models import MatchPreference, OpportunityMatch


class MatchPreferenceView(LoginRequiredMixin, UpdateView):
    """Create or update the user's match preferences."""

    model = MatchPreference
    form_class = MatchPreferenceForm
    template_name = 'matching/preferences.html'
    success_url = reverse_lazy('matching:recommendations')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.has_ai_access:
            messages.info(request, _('Please add your Anthropic API key in your profile settings.'))
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        obj, _ = MatchPreference.objects.get_or_create(user=self.request.user)
        return obj

    def form_valid(self, form):
        response = super().form_valid(form)
        run_matching_async(self.request.user)
        messages.success(self.request, _('Preferences saved! AI matching is running.'))
        return response


class RecommendedMatchesView(LoginRequiredMixin, ListView):
    """List AI-recommended opportunity matches."""

    model = OpportunityMatch
    template_name = 'matching/recommendations.html'
    context_object_name = 'matches'
    paginate_by = 20

    def get_queryset(self):
        tracked_subquery = TrackedOpportunity.objects.filter(
            federal_opportunity=OuterRef('federal_opportunity'),
            tracked_by=self.request.user,
        )

        qs = OpportunityMatch.objects.filter(
            user=self.request.user,
        ).exclude(
            status=OpportunityMatch.Status.DISMISSED,
        ).select_related('federal_opportunity').annotate(
            is_tracked=Exists(tracked_subquery),
        )

        qs.filter(status=OpportunityMatch.Status.NEW).update(
            status=OpportunityMatch.Status.VIEWED,
        )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_matches'] = OpportunityMatch.objects.filter(
            user=self.request.user,
        ).exclude(status=OpportunityMatch.Status.DISMISSED).count()
        context['new_matches'] = OpportunityMatch.objects.filter(
            user=self.request.user, status=OpportunityMatch.Status.NEW,
        ).count()
        context['has_preferences'] = MatchPreference.objects.filter(
            user=self.request.user,
        ).exists()
        context['has_ai_access'] = self.request.user.has_ai_access
        return context


class DismissMatchView(LoginRequiredMixin, View):
    """POST-only view to dismiss a match recommendation."""

    http_method_names = ['post']

    def post(self, request, pk):
        match = get_object_or_404(OpportunityMatch, pk=pk, user=request.user)
        match.status = OpportunityMatch.Status.DISMISSED
        match.save(update_fields=['status', 'updated_at'])
        messages.info(request, _('Recommendation dismissed.'))
        next_url = request.POST.get('next', '')
        return redirect(next_url or reverse('matching:recommendations'))


class TrackAndDismissView(CoordinatorRequiredMixin, View):
    """POST-only: track a federal opportunity AND dismiss the recommendation."""

    http_method_names = ['post']

    def post(self, request, pk):
        match = get_object_or_404(OpportunityMatch, pk=pk, user=request.user)
        TrackedOpportunity.objects.get_or_create(
            federal_opportunity=match.federal_opportunity,
            tracked_by=request.user,
            defaults={'status': TrackedOpportunity.TrackingStatus.WATCHING},
        )
        match.status = OpportunityMatch.Status.DISMISSED
        match.save(update_fields=['status', 'updated_at'])
        messages.success(request, _('Opportunity tracked and recommendation dismissed.'))
        next_url = request.POST.get('next', '')
        return redirect(next_url or reverse('matching:recommendations'))


class MatchFeedbackView(LoginRequiredMixin, View):
    """POST-only: record thumbs up/down feedback."""

    http_method_names = ['post']

    def post(self, request, pk):
        match = get_object_or_404(OpportunityMatch, pk=pk, user=request.user)
        feedback = request.POST.get('feedback', '')
        reason = request.POST.get('feedback_reason', '')

        if feedback in dict(OpportunityMatch.Feedback.choices):
            match.feedback = feedback
        if feedback == 'negative' and reason in dict(OpportunityMatch.FeedbackReason.choices):
            match.feedback_reason = reason
        else:
            match.feedback_reason = ''

        match.save(update_fields=['feedback', 'feedback_reason', 'updated_at'])

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok', 'feedback': match.feedback})

        messages.success(request, _('Feedback recorded. Thank you!'))
        next_url = request.POST.get('next', '')
        return redirect(next_url or reverse('matching:recommendations'))
