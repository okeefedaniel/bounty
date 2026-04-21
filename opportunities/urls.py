from django.urls import path

from . import views

app_name = 'opportunities'

urlpatterns = [
    path('', views.TrackedOpportunityListView.as_view(), name='tracked-list'),
    path('add/', views.TrackOpportunityView.as_view(), name='tracked-add'),
    path('<uuid:pk>/', views.TrackedOpportunityDetailView.as_view(), name='tracked-detail'),
    path('<uuid:pk>/claim/', views.ClaimOpportunityView.as_view(), name='tracked-claim'),
    path('<uuid:pk>/release/', views.ReleaseOpportunityView.as_view(), name='tracked-release'),
    path('<uuid:pk>/edit/', views.TrackedOpportunityUpdateView.as_view(), name='tracked-update'),
    path('<uuid:pk>/collaborate/', views.AddCollaboratorView.as_view(), name='tracked-collaborate'),
    path(
        '<uuid:pk>/collaborate/<uuid:collab_pk>/remove/',
        views.RemoveCollaboratorView.as_view(),
        name='tracked-remove-collaborator',
    ),
    path('<uuid:pk>/attachments/', views.UploadAttachmentView.as_view(), name='tracked-attachment-upload'),
    path(
        '<uuid:pk>/attachments/<uuid:attachment_pk>/delete/',
        views.DeleteAttachmentView.as_view(),
        name='tracked-attachment-delete',
    ),
]
