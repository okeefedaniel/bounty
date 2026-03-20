import base64
import hashlib
import logging
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from keel.core.models import AbstractAuditLog

logger = logging.getLogger(__name__)


class User(AbstractUser):
    """Custom user model for the Bounty platform."""

    class Role(models.TextChoices):
        ADMIN = 'admin', _('Administrator')
        COORDINATOR = 'coordinator', _('Federal Fund Coordinator')
        ANALYST = 'analyst', _('Grants Analyst')
        VIEWER = 'viewer', _('Viewer')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
    )
    title = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    organization_name = models.CharField(max_length=255, blank=True)

    anthropic_api_key = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name=_('Anthropic API Key'),
        help_text=_('Personal Claude API key for AI-powered matching.'),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def __str__(self):
        full = self.get_full_name()
        return full if full else self.username

    @property
    def is_coordinator(self):
        return self.role in {self.Role.ADMIN, self.Role.COORDINATOR}

    @property
    def is_analyst(self):
        return self.role in {self.Role.ADMIN, self.Role.COORDINATOR, self.Role.ANALYST}

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
            logger.warning('Failed to decrypt API key for user %s', self.pk)
            return ''

    @property
    def has_ai_access(self):
        return bool(self.anthropic_api_key)


class AuditLog(AbstractAuditLog):
    """Bounty audit log."""

    class Meta(AbstractAuditLog.Meta):
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')


class Notification(models.Model):
    """In-app notification."""

    class Priority(models.TextChoices):
        LOW = 'low', _('Low')
        MEDIUM = 'medium', _('Medium')
        HIGH = 'high', _('High')
        URGENT = 'urgent', _('Urgent')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM,
    )
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')

    def __str__(self):
        return f"{self.title} -> {self.recipient}"
