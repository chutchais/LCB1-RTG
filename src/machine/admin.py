from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from datetime import timedelta
from django.utils import timezone
import json

# Register your models here.
from .models import Equipment,Item,DataLogger,ConnectionStatus

class ItemInline(admin.TabularInline):
	model = Item
	fields = ('seq','name','parameter','monitor','units','current_value')
	autocomplete_fields = ['parameter']
	extra = 1 # how many rows to show
	show_change_link = True

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
	search_fields = ['name','title','ip']
	list_filter = []
	list_display = ('name','title','ip','created','user')

	readonly_fields = ('created','updated','user')

	inlines = [
        ItemInline,
    ]
	save_as = True
	save_as_continue = True
	save_on_top =True
	list_select_related = True

	fieldsets = [
		('Basic Information',{'fields': ['name','title','ip']}),
		('System Information',{'fields':[('user','created'),'updated']})
	]

@admin.register(DataLogger)
class DataLoggerAdmin(admin.ModelAdmin):
	search_fields = ['item__equipment__name','item__parameter__name']
	list_filter = ['item__equipment__name','item__parameter__name']
	list_display = ('item','last_value','current_value','created')
	readonly_fields = ('created','updated')


	fieldsets = [
		('Basic Information',{'fields': ['item','last_value','current_value']}),
		('System Information',{'fields':['created','updated']})
	]

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from machine.models import ConnectionStatus
import json


