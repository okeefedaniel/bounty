"""Notification helpers for Bounty.

Delegates to Keel's centralized notification utilities for consistency
across the DockLabs portfolio.
"""
from keel.core.notifications import (  # noqa: F401
    build_absolute_url,
    create_notification,
    send_notification_email,
)
