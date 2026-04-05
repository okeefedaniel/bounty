from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from django.views.generic import TemplateView

from .forms import LoginForm

app_name = 'core'

urlpatterns = [
    path(
        'login/',
        LoginView.as_view(
            template_name='registration/login.html',
            authentication_form=LoginForm,
        ),
        name='login',
    ),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('pending-approval/', TemplateView.as_view(template_name='registration/pending_approval.html'), name='pending-approval'),
]
