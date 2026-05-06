import uuid

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from keel.core.models import (
    AbstractAssignment,
    AbstractAttachment,
    AbstractCollaborator,
    AbstractStatusHistory,
)


class FederalOpportunity(models.Model):
    """Federal grant opportunity cached from the Simpler Grants.gov API."""

    class OpportunityStatus(models.TextChoices):
        POSTED = 'posted', _('Posted')
        CLOSED = 'closed', _('Closed')
        ARCHIVED = 'archived', _('Archived')
        FORECASTED = 'forecasted', _('Forecasted')

    class FundingInstrument(models.TextChoices):
        GRANT = 'grant', _('Grant')
        COOPERATIVE_AGREEMENT = 'cooperative_agreement', _('Cooperative Agreement')
        PROCUREMENT_CONTRACT = 'procurement_contract', _('Procurement Contract')
        OTHER = 'other', _('Other')

    id = models.AutoField(primary_key=True)

    opportunity_id = models.CharField(
        max_length=64, unique=True,
        help_text=_('Unique identifier from Grants.gov'),
    )
    opportunity_number = models.CharField(
        max_length=255, blank=True, default='',
        help_text=_('Opportunity number / NOFO number'),
    )

    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, default='')
    agency_name = models.CharField(max_length=255, blank=True, default='')
    agency_code = models.CharField(max_length=50, blank=True, default='')

    category = models.CharField(max_length=255, blank=True, default='')
    funding_instrument = models.CharField(
        max_length=30, choices=FundingInstrument.choices,
        default=FundingInstrument.GRANT,
    )
    cfda_numbers = models.JSONField(default=list, blank=True)

    award_floor = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )
    award_ceiling = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )
    expected_awards = models.IntegerField(null=True, blank=True)
    total_funding = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )

    post_date = models.DateField(null=True, blank=True)
    close_date = models.DateField(null=True, blank=True)
    archive_date = models.DateField(null=True, blank=True)

    opportunity_status = models.CharField(
        max_length=15, choices=OpportunityStatus.choices,
        default=OpportunityStatus.POSTED,
    )

    applicant_types = models.JSONField(default=list, blank=True)
    eligible_applicants = models.TextField(blank=True, default='')

    grants_gov_url = models.URLField(max_length=500, blank=True, default='')

    # Cross-reference to Harbor (set after push)
    harbor_program_id = models.CharField(
        max_length=64, blank=True, default='',
        help_text=_('ID of linked GrantProgram in Harbor (set after push)'),
    )

    synced_at = models.DateTimeField(auto_now=True)
    raw_data = models.JSONField(default=dict, blank=True)

    # Full-text search (populated by sync + management command)
    search_vector = SearchVectorField(null=True)

    class Meta:
        ordering = ['-post_date', '-close_date']
        verbose_name = _('Federal Opportunity')
        verbose_name_plural = _('Federal Opportunities')
        indexes = [
            models.Index(fields=['opportunity_status', 'close_date'], name='idx_fedopp_status_close'),
            models.Index(fields=['agency_code'], name='idx_fedopp_agency'),
            GinIndex(fields=['search_vector'], name='fedopp_search_gin'),
        ]

    def __str__(self):
        return f"{self.opportunity_number or self.opportunity_id} — {self.title[:80]}"

    @property
    def is_open(self):
        if self.opportunity_status != self.OpportunityStatus.POSTED:
            return False
        if self.close_date and self.close_date < timezone.now().date():
            return False
        return True

    @property
    def days_until_close(self):
        if not self.close_date:
            return None
        delta = self.close_date - timezone.now().date()
        return delta.days if delta.days >= 0 else None

    @property
    def funding_range_display(self):
        if self.award_floor and self.award_ceiling:
            return f"${self.award_floor:,.0f} – ${self.award_ceiling:,.0f}"
        if self.award_ceiling:
            return f"Up to ${self.award_ceiling:,.0f}"
        if self.award_floor:
            return f"From ${self.award_floor:,.0f}"
        return "Not specified"


