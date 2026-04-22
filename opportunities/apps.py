from django.apps import AppConfig


class OpportunitiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'opportunities'

    def ready(self):
        # Wire the packet_approved receiver that files the signed PDF and
        # transitions status when a Manifest handoff completes.
        from . import signals  # noqa: F401