@admin.register(ConnectionStatus)
class ConnectionStatusAdmin(admin.ModelAdmin):
    """
    Admin interface for Connection Status tracking
    Shows connection health timeline with shift information and item data
    """
    
    # List display
    list_display = [
        'get_equipment_name',
        'get_status_badge',
        'get_shift_badge',
        'shift_date',
        'recorded_at',
        'get_item_count',
        'error_message_short'
    ]
    
    # Filters
    list_filter = [
        'connection_status',
        'shift',
        'shift_date',
        'recorded_at',
        'equipment__name',
    ]
    
    # Search
    search_fields = [
        'equipment__name',
        'error_message',
    ]
    
    # Read-only fields
    readonly_fields = [
        'created_at',
        'updated_at',
        'get_items_table',
        'get_shift_info',
        'get_status_summary',
        'get_equipment_info',
    ]
    
    # Fieldsets - organize form into sections
    fieldsets = (
        ('Equipment & Status', {
            'fields': (
                'get_equipment_info',
                'connection_status',
                'get_status_summary',
            )
        }),
        ('Error Information', {
            'fields': (
                'error_message',
            ),
            'classes': ('collapse',),
        }),
        ('Shift Information', {
            'fields': (
                'shift',
                'shift_date',
                'get_shift_info',
            )
        }),
        ('Timing', {
            'fields': (
                'recorded_at',
                'created_at',
                'updated_at',
            )
        }),
        ('Item Data', {
            'fields': (
                'items_data',
                'get_items_table',
            ),
            'description': 'Detailed item readings from this connection attempt',
        }),
    )
    
    # Ordering
    ordering = ['-recorded_at']
    
    # Date hierarchy
    # date_hierarchy = 'recorded_at'
    
    # Pagination
    list_per_page = 50
    
    # Actions
    actions = [
        'export_as_json',
        'export_morning_shift',
        'export_night_shift',
    ]
    
    # ===== Display Methods =====
    
    def get_equipment_name(self, obj):
        """Display equipment name - click to view this record's detail"""
        url = reverse('admin:machine_connectionstatus_change', args=[obj.id])
        status_icon = {
            'success': '✓',
            'failed': '✗',
            'timeout': '⏱',
            'partial': '◐',
        }.get(obj.connection_status, '?')
        
        return format_html(
            '<a href="{}">{} {} ({})</a>',
            url,
            status_icon,
            obj.equipment.name,
            obj.get_connection_status_display()
        )
    get_equipment_name.short_description = 'Equipment'
    
    def get_equipment_info(self, obj):
        """Display equipment information in readonly field"""
        url = reverse('admin:machine_equipment_change', args=[obj.equipment.id])
        html = f'<div style="padding: 10px; background: #f5f5f5; border-radius: 4px; border-left: 4px solid #667eea;">'
        html += f'<strong>Equipment:</strong> <a href="{url}" target="_blank">{obj.equipment.name}</a><br>'
        html += f'<strong>IP Address:</strong> {obj.equipment.ip}<br>'
        html += f'<strong>Equipment ID:</strong> {obj.equipment.id}'
        html += '</div>'
        
        return format_html(html)
    get_equipment_info.short_description = 'Equipment Information'
    
    def get_status_badge(self, obj):
        """Display connection status as colored badge"""
        colors = {
            'success': '#4caf50',
            'failed': '#f44336',
            'timeout': '#ff9800',
            'partial': '#2196f3',
        }
        color = colors.get(obj.connection_status, '#999')
        
        icons = {
            'success': '✓',
            'failed': '✗',
            'timeout': '⏱️',
            'partial': '◐',
        }
        icon = icons.get(obj.connection_status, '?')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_connection_status_display()
        )
    get_status_badge.short_description = 'Status'
    
    def get_shift_badge(self, obj):
        """Display shift as colored badge"""
        color = '#667eea' if obj.shift == 'morning' else '#8b5fbf'
        icon = '🌅' if obj.shift == 'morning' else '🌙'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_shift_display()
        )
    get_shift_badge.short_description = 'Shift'
    
    def get_item_count(self, obj):
        """Display number of items recorded"""
        count = len(obj.items_data) if obj.items_data else 0
        if count > 0:
            return format_html(
                '<span style="background-color: #e3f2fd; color: #1976d2; padding: 3px 8px; border-radius: 3px; font-size: 0.9em;"><strong>{}</strong> items</span>',
                count
            )
        return format_html(
            '<span style="color: #999;">No items</span>'
        )
    get_item_count.short_description = 'Items'
    
    def error_message_short(self, obj):
        """Display truncated error message"""
        if obj.error_message:
            msg = obj.error_message[:50] + ('...' if len(obj.error_message) > 50 else '')
            return format_html(
                '<span style="color: #f44336; font-size: 0.9em;"><strong>⚠️</strong> {}</span>',
                msg
            )
        return '-'
    error_message_short.short_description = 'Error'
    
    def get_status_summary(self, obj):
        """Display status summary in readonly field"""
        color = {
            'success': '#4caf50',
            'failed': '#f44336',
            'timeout': '#ff9800',
            'partial': '#2196f3',
        }.get(obj.connection_status, '#999')
        
        status_text = obj.get_connection_status_display()
        
        html = f'<div style="padding: 10px; background: {color}; color: white; border-radius: 4px; font-weight: bold; text-align: center;">'
        html += f'{status_text}'
        html += '</div>'
        
        if obj.error_message:
            html += f'<p style="color: #f44336; margin-top: 10px; padding: 10px; background: #ffebee; border-radius: 4px;"><strong>❌ Error:</strong><br>{obj.error_message}</p>'
        
        return format_html(html)
    get_status_summary.short_description = 'Status Summary'
    
    def get_shift_info(self, obj):
        """Display shift information"""
        shift_label = 'Morning (08:00 - 20:00)' if obj.shift == 'morning' else 'Night (20:00 - 08:00)'
        shift_icon = '🌅' if obj.shift == 'morning' else '🌙'
        
        info = f'<div style="padding: 10px; background: #f5f5f5; border-radius: 4px;">'
        info += f'<strong>{shift_icon} Shift:</strong> {shift_label}<br>'
        info += f'<strong>📅 Shift Date:</strong> {obj.shift_date.strftime("%Y-%m-%d (%A)")}<br>'
        info += f'<strong>⏰ Recorded At:</strong> {obj.recorded_at.strftime("%Y-%m-%d %H:%M:%S")}'
        info += '</div>'
        
        return format_html(info)
    get_shift_info.short_description = 'Shift Details'
    
    def get_items_table(self, obj):
        """Display items data in formatted table"""
        if not obj.items_data or len(obj.items_data) == 0:
            return format_html('<em style="color: #999;">No item data recorded</em>')
        
        html = '<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">'
        html += '<thead><tr style="background-color: #667eea; color: white; border: 1px solid #ddd;">'
        html += '<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Item Name</th>'
        html += '<th style="padding: 12px; text-align: right; border: 1px solid #ddd;">Value</th>'
        html += '<th style="padding: 12px; text-align: center; border: 1px solid #ddd;">Type</th>'
        html += '</tr></thead>'
        html += '<tbody>'
        
        for idx, (key, value) in enumerate(sorted(obj.items_data.items()), 1):
            # Format value based on type
            if isinstance(value, int):
                formatted_value = f'{value:,}'
                value_color = '#4caf50'
                value_type = 'Integer'
            elif isinstance(value, float):
                formatted_value = f'{value:.2f}'
                value_color = '#2196f3'
                value_type = 'Float'
            elif isinstance(value, bool):
                formatted_value = '✓ Yes' if value else '✗ No'
                value_color = '#ff9800'
                value_type = 'Boolean'
            else:
                formatted_value = str(value)
                value_color = '#333'
                value_type = 'Text'
            
            bg_color = '#f9f9f9' if idx % 2 == 0 else '#ffffff'
            
            html += f'<tr style="background-color: {bg_color}; border: 1px solid #ddd;">'
            html += f'<td style="padding: 10px; border: 1px solid #ddd; font-weight: 500;">{key}</td>'
            html += f'<td style="padding: 10px; text-align: right; border: 1px solid #ddd; color: {value_color}; font-weight: bold; font-size: 1.05em;">{formatted_value}</td>'
            html += f'<td style="padding: 10px; text-align: center; border: 1px solid #ddd; color: #666; font-size: 0.85em;">{value_type}</td>'
            html += '</tr>'
        
        html += '</tbody></table>'
        
        # Add summary
        html += f'<p style="margin-top: 15px; padding: 10px; background: #e3f2fd; border-radius: 4px; color: #1976d2;"><strong>ℹ️ Summary:</strong> {len(obj.items_data)} items recorded</p>'
        
        return format_html(html)
    get_items_table.short_description = 'Item Data Table'
    
    # ===== Customization =====
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('equipment')
    
    def has_add_permission(self, request):
        """Prevent manual creation (auto-created by read_item_data)"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup"""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """Allow viewing but prevent editing"""
        if obj is None:
            return True
        # Can only view, not edit
        return False
    
    # ===== Actions =====
    
    def export_as_json(self, request, queryset):
        """Export selected records as JSON"""
        import json
        from django.http import HttpResponse
        
        data = []
        for obj in queryset:
            data.append({
                'id': obj.id,
                'equipment': obj.equipment.name,
                'equipment_ip': obj.equipment.ip,
                'connection_status': obj.connection_status,
                'shift': obj.shift,
                'shift_date': obj.shift_date.isoformat(),
                'recorded_at': obj.recorded_at.isoformat(),
                'created_at': obj.created_at.isoformat(),
                'error_message': obj.error_message,
                'items_data': obj.items_data,
            })
        
        response = HttpResponse(
            json.dumps(data, indent=2, default=str),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename="connection_status.json"'
        return response
    export_as_json.short_description = '📥 Export selected as JSON'
    
    def export_morning_shift(self, request, queryset):
        """Export morning shift data as JSON"""
        import json
        from django.http import HttpResponse
        
        data = []
        for obj in queryset.filter(shift='morning'):
            data.append({
                'equipment': obj.equipment.name,
                'connection_status': obj.connection_status,
                'shift_date': obj.shift_date.isoformat(),
                'recorded_at': obj.recorded_at.isoformat(),
                'items_data': obj.items_data,
            })
        
        response = HttpResponse(
            json.dumps(data, indent=2, default=str),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename="morning_shift.json"'
        return response
    export_morning_shift.short_description = '🌅 Export morning shift'
    
    def export_night_shift(self, request, queryset):
        """Export night shift data as JSON"""
        import json
        from django.http import HttpResponse
        
        data = []
        for obj in queryset.filter(shift='night'):
            data.append({
                'equipment': obj.equipment.name,
                'connection_status': obj.connection_status,
                'shift_date': obj.shift_date.isoformat(),
                'recorded_at': obj.recorded_at.isoformat(),
                'items_data': obj.items_data,
            })
        
        response = HttpResponse(
            json.dumps(data, indent=2, default=str),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename="night_shift.json"'
        return response
    export_night_shift.short_description = '🌙 Export night shift'
