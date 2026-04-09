"""Bounty's /api/v1/helm-feed/ endpoint.

Exposes federal opportunity tracking metrics for Helm's executive dashboard.
"""
from django.conf import settings
from django.db.models import Count, Q, Sum
from django.utils import timezone

from keel.feed.views import helm_feed_view


def _product_url():
    if getattr(settings, 'DEMO_MODE', False):
        return 'https://demo-bounty.docklabs.ai'
    return 'https://bounty.docklabs.ai'


@helm_feed_view
def bounty_helm_feed(request):
    from opportunities.models import FederalOpportunity, TrackedOpportunity

    now = timezone.now()
    base_url = _product_url()

    # ── Metrics ──────────────────────────────────────────────────
    posted_count = FederalOpportunity.objects.filter(
        opportunity_status='posted',
    ).count()

    tracked_counts = TrackedOpportunity.objects.values('status').annotate(
        count=Count('id'),
    )
    tracked_by_status = {r['status']: r['count'] for r in tracked_counts}

    watching = tracked_by_status.get('watching', 0)
    preparing = tracked_by_status.get('preparing', 0)
    applied = tracked_by_status.get('applied', 0)
    awarded = tracked_by_status.get('awarded', 0)
    total_tracked = sum(tracked_by_status.values())

    total_funding = int(
        FederalOpportunity.objects.filter(
            opportunity_status='posted',
        ).aggregate(total=Sum('total_funding'))['total'] or 0
    )

    metrics = [
        {
            'key': 'opportunities_tracked',
            'label': 'Tracked',
            'value': total_tracked,
            'unit': None,
            'trend': None, 'trend_value': None, 'trend_period': None,
            'severity': 'normal',
            'deep_link': f'{base_url}/tracked/',
        },
        {
            'key': 'submissions_pending',
            'label': 'Preparing / Applied',
            'value': preparing + applied,
            'unit': None,
            'trend': None, 'trend_value': None, 'trend_period': None,
            'severity': 'normal',
            'deep_link': f'{base_url}/tracked/?status=preparing',
        },
        {
            'key': 'awards_received',
            'label': 'Awards Received',
            'value': awarded,
            'unit': None,
            'trend': None, 'trend_value': None, 'trend_period': None,
            'severity': 'normal',
            'deep_link': f'{base_url}/tracked/?status=awarded',
        },
        {
            'key': 'open_opportunities',
            'label': 'Open Opportunities',
            'value': posted_count,
            'unit': None,
            'trend': None, 'trend_value': None, 'trend_period': None,
            'severity': 'normal',
            'deep_link': f'{base_url}/opportunities/',
        },
    ]

    # ── Action Items ─────────────────────────────────────────────
    action_items = []

    # Opportunities closing soon (within 14 days)
    closing_soon = FederalOpportunity.objects.filter(
        opportunity_status='posted',
        close_date__lte=now.date() + __import__('datetime').timedelta(days=14),
        close_date__gte=now.date(),
    ).order_by('close_date')[:5]

    for opp in closing_soon:
        action_items.append({
            'id': f'bounty-closing-{opp.pk}',
            'type': 'submission',
            'title': f'Closing soon: {opp.title[:80]}',
            'description': f'Closes {opp.close_date.strftime("%b %d")}',
            'priority': 'high',
            'due_date': opp.close_date.isoformat() if opp.close_date else '',
            'assigned_to_role': 'federal_coordinator',
            'deep_link': f'{base_url}/opportunities/{opp.pk}/',
            'created_at': '',
        })

    # Tracked opportunities in preparing status
    preparing_opps = (
        TrackedOpportunity.objects
        .filter(status='preparing')
        .select_related('federal_opportunity')
        .order_by('-updated_at')[:5]
    )
    for tracked in preparing_opps:
        action_items.append({
            'id': f'bounty-prep-{tracked.pk}',
            'type': 'submission',
            'title': f'Prepare: {tracked.federal_opportunity.title[:80]}',
            'description': 'Application in preparation',
            'priority': 'medium',
            'due_date': tracked.federal_opportunity.close_date.isoformat() if tracked.federal_opportunity.close_date else '',
            'assigned_to_role': 'federal_coordinator',
            'deep_link': f'{base_url}/tracked/{tracked.pk}/',
            'created_at': tracked.created_at.isoformat() if tracked.created_at else '',
        })

    # ── Alerts ───────────────────────────────────────────────────
    alerts = []

    # High-relevance matches not yet viewed
    try:
        from matching.models import OpportunityMatch
        new_high_matches = OpportunityMatch.objects.filter(
            status='new',
            relevance_score__gte=getattr(settings, 'GRANT_MATCH_HIGH_SCORE', 90),
        ).count()
        if new_high_matches > 0:
            alerts.append({
                'id': 'bounty-high-matches',
                'type': 'milestone',
                'title': f'{new_high_matches} high-relevance match{"es" if new_high_matches != 1 else ""} awaiting review',
                'severity': 'info',
                'since': '',
                'deep_link': f'{base_url}/matching/',
            })
    except Exception:
        pass

    return {
        'product': 'bounty',
        'product_label': 'Bounty',
        'product_url': f'{base_url}/dashboard/',
        'metrics': metrics,
        'action_items': action_items,
        'alerts': alerts,
        'sparklines': {},
    }
