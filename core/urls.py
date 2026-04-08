from django.contrib.auth.views import LoginView
from django.urls import path
from django.views.generic import TemplateView

from keel.core.views import SuiteLogoutView

from .forms import LoginForm

app_name = 'core'

urlpatterns = [
    path(
        'login/',
        LoginView.as_view(
            template_name='account/login.html',
            authentication_form=LoginForm,
        ),
        name='login',
    ),
    path('logout/', SuiteLogoutView.as_view(), name='logout'),
    path('pending-approval/', TemplateView.as_view(template_name='registration/pending_approval.html'), name='pending-approval'),
]
