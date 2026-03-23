"""Custom allauth adapter — admin approval required for new accounts.

New users sign up normally but are set to is_active=False until an
admin approves them via the Django admin panel.
"""
import logging

from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.shortcuts import resolve_url

logger = logging.getLogger(__name__)


class ApprovalRequiredAdapter(DefaultAccountAdapter):
    """Deactivate new accounts until an admin approves them."""

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        user.is_active = False
        user.role = 'viewer'  # Default role for self-registered users
        if commit:
            user.save()
        logger.info('New signup pending approval: %s (%s)', user.username, user.email)
        return user

    def is_open_for_signup(self, request):
        """Allow public signup (overrides ACCOUNT_SIGNUP_ENABLED if it were set)."""
        return True

    def get_signup_redirect_url(self, request):
        """After signup, redirect to pending-approval page."""
        return resolve_url('core:pending-approval')

    def login(self, request, user):
        """Prevent auto-login after signup for inactive users."""
        if not user.is_active:
            return  # Don't log in — redirect will handle it
        return super().login(request, user)
