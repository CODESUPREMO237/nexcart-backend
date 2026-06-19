"""
NexCart Coupon Serializers
"""
from rest_framework import serializers
from .models import Coupon, CouponUsage


class CouponSerializer(serializers.ModelSerializer):
    is_valid = serializers.BooleanField(read_only=True)
    vendor_name = serializers.CharField(source='vendor.store_name', read_only=True, default=None)

    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'description', 'discount_type', 'discount_value',
            'min_order_amount', 'max_discount_amount', 'max_uses',
            'used_count', 'valid_from', 'valid_until', 'is_active',
            'is_valid', 'vendor', 'vendor_name'
        ]


class CouponValidateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    order_total = serializers.DecimalField(max_digits=10, decimal_places=2)
