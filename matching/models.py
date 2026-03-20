import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class MatchPreference(models.Model):
    """User preferences for AI-powered federal grant matching."""

    class FocusArea(models.TextChoices):
        EDUCATION = 'education', _('Education')
        HEALTH = 'health', _('Health & Human Services')
        ENVIRONMENT = 'environment', _('Environment & Energy')
        INFRASTRUCTURE = 'infrastructure', _('Infrastructure & Transportation')
        PUBLIC_SAFETY = 'public_safety', _('Public Safety')
        HOUSING = 'housing', _('Housing & Community Development')
        ECONOMIC_DEV = 'economic_dev', _('Economic Development')
        ARTS_CULTURE = 'arts_culture', _('Arts & Culture')
        TECHNOLOGY = 'technology', _('Technology & Innovation')
        AGRICULTURE = 'agriculture', _('Agriculture & Food')
        WORKFORCE = 'workforce', _('Workforce Development')
        JUSTICE = 'justice', _('Justice & Legal Services')
        OTHER = 'other', _('Other')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='match_preference',
    )
    focus_areas = models.JSONField(default=list, blank=True)
    funding_range_min = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )
    funding_range_max = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Match Preference')
        verbose_name_plural = _('Match Preferences')

    def __str__(self):
        return f"Preferences for {self.user}"


class OpportunityMatch(models.Model):
    """AI-scored match linking a user to a federal opportunity."""

    class Status(models.TextChoices):
        NEW = 'new', _('New')
        VIEWED = 'viewed', _('Viewed')
        SAVED = 'saved', _('Saved')
        DISMISSED = 'dismissed', _('Dismissed')

    class Feedback(models.TextChoices):
        POSITIVE = 'positive', _('Positive')
        NEGATIVE = 'negative', _('Negative')

    class FeedbackReason(models.TextChoices):
        WRONG_FOCUS = 'wrong_focus', _('Wrong focus area')
        BUDGET_TOO_LARGE = 'budget_too_large', _('Budget too large')
        BUDGET_TOO_SMALL = 'budget_too_small', _('Budget too small')
        ALREADY_AWARE = 'already_aware', _('Already aware of this')
        NOT_ELIGIBLE = 'not_eligible', _('Not eligible')
        NOT_RELEVANT = 'not_relevant', _('Not relevant to our mission')
        OTHER = 'other', _('Other')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='opportunity_matches',
    )
    federal_opportunity = models.ForeignKey(
        'opportunities.FederalOpportunity', on_delete=models.CASCADE,
        related_name='matches',
    )
    relevance_score = models.IntegerField(
        help_text=_('AI relevance score from 0 to 100'),
    )
    explanation = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.NEW,
    )
    notified = models.BooleanField(default=False)
    notified_at = models.DateTimeField(null=True, blank=True)
    feedback = models.CharField(
        max_length=10, choices=Feedback.choices, blank=True, default='',
    )
    feedback_reason = models.CharField(
        max_length=20, choices=FeedbackReason.choices, blank=True, default='',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-relevance_score', '-created_at']
        verbose_name = _('Opportunity Match')
        verbose_name_plural = _('Opportunity Matches')
        indexes = [
            models.Index(fields=['user', 'status'], name='idx_oppmatch_user_status'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'federal_opportunity'],
                name='unique_user_federal_match',
            ),
        ]

    def __str__(self):
        return f"{self.user} — {self.federal_opportunity.title[:50]} ({self.relevance_score}%)"

    @property
    def opportunity_title(self):
        return self.federal_opportunity.title

    @property
    def opportunity_url(self):
        from django.urls import reverse
        return reverse('portal:opportunity-detail', kwargs={'pk': self.federal_opportunity.pk})
