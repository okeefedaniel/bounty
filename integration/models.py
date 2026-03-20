import uuid

from django.conf import settings
from django.db import models


class HarborConnection(models.Model):
    """Stores per-user Harbor API connection settings for pushing opportunities."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='harbor_connection',
    )
    harbor_base_url = models.URLField(
        default='https://harbor.docklabs.ai',
        help_text='Base URL for the Harbor instance',
    )
    harbor_api_token = models.CharField(
        max_length=255,
        blank=True,
        help_text='API token for authenticating with Harbor',
    )
    is_active = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Harbor Connection'
        verbose_name_plural = 'Harbor Connections'

    def __str__(self):
        return f'{self.user.username} → {self.harbor_base_url}'
