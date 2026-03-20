import logging

import requests
from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import UpdateView

from core.mixins import CoordinatorRequiredMixin
from opportunities.models import TrackedOpportunity

from .models import HarborConnection

logger = logging.getLogger(__name__)


class HarborConnectionSettingsView(CoordinatorRequiredMixin, UpdateView):
    """Configure Harbor API connection settings."""

    model = HarborConnection
    fields = ['harbor_base_url', 'harbor_api_token', 'is_active']
    template_name = 'integration/harbor_settings.html'
    success_url = reverse_lazy('integration:harbor-settings')

    def get_object(self, queryset=None):
        obj, _ = HarborConnection.objects.get_or_create(
            user=self.request.user,
            defaults={'harbor_base_url': 'https://harbor.docklabs.ai'},
        )
        return obj

    def form_valid(self, form):
        messages.success(self.request, 'Harbor connection settings updated.')
        return super().form_valid(form)


class PushToHarborView(CoordinatorRequiredMixin, View):
    """Push an awarded TrackedOpportunity to Harbor as a draft GrantProgram."""

    def post(self, request, pk):
        tracked = get_object_or_404(
            TrackedOpportunity,
            pk=pk,
            tracked_by=request.user,
        )

        if tracked.harbor_push_status == 'pushed':
            messages.info(request, 'This opportunity has already been pushed to Harbor.')
            return redirect('opportunities:tracked-detail', pk=tracked.pk)

        # Use global token from settings, or per-user connection
        connection = getattr(request.user, 'harbor_connection', None)
        base_url = getattr(connection, 'harbor_base_url', None) if connection else None
        api_token = getattr(connection, 'harbor_api_token', None) if connection else None

        if not base_url:
            base_url = getattr(settings, 'HARBOR_API_BASE_URL', '')
        if not api_token:
            api_token = getattr(settings, 'HARBOR_API_TOKEN', '')

        if not base_url or not api_token:
            messages.error(request, 'Harbor connection not configured. Set up your connection in Settings.')
            return redirect('opportunities:tracked-detail', pk=tracked.pk)

        opp = tracked.federal_opportunity
        payload = {
            'title': opp.title,
            'description': opp.description or '',
            'agency': opp.agency_name,
            'cfda_numbers': opp.cfda_numbers or '',
            'award_floor': str(opp.award_floor) if opp.award_floor else '',
            'award_ceiling': str(opp.award_ceiling) if opp.award_ceiling else '',
            'eligible_applicants': opp.eligible_applicants or '',
            'grants_gov_url': opp.url or '',
            'bounty_opportunity_id': str(opp.pk),
        }

        try:
            resp = requests.post(
                f'{base_url.rstrip("/")}/api/federal-intake/',
                json=payload,
                headers={'Authorization': f'Token {api_token}'},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            tracked.harbor_program_id = data.get('program_id', '')
            tracked.harbor_push_status = 'pushed'
            tracked.save(update_fields=['harbor_program_id', 'harbor_push_status'])

            if connection:
                connection.last_synced_at = timezone.now()
                connection.save(update_fields=['last_synced_at'])

            messages.success(request, f'Successfully pushed to Harbor as program {tracked.harbor_program_id}.')

        except requests.RequestException as e:
            logger.error('Failed to push to Harbor: %s', e)
            tracked.harbor_push_status = 'failed'
            tracked.save(update_fields=['harbor_push_status'])
            messages.error(request, f'Failed to push to Harbor: {e}')

        return redirect('opportunities:tracked-detail', pk=tracked.pk)
