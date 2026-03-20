from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from core.views import DashboardView

urlpatterns = [
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

    # AI matching
    path('matching/', include('matching.urls')),

    # Harbor integration
    path('integration/', include('integration.urls')),

    # API
    path('api/v1/', include('api.urls')),
]
