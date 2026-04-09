from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views
from .helm_feed import bounty_helm_feed

router = DefaultRouter()
router.register(r'opportunities', views.FederalOpportunityViewSet)
router.register(r'tracked', views.TrackedOpportunityViewSet, basename='tracked')
router.register(r'preferences', views.MatchPreferenceViewSet, basename='preferences')
router.register(r'matches', views.OpportunityMatchViewSet, basename='matches')

app_name = 'api'

urlpatterns = [
    path('helm-feed/', bounty_helm_feed, name='helm-feed'),
    path('', include(router.urls)),
]
