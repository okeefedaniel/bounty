from django.contrib import admin
from django.contrib.auth.views import LoginView
from django.urls import include, path
from django.views.generic import RedirectView

from django.views.generic import TemplateView

from core.forms import LoginForm
from core.views import DashboardView
from keel.core.demo import demo_login_view
from keel.core.views import SuiteLogoutView, favicon_view, health_check, robots_txt
from keel.core.search_views import search_view

urlpatterns = [
    # Support (shared keel page — linked from 500.html)
    path('support/', TemplateView.as_view(template_name='keel/support.html'), name='support'),
    path('health/', health_check, name='health_check'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('favicon.ico', favicon_view, name='favicon'),
    path('demo-login/', demo_login_view, name='demo_login'),
    path('admin/', admin.site.urls),

    # Portal (public pages)
    path('', include('opportunities.portal_urls')),

    # Auth
    # Canonical login lives at /accounts/login/. The legacy /auth/login/
    # path is preserved as a 301 to keep old bookmarks and inbound links
    # working. Pattern is mounted BEFORE the auth/ include so it wins
    # the resolver match. (ISSUE-019)
    path(
        'auth/login/',
        RedirectView.as_view(url='/accounts/login/', permanent=True),
    ),
    path('auth/', include('core.urls')),
    # Custom login/logout views using our styled templates (before allauth)
    # so /accounts/login/ uses the shared keel LoginForm (which sets
    # form-control on its widgets) instead of allauth's default form.
    path('accounts/login/', LoginView.as_view(
        template_name='account/login.html',
        authentication_form=LoginForm,
    ), name='account_login'),
    path('accounts/logout/', SuiteLogoutView.as_view(), name='account_logout'),
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

    # Manifest signing handoff (inbound webhook)
    path('keel/signatures/', include('keel.signatures.urls')),

    # AI matching
    path('matching/', include('matching.urls')),

    # Harbor integration
    path('integration/', include('integration.urls')),

    # API
    path('api/v1/', include('api.urls')),

    # Keel accounts admin
    path('search/', search_view, name='search'),
    path('keel/', include('keel.accounts.urls')),
]
