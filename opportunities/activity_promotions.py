"""Track A promotion rules for Bounty opportunities.

Maps audit-row creates of OpportunityCollaborator / OpportunityAttachment /
OpportunityAssignment to activity verbs. Track B verbs
(workflow.transitioned for TrackedOpportunity status changes, signing.*
for Manifest handoffs) emit explicitly via record_activity() from
bounty's services.

Bounty has no AbstractInternalNote subclass yet (the lifecycle standard
calls for one but it's not landed); when added, register a
``diligence.note_posted`` rule here.
"""
from __future__ import annotations

import logging

from django.apps import apps

from keel.activity.registry import PromotionRegistry, PromotionRule

logger = logging.getLogger(__name__)


def _get_collab(audit):
    Collab = apps.get_model('opportunities', 'OpportunityCollaborator')
    try:
        return (
            Collab.objects.select_related(
                'tracked_opportunity', 'tracked_opportunity__federal_opportunity', 'user',
            ).get(pk=audit.entity_id)
        )
    except (Collab.DoesNotExist, ValueError):
        return None


def _get_assignment(audit):
    Assignment = apps.get_model('opportunities', 'OpportunityAssignment')
    try:
        return (
            Assignment.objects.select_related('tracked_opportunity', 'assigned_to')
            .get(pk=audit.entity_id)
        )
    except (Assignment.DoesNotExist, ValueError):
        return None


def _get_attachment(audit):
    Attachment = apps.get_model('opportunities', 'OpportunityAttachment')
    try:
        return Attachment.objects.select_related('tracked_opportunity').get(pk=audit.entity_id)
    except (Attachment.DoesNotExist, ValueError):
        return None


def _collab_added_kwargs(audit):
    collab = _get_collab(audit)
    if collab is None:
        return None
    return {
        'tracked_opportunity': collab.tracked_opportunity,
        'metadata': {
            'role': collab.role,
            'invited_email': collab.email or '',
            'is_external_invite': bool(collab.email and not collab.user_id),
        },
    }


def _assignment_added_kwargs(audit):
    assignment = _get_assignment(audit)
    if assignment is None:
        return None
    return {
        'tracked_opportunity': assignment.tracked_opportunity,
        'metadata': {
            'assignment_id': str(assignment.pk),
            'assigned_to': str(assignment.assigned_to_id) if assignment.assigned_to_id else '',
            'status': getattr(assignment, 'status', ''),
            'assignment_type': getattr(assignment, 'assignment_type', ''),
        },
    }


def _attachment_uploaded_kwargs(audit):
    attachment = _get_attachment(audit)
    if attachment is None:
        return None
    return {
        'tracked_opportunity': attachment.tracked_opportunity,
        'metadata': {
            'attachment_id': str(attachment.pk),
            'filename': str(getattr(attachment, 'file', '')).split('/')[-1] or '(file)',
            'visibility': getattr(attachment, 'visibility', ''),
        },
    }


def register_all() -> None:
    """Called from OpportunitiesConfig.ready()."""
    PromotionRegistry.register(PromotionRule(
        entity_type='Opportunity Collaborator',
        action='create',
        verb='collab.added',
        visibility='collaborators',
        target_fn=lambda audit: getattr(_get_collab(audit), 'tracked_opportunity', None),
        action_fn=_get_collab,
        deep_link_fn=lambda audit: _safe_get_url(getattr(_get_collab(audit), 'tracked_opportunity', None)),
        source_label_fn=_collab_added_label,
        metadata_fn=_collab_added_kwargs,
    ))

    PromotionRegistry.register(PromotionRule(
        entity_type='Opportunity Collaborator',
        action='delete',
        verb='collab.removed',
        visibility='collaborators',
        target_fn=lambda audit: _resolve_tracked_opportunity_from_changes(
            audit, 'tracked_opportunity_id', 'tracked_opportunity',
        ),
        source_label_fn=lambda audit: f'{_actor_name(audit)} removed a collaborator',
        metadata_fn=lambda audit: {
            'role': (audit.changes or {}).get('role', ''),
        },
    ))

    PromotionRegistry.register(PromotionRule(
        entity_type='Opportunity Assignment',
        action='create',
        verb='workflow.assignment_changed',
        visibility='collaborators',
        target_fn=lambda audit: getattr(_get_assignment(audit), 'tracked_opportunity', None),
        action_fn=_get_assignment,
        deep_link_fn=lambda audit: _safe_get_url(getattr(_get_assignment(audit), 'tracked_opportunity', None)),
        source_label_fn=_assignment_added_label,
        metadata_fn=_assignment_added_kwargs,
    ))

    PromotionRegistry.register(PromotionRule(
        entity_type='Opportunity Attachment',
        action='create',
        verb='diligence.attachment_uploaded',
        visibility='collaborators',
        target_fn=lambda audit: getattr(_get_attachment(audit), 'tracked_opportunity', None),
        action_fn=_get_attachment,
        deep_link_fn=lambda audit: _safe_get_url(getattr(_get_attachment(audit), 'tracked_opportunity', None)),
        source_label_fn=lambda audit: f'{_actor_name(audit)} uploaded a file',
        metadata_fn=_attachment_uploaded_kwargs,
    ))

    logger.debug('keel.activity: bounty opportunities promotion rules registered (4 Track A rules)')


# Helpers

def _actor_name(audit) -> str:
    if audit.user_id is None:
        return 'system'
    return str(audit.user)


def _collab_added_label(audit) -> str:
    collab = _get_collab(audit)
    if collab is None:
        return f'{_actor_name(audit)} added a collaborator'
    if collab.user_id and collab.user:
        invitee = collab.user.get_full_name() or collab.user.username
    else:
        invitee = collab.email or 'an invitee'
    return f'{_actor_name(audit)} added {invitee} as {collab.get_role_display()}'


def _assignment_added_label(audit) -> str:
    assignment = _get_assignment(audit)
    if assignment is None:
        return f'{_actor_name(audit)} updated an assignment'
    if assignment.assigned_to_id and assignment.assigned_to:
        invitee = assignment.assigned_to.get_full_name() or assignment.assigned_to.username
    else:
        invitee = 'someone'
    return f'{_actor_name(audit)} assigned {invitee} as principal driver'


def _resolve_tracked_opportunity_from_changes(audit, *fk_keys):
    changes = audit.changes or {}
    to_id = None
    for k in fk_keys:
        if changes.get(k):
            to_id = changes.get(k)
            break
    if not to_id:
        return None
    TrackedOpportunity = apps.get_model('opportunities', 'TrackedOpportunity')
    try:
        return TrackedOpportunity.objects.get(pk=to_id)
    except (TrackedOpportunity.DoesNotExist, ValueError, TypeError):
        return None


def _safe_get_url(obj) -> str:
    if obj is None:
        return ''
    try:
        return obj.get_absolute_url() or ''
    except Exception:
        return ''
