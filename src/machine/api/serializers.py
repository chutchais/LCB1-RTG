from rest_framework import serializers
from machine.models import ConnectionStatus, Equipment


class ItemDataSerializer(serializers.Serializer):
    """Serializer for individual item data"""
    name = serializers.CharField()
    first_value = serializers.SerializerMethodField()
    last_value = serializers.SerializerMethodField()
    difference = serializers.SerializerMethodField()
    count = serializers.IntegerField()
    min = serializers.SerializerMethodField()
    max = serializers.SerializerMethodField()
    all_values = serializers.SerializerMethodField()
    
    def get_first_value(self, obj):
        return obj.get('first_value')
    
    def get_last_value(self, obj):
        return obj.get('last_value')
    
    def get_difference(self, obj):
        return obj.get('difference')
    
    def get_min(self, obj):
        return obj.get('min')
    
    def get_max(self, obj):
        return obj.get('max')
    
    def get_all_values(self, obj):
        return obj.get('all_values', [])


class EquipmentShiftDataSerializer(serializers.Serializer):
    """Serializer for equipment+shift grouped data"""
    equipment = serializers.CharField()
    shift = serializers.CharField()
    shift_label = serializers.CharField()
    first_record_time = serializers.DateTimeField()
    last_record_time = serializers.DateTimeField()
    record_count = serializers.IntegerField()
    duration_minutes = serializers.IntegerField()
    items = ItemDataSerializer(many=True)


class ItemsDataResponseSerializer(serializers.Serializer):
    """Main response serializer"""
    target_date = serializers.CharField()
    shift_filter = serializers.CharField()
    equipment_filter = serializers.CharField(required=False, allow_blank=True)
    equipment_stats = EquipmentShiftDataSerializer(many=True)
    total_records = serializers.IntegerField()
    timestamp = serializers.DateTimeField()


# ✅ NEW SERIALIZER - FOR CONNECTION STATUS RECORDS
class ConnectionStatusListSerializer(serializers.ModelSerializer):
    """Serializer for individual connection status records"""
    equipment_name = serializers.CharField(source='equipment.name', read_only=True)
    
    class Meta:
        model = ConnectionStatus
        fields = [
            'id',
            'equipment_name',
            'connection_status',
            'error_message',
            'items_data',
            'recorded_at',
            'shift',
            'shift_date',
            'created_at',
            'updated_at',
        ]