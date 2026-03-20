from django.urls import path

from . import views

app_name = 'matching'

urlpatterns = [
    path('preferences/', views.MatchPreferenceView.as_view(), name='preferences'),
    path('recommendations/', views.RecommendedMatchesView.as_view(), name='recommendations'),
    path('dismiss/<uuid:pk>/', views.DismissMatchView.as_view(), name='dismiss-match'),
    path('track-dismiss/<uuid:pk>/', views.TrackAndDismissView.as_view(), name='track-and-dismiss'),
    path('feedback/<uuid:pk>/', views.MatchFeedbackView.as_view(), name='match-feedback'),
]
