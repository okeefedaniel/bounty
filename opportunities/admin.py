from django.contrib import admin

from .models import FederalOpportunity, OpportunityCollaborator, TrackedOpportunity


class OpportunityCollaboratorInline(admin.TabularInline):
    model = OpportunityCollaborator
    extra = 0
    readonly_fields = ('invited_at',)


@admin.register(FederalOpportunity)
class FederalOpportunityAdmin(admin.ModelAdmin):
    list_display = ('opportunity_id', 'title', 'agency_code', 'opportunity_status', 'close_date')
    list_filter = ('opportunity_status', 'funding_instrument')
    search_fields = ('title', 'opportunity_id', 'opportunity_number', 'agency_name')
    readonly_fields = ('synced_at', 'raw_data')


@admin.register(TrackedOpportunity)
class TrackedOpportunityAdmin(admin.ModelAdmin):
    list_display = ('federal_opportunity', 'tracked_by', 'status', 'priority', 'harbor_push_status')
    list_filter = ('status', 'priority', 'harbor_push_status')
    inlines = [OpportunityCollaboratorInline]