class TrackedOpportunity(models.Model):
    """A federal opportunity being actively tracked by a coordinator."""

    class TrackingStatus(models.TextChoices):
        WATCHING = 'watching', _('Watching')
        PREPARING = 'preparing', _('Preparing Application')
        APPROVED = 'approved', _('Internally Approved')
        APPLIED = 'applied', _('Applied')
        AWARDED = 'awarded', _('Awarded')
        DECLINED = 'declined', _('Declined')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    federal_opportunity = models.ForeignKey(
        FederalOpportunity, on_delete=models.CASCADE,
        related_name='tracked_records',
    )
    tracked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tracked_opportunities',
        help_text=_('Current principal driver. Null when unclaimed.'),
    )
    status = models.CharField(
        max_length=15, choices=TrackingStatus.choices,
        default=TrackingStatus.WATCHING,
    )
    notes = models.TextField(blank=True, default='')
    priority = models.CharField(
        max_length=10,
        choices=[('low', _('Low')), ('medium', _('Medium')), ('high', _('High'))],
        default='medium',
    )

    # Harbor integration
    harbor_program_id = models.CharField(
        max_length=64, blank=True, default='',
        help_text=_('Harbor GrantProgram ID if pushed'),
    )
    harbor_push_status = models.CharField(
        max_length=20,
        choices=[
            ('not_pushed', _('Not Pushed')),
            ('pushed', _('Pushed to Harbor')),
            ('failed', _('Push Failed')),
        ],
        default='not_pushed',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = _('Tracked Opportunity')
        verbose_name_plural = _('Tracked Opportunities')
        unique_together = ['federal_opportunity', 'tracked_by']

    def __str__(self):
        return f"[{self.get_status_display()}] {self.federal_opportunity.title[:60]}"

    @property
    def is_claimed(self):
        return self.tracked_by_id is not None

    def claim(self, user, by_manager=None):
        """Assign a principal driver and open an Assignment record.

        ``by_manager`` is set when a manager assigns on someone else's behalf;
        self-claims leave it None and record ``assignment_type=CLAIMED``.
        Closes any open assignment row before opening the new one.
        """
        from django.utils import timezone

        for open_row in self.assignments.filter(
            status__in=[
                OpportunityAssignment.Status.ASSIGNED,
                OpportunityAssignment.Status.IN_PROGRESS,
            ],
        ):
            open_row.status = (
                OpportunityAssignment.Status.REASSIGNED
                if user != open_row.assigned_to
                else OpportunityAssignment.Status.COMPLETED
            )
            open_row.released_at = timezone.now()
            open_row.save(update_fields=['status', 'released_at'])

        assignment = OpportunityAssignment.objects.create(
            tracked_opportunity=self,
            assigned_to=user,
            assigned_by=by_manager,
            assignment_type=(
                OpportunityAssignment.AssignmentType.MANAGER_ASSIGNED
                if by_manager else OpportunityAssignment.AssignmentType.CLAIMED
            ),
            status=OpportunityAssignment.Status.IN_PROGRESS,
        )
        self.tracked_by = user
        self.save(update_fields=['tracked_by', 'updated_at'])
        return assignment

    def release(self, released_by):
        """Return this opportunity to the unowned pool.

        Closes the active assignment row and nulls ``tracked_by``.
        """
        from django.utils import timezone

        self.assignments.filter(
            status__in=[
                OpportunityAssignment.Status.ASSIGNED,
                OpportunityAssignment.Status.IN_PROGRESS,
            ],
        ).update(
            status=OpportunityAssignment.Status.RELEASED,
            released_at=timezone.now(),
        )
        self.tracked_by = None
        self.save(update_fields=['tracked_by', 'updated_at'])


class TrackedOpportunityStatusHistory(AbstractStatusHistory):
    """Immutable audit trail of tracked opportunity status transitions."""

    tracked_opportunity = models.ForeignKey(
        TrackedOpportunity, on_delete=models.CASCADE, related_name='status_history',
    )

    class Meta(AbstractStatusHistory.Meta):
        verbose_name = _('Tracked Opportunity Status History')
        verbose_name_plural = _('Tracked Opportunity Status Histories')

    def __str__(self):
        return f"{self.tracked_opportunity}: {self.old_status} -> {self.new_status}"


class OpportunityCollaborator(AbstractCollaborator):
    """A collaborator invited to work on a tracked federal opportunity.

    Extends keel.core.models.AbstractCollaborator (canonical LEAD /
    CONTRIBUTOR / REVIEWER / OBSERVER role vocab, invite lifecycle,
    internal-user or external-email support).
    """

    tracked_opportunity = models.ForeignKey(
        TrackedOpportunity, on_delete=models.CASCADE,
        related_name='collaborators',
    )

    class Meta(AbstractCollaborator.Meta):
        verbose_name = _('Opportunity Collaborator')
        verbose_name_plural = _('Opportunity Collaborators')

    @property
    def display_name(self):
        if self.user:
            return self.user.get_full_name() or self.user.username
        return self.name or self.email


class OpportunityAssignment(AbstractAssignment):
    """Records the explicit claim of a tracked opportunity by a principal driver.

    Created on TrackedOpportunity creation (self-claim) and on explicit
    re-assignment / release. Keeps a history of who drove the opportunity
    and when; the TrackedOpportunity.tracked_by field is always the
    currently-active driver.
    """

    tracked_opportunity = models.ForeignKey(
        TrackedOpportunity, on_delete=models.CASCADE,
        related_name='assignments',
    )

    class Meta(AbstractAssignment.Meta):
        verbose_name = _('Opportunity Assignment')
        verbose_name_plural = _('Opportunity Assignments')


class OpportunityAttachment(AbstractAttachment):
    """Documents attached to a tracked opportunity during diligence.

    Extends keel.core.models.AbstractAttachment. Also the destination for
    signed PDFs returning from the Manifest roundtrip (source=MANIFEST_SIGNED).
    """

    tracked_opportunity = models.ForeignKey(
        TrackedOpportunity, on_delete=models.CASCADE,
        related_name='attachments',
    )

    class Meta(AbstractAttachment.Meta):
        verbose_name = _('Opportunity Attachment')
        verbose_name_plural = _('Opportunity Attachments')


# ---------------------------------------------------------------------------
# keel.activity concrete models -- re-exported for Django app discovery.
# Definitions in activity_models.py to keep this file from growing further.
# ---------------------------------------------------------------------------
from .activity_models import Activity, Watcher  # noqa: E402, F401
