from django.contrib import admin

from .models import AuditLog, BountyProfile, Notification


@admin.register(BountyProfile)
class BountyProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization_name')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'entity_type', 'entity_id')
    list_filter = ('action', 'entity_type')
    readonly_fields = ('id', 'user', 'action', 'entity_type', 'entity_id',
                       'description', 'changes', 'ip_address', 'timestamp')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'priority', 'is_read', 'created_at')
    list_filter = ('priority', 'is_read')
