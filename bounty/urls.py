import traceback

from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from django.views.generic import RedirectView

from core.views import DashboardView


def _debug_login_test(request):
    """Temporary: render login template with full error capture."""
    try:
        from allauth.account import views as allauth_views
        view = allauth_views.LoginView.as_view(template_name='registration/login.html')
        response = view(request)
        # Force lazy TemplateResponse to render so we catch template errors
        if hasattr(response, 'render'):
            response.render()
        return response
    except Exception:
        return HttpResponse(
            '<pre>' + traceback.format_exc() + '</pre>',
            content_type='text/plain',
        )


urlpatterns = [
    path('debug-login/', _debug_login_test),
    path('admin/', admin.site.urls),

    # Portal (public pages)
    path('', include('opportunities.portal_urls')),

    # Auth
    path('auth/', include('core.urls')),
    path('accounts/', include('allauth.urls')),

    # Convenience named URL for the "Sign in with Microsoft" button
    path(
        'auth/sso/microsoft/',
        RedirectView.as_view(url='/accounts/microsoft/login/?process=login', query_string=False),
        name='microsoft_login',
    ),

    # Dashboard
    path('dashboard/', DashboardView.as_view(), name='dashboard'),

    # Tracked opportunities (coordinator pipeline)
    path('tracked/', include('opportunities.urls')),

    # Notifications
    path('notifications/', include('keel.notifications.urls')),

    # Feedback / change requests (beta testers + admins)
    path('feedback/', include('keel.requests.urls')),

    # AI matching
    path('matching/', include('matching.urls')),

    # Harbor integration
    path('integration/', include('integration.urls')),

    # API
    path('api/v1/', include('api.urls')),
]
