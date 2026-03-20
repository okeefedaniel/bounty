from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from matching.models import MatchPreference, OpportunityMatch
from opportunities.models import FederalOpportunity, TrackedOpportunity

from .serializers import (
    FederalOpportunitySerializer,
    MatchPreferenceSerializer,
    OpportunityMatchSerializer,
    TrackedOpportunitySerializer,
)


class FederalOpportunityViewSet(viewsets.ReadOnlyModelViewSet):
    """Browse federal opportunities (read-only)."""

    queryset = FederalOpportunity.objects.all().order_by('-posted_date')
    serializer_class = FederalOpportunitySerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def open(self, request):
        """List only open opportunities."""
        from django.utils import timezone

        qs = self.get_queryset().filter(close_date__gte=timezone.now().date())
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class TrackedOpportunityViewSet(viewsets.ModelViewSet):
    """Manage tracked opportunities for the authenticated user."""

    serializer_class = TrackedOpportunitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TrackedOpportunity.objects.filter(
            tracked_by=self.request.user,
        ).select_related('federal_opportunity').order_by('-updated_at')

    def perform_create(self, serializer):
        serializer.save(tracked_by=self.request.user)


class MatchPreferenceViewSet(viewsets.ModelViewSet):
    """Manage AI match preferences for the authenticated user."""

    serializer_class = MatchPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MatchPreference.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class OpportunityMatchViewSet(viewsets.ReadOnlyModelViewSet):
    """View AI-generated opportunity matches."""

    serializer_class = OpportunityMatchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return OpportunityMatch.objects.filter(
            user=self.request.user,
        ).select_related('federal_opportunity').order_by('-relevance_score')
