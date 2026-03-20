from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, FormView, ListView, UpdateView

from core.mixins import CoordinatorRequiredMixin, SortableListMixin
from core.models import User

from .forms import CollaboratorForm, TrackedOpportunityForm
from .models import FederalOpportunity, OpportunityCollaborator, TrackedOpportunity


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
            qs = qs.filter(agency_code=agency)

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
        context['agency_codes'] = (
            FederalOpportunity.objects.exclude(agency_code='')
            .values_list('agency_code', flat=True)
            .distinct().order_by('agency_code')
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
        if user.is_authenticated and user.is_coordinator:
            context['tracked_record'] = TrackedOpportunity.objects.filter(
                federal_opportunity=self.object, tracked_by=user,
            ).first()
        return context


class HomeView(ListView):
    """Public landing page — redirect logged-in users to dashboard."""

    model = FederalOpportunity
    template_name = 'portal/home.html'
    context_object_name = 'recent_opportunities'
    paginate_by = 6

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return FederalOpportunity.objects.filter(
            opportunity_status=FederalOpportunity.OpportunityStatus.POSTED,
        ).order_by('-post_date')[:6]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['open_federal_count'] = FederalOpportunity.objects.filter(
            opportunity_status=FederalOpportunity.OpportunityStatus.POSTED,
        ).count()
        return context


# ---------------------------------------------------------------------------
# Coordinator pipeline views
# ---------------------------------------------------------------------------

class TrackedOpportunityListView(CoordinatorRequiredMixin, SortableListMixin, ListView):
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


class TrackOpportunityView(CoordinatorRequiredMixin, View):
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
            messages.success(request, _('Now tracking "%(title)s".') % {'title': opp.title[:60]})
        else:
            messages.info(request, _('You are already tracking this opportunity.'))

        next_url = request.POST.get('next', '')
        return redirect(next_url or reverse('dashboard'))


class TrackedOpportunityDetailView(CoordinatorRequiredMixin, DetailView):
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


class TrackedOpportunityUpdateView(CoordinatorRequiredMixin, UpdateView):
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
        messages.success(self.request, _('Tracking details updated.'))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('opportunities:tracked-detail', kwargs={'pk': self.object.pk})


class AddCollaboratorView(CoordinatorRequiredMixin, FormView):
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


class RemoveCollaboratorView(CoordinatorRequiredMixin, View):
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
