from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import TemplateView

from keel.core.demo import demo_login_view

app_name = 'core'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('demo-login/', demo_login_view, name='demo-login'),
    path('pending-approval/', TemplateView.as_view(template_name='registration/pending_approval.html'), name='pending-approval'),
]
