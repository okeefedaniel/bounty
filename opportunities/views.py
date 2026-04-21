from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, FormView, ListView, UpdateView

from core.mixins import SortableListMixin
from django.contrib.auth import get_user_model
User = get_user_model()
from keel.search.views import chat_stream_view, instant_search_view

from .chat import GrantChat
from .forms import CollaboratorForm, TrackedOpportunityForm
from .models import FederalOpportunity, OpportunityCollaborator, TrackedOpportunity
from .search import GrantSearchEngine


# ---------------------------------------------------------------------------
# Public portal views
# ---------------------------------------------------------------------------

class OpportunityListView(ListView):
    """Public listing of federal grant opportunities with filtering."""

    model = FederalOpportunity
    template_name = 'portal/federal_opportunities.html'
    context_object_name = 'opportunities'
    paginate_by = 12

    def get_queryset(self):
        qs = FederalOpportunity.objects.all().order_by('-post_date')

        agency = self.request.GET.get('agency')
        if agency:
            qs = qs.filter(agency_name=agency)

        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(opportunity_status=status)

        category = self.request.GET.get('category')
        if category:
            qs = qs.filter(category=category)

        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_filters'] = {
            'agency': self.request.GET.get('agency', ''),
            'status': self.request.GET.get('status', ''),
            'category': self.request.GET.get('category', ''),
            'q': self.request.GET.get('q', ''),
        }
        context['agencies'] = (
            FederalOpportunity.objects.exclude(agency_name='')
            .values_list('agency_name', flat=True)
            .distinct().order_by('agency_name')
        )
        context['statuses'] = FederalOpportunity.OpportunityStatus.choices
        context['view_mode'] = self.request.GET.get('view', 'cards')
        return context


class OpportunityDetailView(DetailView):
    """Public detail view for a single federal opportunity."""

    model = FederalOpportunity
    template_name = 'portal/federal_opportunity_detail.html'
    context_object_name = 'opportunity'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_authenticated:
            context['tracked_record'] = TrackedOpportunity.objects.filter(
                federal_opportunity=self.object, tracked_by=user,
            ).first()
        return context


# ---------------------------------------------------------------------------
# Search API endpoints
# ---------------------------------------------------------------------------

_grant_engine = GrantSearchEngine()
_grant_chat = GrantChat()


def opportunity_instant(request):
    """GET /opportunities/instant/?q=... — typeahead JSON endpoint."""
    return instant_search_view(request, _grant_engine)


@login_required
def opportunity_chat(request):
    """POST /opportunities/chat/ — AI streaming chat endpoint."""
    return chat_stream_view(request, _grant_chat)


from keel.core.views import LandingView


