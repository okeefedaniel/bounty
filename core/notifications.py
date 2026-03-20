"""Notification helpers for Bounty."""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import Notification

logger = logging.getLogger(__name__)


def create_notification(recipient, title, message, link='', priority='medium'):
    """Create an in-app notification."""
    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        link=link,
        priority=priority,
    )


def send_notification_email(recipient_email, subject, template_name, context):
    """Send an HTML notification email."""
    try:
        html_body = render_to_string(template_name, context)
        txt_template = template_name.replace('.html', '.txt')
        try:
            text_body = render_to_string(txt_template, context)
        except Exception:
            text_body = ''

        send_mail(
            subject=subject,
            message=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_body,
            fail_silently=True,
        )
    except Exception:
        logger.exception('Failed to send notification email to %s', recipient_email)


def build_absolute_url(path):
    """Build a full URL from a relative path."""
    from django.contrib.sites.models import Site
    try:
        domain = Site.objects.get_current().domain
    except Exception:
        domain = 'bounty.docklabs.ai'
    protocol = 'https'
    return f'{protocol}://{domain}{path}'
