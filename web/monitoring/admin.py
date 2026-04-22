from django.contrib import admin
from .models import Machine, TagConfig, TagLatestSnapshot, RawDataPool

@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ('machine_name', 'description')
    search_fields = ('machine_name',)

@admin.register(TagConfig)
class TagConfigAdmin(admin.ModelAdmin):
    list_display = ('tag_name', 'machine', 'opc_address', 'is_active', 'deadband')
    list_filter = ('machine', 'is_active')
    search_fields = ('tag_name', 'opc_address')
    list_editable = ('is_active', 'deadband')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('machine', 'tag_name', 'opc_address', 'description')
        }),
        ('Monitoring Settings', {
            'fields': ('is_active', 'deadband', 'update_interval')
        }),
    )

@admin.register(TagLatestSnapshot)
class TagLatestSnapshotAdmin(admin.ModelAdmin):
    list_display = ('tag', 'last_value', 'last_status', 'last_update')
    list_filter = ('last_status',)
    readonly_fields = ('tag', 'last_value', 'last_status', 'last_update')

@admin.register(RawDataPool)
class RawDataPoolAdmin(admin.ModelAdmin):
    list_display = ('tag', 'tag_value', 'status_code', 'timestamp')
    list_filter = ('tag__machine', 'status_code')
    readonly_fields = ('tag', 'tag_value', 'status_code', 'timestamp')
    
    def has_add_permission(self, request):
        return False # History is read-only in admin
