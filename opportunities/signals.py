"""Manifest roundtrip receiver for TrackedOpportunity.

When a ``ManifestHandoff`` completes — either via a Manifest webhook or
a local_sign fallback — keel.signatures fires ``packet_approved``. We
connect a single receiver that:

  1. Writes the signed PDF to the OpportunityAttachment collection with
     source=MANIFEST_SIGNED so the detail template shows the Signed
     badge and blocks deletion.
  2. Transitions the TrackedOpportunity status to the handoff's
     ``on_approved_status`` via WorkflowEngine so the transition goes
     through the normal audit trail.

The receiver is intentionally minimal — heavier behavior (notifications,
FOIA export registration) belongs in downstream receivers attached to
the same signal.
"""
import logging

from django.apps import apps
from django.core.files.base import ContentFile
from django.dispatch import receiver

from keel.signatures.signals import packet_approved

logger = logging.getLogger(__name__)


@receiver(packet_approved)
def on_packet_approved(sender, handoff, source_obj, signed_pdf, **kwargs):
    """File the signed PDF + transition the source to approved."""
    # Gate on source model to avoid firing on other products' handoffs
    # when multiple products share a process (edge case, but cheap).
    if not hasattr(source_obj, '_meta'):
        return
    if source_obj._meta.label_lower != 'opportunities.trackedopportunity':
        return

    try:
        attachment_cls = apps.get_model(*handoff.attachment_model.split('.'))
    except (LookupError, ValueError):
        logger.exception('Unknown attachment model %r on handoff %s',
                         handoff.attachment_model, handoff.pk)
        return

    # Read the file bytes; caller passes either an open file-like object
    # or a ContentFile. Normalise to Django's file storage contract.
    if hasattr(signed_pdf, 'read'):
        raw = signed_pdf.read()
        filename = getattr(signed_pdf, 'name', None) or f'{handoff.packet_label or "signed"}.pdf'
    else:
        raw = bytes(signed_pdf)
        filename = f'{handoff.packet_label or "signed"}.pdf'
    filename = filename.rsplit('/', 1)[-1] or 'signed.pdf'

    attachment_cls.objects.create(
        **{handoff.attachment_fk_name: source_obj},
        file=ContentFile(raw, name=filename),
        filename=filename,
        content_type='application/pdf',
        size_bytes=len(raw),
        description=handoff.packet_label or 'Signed via Manifest handoff',
        visibility='internal',
        source='manifest_signed',
        manifest_packet_uuid=handoff.manifest_packet_uuid,
        uploaded_by=handoff.created_by,
    )

    # Use WorkflowEngine so the transition is audited + role-checked.
    # Imported lazily to avoid the models → workflows circular import.
    from .workflows import TRACKED_OPPORTUNITY_WORKFLOW
    if source_obj.status != handoff.on_approved_status:
        try:
            TRACKED_OPPORTUNITY_WORKFLOW.execute(
                source_obj,
                handoff.on_approved_status,
                user=handoff.created_by,
                comment=f'Approved via Manifest handoff {handoff.pk}',
            )
        except Exception:
            logger.exception(
                'Failed to transition %s → %s after Manifest handoff %s',
                source_obj.pk, handoff.on_approved_status, handoff.pk,
            )
