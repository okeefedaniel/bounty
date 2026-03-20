from django.urls import path

from . import views

app_name = 'integration'

urlpatterns = [
    path('harbor/settings/', views.HarborConnectionSettingsView.as_view(), name='harbor-settings'),
    path('harbor/push/<uuid:pk>/', views.PushToHarborView.as_view(), name='push-to-harbor'),
]
