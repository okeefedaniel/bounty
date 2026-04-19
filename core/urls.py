from django.urls import path
from django.views.generic import TemplateView

app_name = 'core'

urlpatterns = [
    path('pending-approval/', TemplateView.as_view(template_name='registration/pending_approval.html'), name='pending-approval'),
]