class HomeView(LandingView):
    """Public landing page — Keel-shared landing layout."""

    template_name = 'portal/home.html'
    authenticated_redirect = 'dashboard'

    features = [
        {'icon': 'bi-bullseye', 'title': 'Federal Discovery',
         'description': 'Browse 2,000+ active federal funding opportunities sourced directly from grants.gov.',
         'color': 'blue'},
        {'icon': 'bi-stars', 'title': 'AI Matching',
         'description': 'Claude-powered relevance scoring matches opportunities to your agency priorities and tracked keywords.',
         'color': 'teal'},
        {'icon': 'bi-arrow-up-right-circle', 'title': 'Push to Harbor',
         'description': 'Track promising opportunities and push them straight to Harbor as draft grant programs.',
         'color': 'yellow'},
    ]

    steps = [
        {'title': 'Browse', 'description': 'Search federal grants by agency, category, deadline, or keyword.'},
        {'title': 'Match', 'description': 'AI scores each opportunity against your tracked priorities.'},
        {'title': 'Track', 'description': 'Save opportunities to your watchlist and collaborate with your team.'},
        {'title': 'Push to Harbor', 'description': 'Promote a federal opportunity into a Harbor grant program with one click.'},
    ]

    def get_landing_stats(self):
        try:
            open_count = FederalOpportunity.objects.filter(
                opportunity_status=FederalOpportunity.OpportunityStatus.POSTED,
            ).count()
            open_value = str(open_count) if open_count else '2,000+'
        except Exception:
            open_value = '2,000+'
        return [
            {'value': open_value, 'label': 'Open Opportunities'},
            {'value': '50+', 'label': 'Federal Agencies'},
            {'value': 'AI', 'label': 'Powered'},
            {'value': 'Harbor', 'label': 'Integration'},
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['recent_opportunities'] = list(FederalOpportunity.objects.filter(
                opportunity_status=FederalOpportunity.OpportunityStatus.POSTED,
            ).order_by('-post_date')[:6])
        except Exception:
            context['recent_opportunities'] = []
        return context


# ---------------------------------------------------------------------------
# Coordinator pipeline views
# ---------------------------------------------------------------------------

class TrackedOpportunityListView(LoginRequiredMixin, SortableListMixin, ListView):
    """List federal opportunities tracked by the current user."""

    model = TrackedOpportunity
    template_name = 'opportunities/tracked_opportunities.html'
    context_object_name = 'tracked_opportunities'
    paginate_by = 20

    sortable_fields = {
        'opportunity': 'federal_opportunity__title',
        'agency': 'federal_opportunity__agency_name',
        'status': 'status',
        'priority': Case(
            When(priority='high', then=Value(1)),
            When(priority='medium', then=Value(2)),
            When(priority='low', then=Value(3)),
            output_field=IntegerField(),
        ),
        'close_date': 'federal_opportunity__close_date',
    }
    default_sort = 'close_date'
    default_dir = 'asc'

    def get_queryset(self):
        qs = TrackedOpportunity.objects.select_related(
            'federal_opportunity',
        ).filter(tracked_by=self.request.user)

        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)

        priority = self.request.GET.get('priority')
        if priority:
            qs = qs.filter(priority=priority)

        return self.apply_sorting(qs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = TrackedOpportunity.TrackingStatus.choices
        context['priority_choices'] = [
            ('low', _('Low')), ('medium', _('Medium')), ('high', _('High')),
        ]
        context['current_status'] = self.request.GET.get('status', '')
        context['current_priority'] = self.request.GET.get('priority', '')
        return context


class TrackOpportunityView(LoginRequiredMixin, View):
    """POST-only view to start tracking a federal opportunity."""

    http_method_names = ['post']

    def post(self, request):
        opp_id = request.POST.get('federal_opportunity_id')
        opp = get_object_or_404(FederalOpportunity, pk=opp_id)

        tracked, created = TrackedOpportunity.objects.get_or_create(
            federal_opportunity=opp, tracked_by=request.user,
            defaults={'status': TrackedOpportunity.TrackingStatus.WATCHING},
        )

        if created:
            # Record the explicit self-claim in the assignment history.
            tracked.claim(request.user)
            messages.success(request, _('Now tracking "%(title)s".') % {'title': opp.title[:60]})
        else:
            messages.info(request, _('You are already tracking this opportunity.'))

        next_url = request.POST.get('next', '')
        return redirect(next_url or reverse('dashboard'))


class ClaimOpportunityView(LoginRequiredMixin, View):
    """Claim an unclaimed tracked opportunity from the shared pool."""

    http_method_names = ['post']

    def post(self, request, pk):
        tracked = get_object_or_404(TrackedOpportunity, pk=pk)
        if tracked.is_claimed and tracked.tracked_by != request.user:
            messages.error(
                request,
                _('This opportunity is already claimed by %(who)s.') % {
                    'who': tracked.tracked_by.get_full_name() or tracked.tracked_by.username,
                },
            )
            return redirect(reverse('opportunities:tracked-detail', kwargs={'pk': pk}))

        tracked.claim(request.user)
        messages.success(request, _('You are now the principal driver for this opportunity.'))
        return redirect(reverse('opportunities:tracked-detail', kwargs={'pk': pk}))


class ReleaseOpportunityView(LoginRequiredMixin, View):
    """Release a tracked opportunity back to the shared pool."""

    http_method_names = ['post']

    def post(self, request, pk):
        tracked = get_object_or_404(TrackedOpportunity, pk=pk, tracked_by=request.user)
        tracked.release(request.user)
        messages.success(request, _('Opportunity released back to the pool.'))
        return redirect(reverse('opportunities:tracked-list'))


class TrackedOpportunityDetailView(LoginRequiredMixin, DetailView):
    """Detail view for a tracked opportunity with edit form and collaborators."""

    model = TrackedOpportunity
    template_name = 'opportunities/tracked_opportunity_detail.html'
    context_object_name = 'tracked'

    def get_queryset(self):
        return TrackedOpportunity.objects.select_related(
            'federal_opportunity', 'tracked_by',
        ).filter(tracked_by=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = TrackedOpportunityForm(instance=self.object)
        context['collaborator_form'] = CollaboratorForm()
        context['collaborators'] = self.object.collaborators.select_related(
            'user', 'invited_by',
        ).filter(is_active=True)
        return context


class TrackedOpportunityUpdateView(LoginRequiredMixin, UpdateView):
    """Update a tracked opportunity's status, notes, and priority."""

    model = TrackedOpportunity
    form_class = TrackedOpportunityForm
    template_name = 'opportunities/tracked_opportunity_detail.html'
    context_object_name = 'tracked'

    def get_queryset(self):
        return TrackedOpportunity.objects.select_related(
            'federal_opportunity', 'tracked_by',
        ).filter(tracked_by=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collaborator_form'] = CollaboratorForm()
        context['collaborators'] = self.object.collaborators.select_related(
            'user', 'invited_by',
        ).filter(is_active=True)
        return context

    def form_valid(self, form):
        from .workflows import TRACKED_OPPORTUNITY_WORKFLOW

        old_status = self.get_object().status
        new_status = form.cleaned_data.get('status', old_status)

        if old_status != new_status:
            # Save non-status fields first, then use workflow for status transition
            obj = form.save(commit=False)
            obj.status = old_status  # Restore — let workflow handle it
            obj.save()
            try:
                TRACKED_OPPORTUNITY_WORKFLOW.execute(obj, new_status, user=self.request.user)
            except Exception:
                messages.error(self.request, _('Cannot transition from %(old)s to %(new)s.') % {
                    'old': old_status, 'new': new_status,
                })
                return self.form_invalid(form)
        else:
            form.save()

        messages.success(self.request, _('Tracking details updated.'))
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('opportunities:tracked-detail', kwargs={'pk': self.object.pk})


class AddCollaboratorView(LoginRequiredMixin, FormView):
    """Add an internal or external collaborator to a tracked opportunity."""

    form_class = CollaboratorForm
    template_name = 'opportunities/add_collaborator.html'

    def dispatch(self, request, *args, **kwargs):
        self.tracked = get_object_or_404(
            TrackedOpportunity, pk=self.kwargs['pk'], tracked_by=request.user,
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        collab_type = form.cleaned_data['collaborator_type']
        role = form.cleaned_data['role']
        collab_kwargs = {
            'tracked_opportunity': self.tracked,
            'role': role,
            'invited_by': self.request.user,
        }

        if collab_type == 'internal':
            user = get_object_or_404(User, username=form.cleaned_data['username'])
            collab_kwargs['user'] = user
        else:
            collab_kwargs['email'] = form.cleaned_data['email']
            collab_kwargs['name'] = form.cleaned_data.get('name', '')

        OpportunityCollaborator.objects.create(**collab_kwargs)
        messages.success(self.request, _('Collaborator added successfully.'))
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('opportunities:tracked-detail', kwargs={'pk': self.tracked.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tracked'] = self.tracked
        return context


class RemoveCollaboratorView(LoginRequiredMixin, View):
    """POST-only view to deactivate a collaborator."""

    http_method_names = ['post']

    def post(self, request, pk, collab_pk):
        tracked = get_object_or_404(TrackedOpportunity, pk=pk, tracked_by=request.user)
        collaborator = get_object_or_404(
            OpportunityCollaborator, pk=collab_pk, tracked_opportunity=tracked,
        )
        collaborator.is_active = False
        collaborator.save(update_fields=['is_active'])
        messages.success(request, _('Collaborator removed.'))
        return redirect(reverse('opportunities:tracked-detail', kwargs={'pk': pk}))
