import base64
import hashlib
import logging

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from keel.core.models import AbstractAuditLog, AbstractNotification
from keel.notifications.models import AbstractNotificationPreference, AbstractNotificationLog

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
        verbose_name = _('Bounty Profile')
        verbose_name_plural = _('Bounty Profiles')

    def __str__(self):
        return f"Profile: {self.user}"

    @staticmethod
    def _get_fernet():
        from cryptography.fernet import Fernet
        key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(key))

    def set_anthropic_api_key(self, raw_key):
        if not raw_key:
            self.anthropic_api_key = ''
            return
        encrypted = self._get_fernet().encrypt(raw_key.encode()).decode()
        self.anthropic_api_key = encrypted

    def get_anthropic_api_key(self):
        if not self.anthropic_api_key:
            return ''
        try:
            return self._get_fernet().decrypt(
                self.anthropic_api_key.encode()
            ).decode()
        except Exception:
            logger.warning('Failed to decrypt API key for user %s', self.user_id)
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
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')


class Notification(AbstractNotification):
    """Bounty in-app notification."""

    class Meta(AbstractNotification.Meta):
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')


class NotificationPreference(AbstractNotificationPreference):
    """Per-user notification channel preferences."""

    class Meta(AbstractNotificationPreference.Meta):
        verbose_name = _('Notification Preference')
        verbose_name_plural = _('Notification Preferences')


class NotificationLog(AbstractNotificationLog):
    """Notification delivery log."""

    class Meta(AbstractNotificationLog.Meta):
        verbose_name = _('Notification Log')
        verbose_name_plural = _('Notification Logs')
