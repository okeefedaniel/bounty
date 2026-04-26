from django.urls import path

from . import views

app_name = 'matching'

urlpatterns = [
    path('preferences/', views.MatchPreferenceView.as_view(), name='preferences'),
    path('state-preferences/', views.StatePreferenceView.as_view(), name='state-preferences'),
    path('recommendations/', views.RecommendedMatchesView.as_view(), name='recommendations'),
    path('recommendations/run/', views.RunMatchingView.as_view(), name='run-matching'),
    path('recommendations/mark-viewed/', views.MarkMatchesViewedView.as_view(), name='mark-matches-viewed'),
    path('dismiss/<uuid:pk>/', views.DismissMatchView.as_view(), name='dismiss-match'),
    path('track-dismiss/<uuid:pk>/', views.TrackAndDismissView.as_view(), name='track-and-dismiss'),
    path('feedback/<uuid:pk>/', views.MatchFeedbackView.as_view(), name='match-feedback'),
]
