from django.contrib import admin

from .models import MatchPreference, OpportunityMatch


@admin.register(MatchPreference)
class MatchPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_active', 'updated_at')
    list_filter = ('is_active',)


@admin.register(OpportunityMatch)
class OpportunityMatchAdmin(admin.ModelAdmin):
    list_display = ('user', 'federal_opportunity', 'relevance_score', 'status', 'feedback')
    list_filter = ('status', 'feedback')
    search_fields = ('user__username', 'federal_opportunity__title')
