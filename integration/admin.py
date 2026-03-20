from django.contrib import admin

from .models import HarborConnection


@admin.register(HarborConnection)
class HarborConnectionAdmin(admin.ModelAdmin):
    list_display = ('user', 'harbor_base_url', 'is_active', 'last_synced_at')
    list_filter = ('is_active',)
