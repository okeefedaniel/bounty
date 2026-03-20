from rest_framework import serializers

from matching.models import MatchPreference, OpportunityMatch
from opportunities.models import FederalOpportunity, TrackedOpportunity


class FederalOpportunitySerializer(serializers.ModelSerializer):
    is_open = serializers.BooleanField(read_only=True)
    days_until_close = serializers.IntegerField(read_only=True)

    class Meta:
        model = FederalOpportunity
        fields = [
            'id', 'opportunity_id', 'title', 'agency_name', 'description',
            'posted_date', 'close_date', 'award_floor', 'award_ceiling',
            'eligible_applicants', 'cfda_numbers', 'url',
            'is_open', 'days_until_close', 'created_at',
        ]


class TrackedOpportunitySerializer(serializers.ModelSerializer):
    federal_opportunity_title = serializers.CharField(
        source='federal_opportunity.title', read_only=True,
    )

    class Meta:
        model = TrackedOpportunity
        fields = [
            'id', 'federal_opportunity', 'federal_opportunity_title',
            'status', 'priority', 'notes',
            'harbor_push_status', 'harbor_program_id',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['harbor_push_status', 'harbor_program_id']


class MatchPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchPreference
        fields = [
            'id', 'focus_areas', 'min_funding', 'max_funding',
            'description', 'is_active', 'updated_at',
        ]


class OpportunityMatchSerializer(serializers.ModelSerializer):
    federal_opportunity_title = serializers.CharField(
        source='federal_opportunity.title', read_only=True,
    )

    class Meta:
        model = OpportunityMatch
        fields = [
            'id', 'federal_opportunity', 'federal_opportunity_title',
            'relevance_score', 'explanation', 'status', 'feedback',
            'created_at',
        ]
        read_only_fields = ['relevance_score', 'explanation']
