import logging

from cryptography.fernet import InvalidToken
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from keel.core.models import AbstractAuditLog, AbstractNotification
from keel.notifications.models import AbstractNotificationPreference, AbstractNotificationLog
from keel.security import encryption

logger = logging.getLogger(__name__)


class BountyProfile(models.Model):
    """Product-specific fields for Bounty users.

    KeelUser handles identity (email, name, agency). BountyProfile stores
    Bounty-specific data that doesn't belong on the shared user model.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='bounty_profile',
    )
    organization_name = models.CharField(max_length=255, blank=True)
    anthropic_api_key = models.CharField(
        max_length=255, blank=True, default='',
        verbose_name=_('Anthropic API Key'),
    )

    class Meta:
        db_table = 'bounty_core_bountyprofile'
        verbose_name = _('Bounty Profile')
        verbose_name_plural = _('Bounty Profiles')

    def __str__(self):
        return f"Profile: {self.user}"

    def set_anthropic_api_key(self, raw_key):
        """Encrypt ``raw_key`` under the active KEEL_ENCRYPTION_KEYS primary."""
        if not raw_key:
            self.anthropic_api_key = ''
            return
        self.anthropic_api_key = encryption.encrypt(raw_key)

    def get_anthropic_api_key(self):
        """Decrypt under any configured key (for rotation overlap).

        Tolerates ``InvalidToken`` so a stale ciphertext blocked by a
        rotation gap returns an empty string instead of raising; the AI
        scorer falls back to ``settings.ANTHROPIC_API_KEY`` in that case.
        """
        if not self.anthropic_api_key:
            return ''
        try:
            return encryption.decrypt(self.anthropic_api_key)
        except InvalidToken:
            logger.warning(
                'Failed to decrypt anthropic_api_key for user %s — token is '
                'not under any configured KEEL_ENCRYPTION_KEYS. If you just '
                'rotated keys, set KEEL_ENCRYPTION_LEGACY_SECRET_KEY_FALLBACK=true '
                'until you have run rotate_anthropic_keys.',
                self.user_id,
            )
            return ''

    @property
    def has_ai_access(self):
        return bool(self.anthropic_api_key) or bool(getattr(settings, 'ANTHROPIC_API_KEY', ''))


def get_bounty_profile(user):
    """Get or create BountyProfile for a user."""
    profile, _ = BountyProfile.objects.get_or_create(user=user)
    return profile


class AuditLog(AbstractAuditLog):
    """Bounty audit log."""

    class Meta(AbstractAuditLog.Meta):
        db_table = 'bounty_core_auditlog'
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')


class Notification(AbstractNotification):
    """Bounty in-app notification."""

    class Meta(AbstractNotification.Meta):
        db_table = 'bounty_core_notification'
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')


class NotificationPreference(AbstractNotificationPreference):
    """Per-user notification channel preferences."""

    class Meta(AbstractNotificationPreference.Meta):
        db_table = 'bounty_core_notificationpreference'
        verbose_name = _('Notification Preference')
        verbose_name_plural = _('Notification Preferences')


class NotificationLog(AbstractNotificationLog):
    """Notification delivery log."""

    class Meta(AbstractNotificationLog.Meta):
        db_table = 'bounty_core_notificationlog'
        verbose_name = _('Notification Log')
        verbose_name_plural = _('Notification Logs')
