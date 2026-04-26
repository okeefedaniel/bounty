"""Bounty's /api/v1/helm-feed/inbox/ endpoint — per-user inbox.

Items where the requesting user is the gating dependency right now in
Bounty: NEW high-relevance ``OpportunityMatch`` rows the user hasn't
reviewed yet, plus that user's unread notifications.

Conforms to the UserInbox shape in helm.dashboard.feed_contract.
Auth + cache + sub-resolution come from keel.feed.helm_inbox_view.
"""
from django.conf import settings
from keel.feed.views import helm_inbox_view

from .helm_feed import _product_url


@helm_inbox_view
def bounty_helm_feed_inbox(request, user):
    from core.models import Notification
    from matching.models import OpportunityMatch

    base_url = _product_url().rstrip('/')
    high_threshold = getattr(settings, 'GRANT_MATCH_HIGH_SCORE', 90)

    items = []

    new_matches = (
        OpportunityMatch.objects
        .filter(
            user=user,
            status=OpportunityMatch.Status.NEW,
            relevance_score__gte=high_threshold,
        )
        .select_related('federal_opportunity')
        .order_by('-relevance_score', '-created_at')[:50]
    )
    for m in new_matches:
        opp = m.federal_opportunity
        title_label = (opp.title or f'Opportunity {opp.pk}')[:80]
        items.append({
            'id': str(m.id),
            'type': 'match',
            'title': f'Review match: {title_label} ({m.relevance_score}%)',
            'deep_link': f'{base_url}/matching/recommendations/',
            'waiting_since': m.created_at.isoformat() if m.created_at else '',
            'due_date': opp.close_date.isoformat() if getattr(opp, 'close_date', None) else None,
            'priority': 'high',
        })

    unread = (
        Notification.objects
        .filter(recipient=user, is_read=False)
        .order_by('-created_at')[:50]
    )
    notifications = []
    for n in unread:
        link = n.link or ''
        if link and base_url and link.startswith('/'):
            link = f'{base_url}{link}'
        notifications.append({
            'id': str(n.id),
            'title': n.title,
            'body': getattr(n, 'message', '') or '',
            'deep_link': link,
            'created_at': n.created_at.isoformat(),
            'priority': (n.priority or 'normal').lower(),
        })

    return {
        'product': getattr(settings, 'KEEL_PRODUCT_CODE', 'bounty'),
        'product_label': getattr(settings, 'KEEL_PRODUCT_NAME', 'Bounty'),
        'product_url': base_url,
        'user_sub': '',  # filled by decorator
        'items': items,
        'unread_notifications': notifications,
        'fetched_at': '',  # filled by decorator
    }
