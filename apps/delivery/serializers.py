"""
NexCart Delivery Serializers
"""
from rest_framework import serializers
from .models import DeliveryZone, DeliveryArea


class DeliveryAreaSerializer(serializers.ModelSerializer):
    total_delivery_fee = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = DeliveryArea
        fields = ['id', 'name', 'city', 'surcharge', 'total_delivery_fee']


class DeliveryZoneSerializer(serializers.ModelSerializer):
    areas = DeliveryAreaSerializer(many=True, read_only=True)

    class Meta:
        model = DeliveryZone
        fields = [
            'id', 'name', 'region', 'description', 'base_fee',
            'free_delivery_threshold', 'estimated_days_min',
            'estimated_days_max', 'areas'
        ]


class DeliveryEstimateSerializer(serializers.Serializer):
    area_id = serializers.UUIDField(required=False)
    city = serializers.CharField(required=False)
    order_total = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)
