from django.apps import AppConfig


class OpportunitiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'opportunities'

    def ready(self):
        # Wire the packet_approved receiver that files the signed PDF and
        # transitions status when a Manifest handoff completes.
        from . import signals  # noqa: F401
        # Register keel.activity Track A promotion rules.
        # Phase 1A Week 5 / Phase 1C — Bounty is the third non-pilot peer.
        try:
            from opportunities.activity_promotions import register_all
            register_all()
        except ImportError:
            pass
