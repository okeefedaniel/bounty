from django.urls import path

from . import views

app_name = 'portal'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('opportunities/', views.OpportunityListView.as_view(), name='opportunities'),
    path('opportunities/<int:pk>/', views.OpportunityDetailView.as_view(), name='opportunity-detail'),
]
