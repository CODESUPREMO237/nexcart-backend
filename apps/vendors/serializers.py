"""
NexCart Vendor Serializers
"""
from rest_framework import serializers
from .models import Vendor, VendorPayout


class VendorSerializer(serializers.ModelSerializer):
    """Public vendor serializer"""
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Vendor
        fields = [
            'id', 'store_name', 'slug', 'description', 'logo_url',
            'city', 'region', 'average_rating', 'total_products',
            'is_verified', 'created_at', 'user_name'
        ]

    def get_logo_url(self, obj):
        if obj.logo and obj.logo.name:
            if str(obj.logo.name).startswith('http'):
                return obj.logo.name
            try:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.logo.url)
                return obj.logo.url
            except Exception:
                return None
        return None


class VendorRegistrationSerializer(serializers.ModelSerializer):
    """Vendor registration serializer"""
    class Meta:
        model = Vendor
        fields = [
            'store_name', 'description', 'phone', 'whatsapp',
            'email', 'address', 'city', 'region',
            'momo_provider', 'momo_number'
        ]

    def validate_store_name(self, value):
        if Vendor.objects.filter(store_name__iexact=value).exists():
            raise serializers.ValidationError("A store with this name already exists.")
        return value


class VendorDashboardSerializer(serializers.ModelSerializer):
    """Full vendor dashboard serializer"""
    user_email = serializers.CharField(source='user.email', read_only=True)
    pending_payouts = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Vendor
        fields = [
            'id', 'store_name', 'slug', 'description', 'logo_url',
            'phone', 'whatsapp', 'email', 'address', 'city', 'region',
            'momo_provider', 'momo_number', 'commission_rate',
            'total_sales', 'total_products', 'average_rating',
            'status', 'is_active', 'is_verified',
            'created_at', 'approved_at', 'user_email', 'pending_payouts'
        ]
        read_only_fields = [
            'id', 'slug', 'commission_rate', 'total_sales',
            'total_products', 'average_rating', 'status',
            'is_active', 'is_verified', 'created_at', 'approved_at'
        ]

    def get_pending_payouts(self, obj):
        return obj.payouts.filter(status='pending').count()

    def get_logo_url(self, obj):
        if obj.logo and obj.logo.name:
            if str(obj.logo.name).startswith('http'):
                return obj.logo.name
            try:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.logo.url)
                return obj.logo.url
            except Exception:
                return None
        return None


class VendorPayoutSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.store_name', read_only=True)

    class Meta:
        model = VendorPayout
        fields = [
            'id', 'vendor', 'vendor_name', 'amount',
            'transaction_id', 'payment_method', 'status',
            'notes', 'created_at', 'completed_at'
        ]
        read_only_fields = ['id', 'transaction_id', 'status', 'created_at', 'completed_at']
