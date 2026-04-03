import logging
import traceback

from allauth.account import views as allauth_views
from django.contrib.auth import views as auth_views
from django.http import HttpResponse
from django.urls import path
from django.views.generic import TemplateView

from keel.core.demo import demo_login_view

logger = logging.getLogger(__name__)

app_name = 'core'


def _debug_login(request):
    """Temporary wrapper to capture login page errors."""
    try:
        view = allauth_views.LoginView.as_view(template_name='registration/login.html')
        return view(request)
    except Exception:
        tb = traceback.format_exc()
        logger.error('Login page error:\n%s', tb)
        return HttpResponse(f'<pre>{tb}</pre>', status=500, content_type='text/html')


urlpatterns = [
    path('login/', _debug_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('demo-login/', demo_login_view, name='demo-login'),
    path('pending-approval/', TemplateView.as_view(template_name='registration/pending_approval.html'), name='pending-approval'),
]
