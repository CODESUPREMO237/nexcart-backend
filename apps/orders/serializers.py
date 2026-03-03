# Location: apps\orders\serializers.py
"""
NexCart Order Serializers
"""
from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem, OrderStatusHistory
from apps.products.serializers import ProductListSerializer


class CartItemSerializer(serializers.ModelSerializer):
    """Cart item serializer"""
    product = ProductListSerializer(read_only=True)
    product_id = serializers.UUIDField(write_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'price', 'total_price', 'created_at']
        read_only_fields = ['id', 'price', 'created_at']


class CartSerializer(serializers.ModelSerializer):
    """Cart serializer"""
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_items', 'subtotal', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class OrderItemSerializer(serializers.ModelSerializer):
    """Order item serializer"""
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'product_image', 'quantity', 'price', 'total'
        ]
        read_only_fields = ['id']


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    """Order status history serializer"""
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    
    class Meta:
        model = OrderStatusHistory
        fields = ['id', 'status', 'notes', 'created_by', 'created_by_name', 'created_at']
        read_only_fields = ['id', 'created_at']


class OrderListSerializer(serializers.ModelSerializer):
    """Order list serializer (minimal fields)"""
    total_amount = serializers.DecimalField(source='total', max_digits=10, decimal_places=2, read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_address = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'payment_status',
            'total', 'total_amount', 'items', 'shipping_address', 'tracking_number', 'created_at'
        ]

    def get_shipping_address(self, obj):
        return {
            'city': obj.shipping_city,
            'state': obj.shipping_state,
            'country': obj.shipping_country,
        }


class OrderDetailSerializer(serializers.ModelSerializer):
    """Order detail serializer (full fields)"""
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'email', 'phone',
            'shipping_first_name', 'shipping_last_name',
            'shipping_address_line1', 'shipping_address_line2',
            'shipping_city', 'shipping_state', 'shipping_country',
            'shipping_postal_code', 'billing_same_as_shipping',
            'billing_first_name', 'billing_last_name',
            'billing_address_line1', 'billing_address_line2',
            'billing_city', 'billing_state', 'billing_country',
            'billing_postal_code', 'status', 'payment_status',
            'subtotal', 'shipping_cost', 'tax', 'discount', 'total',
            'notes', 'tracking_number', 'carrier', 'items',
            'status_history', 'created_at', 'updated_at',
            'shipped_at', 'delivered_at'
        ]
        read_only_fields = ['id', 'order_number', 'created_at', 'updated_at']


class OrderCreateSerializer(serializers.ModelSerializer):
    """Order creation serializer"""
    
    class Meta:
        model = Order
        fields = [
            'email', 'phone', 'shipping_first_name', 'shipping_last_name',
            'shipping_address_line1', 'shipping_address_line2',
            'shipping_city', 'shipping_state', 'shipping_country',
            'shipping_postal_code', 'billing_same_as_shipping',
            'billing_first_name', 'billing_last_name',
            'billing_address_line1', 'billing_address_line2',
            'billing_city', 'billing_state', 'billing_country',
            'billing_postal_code', 'notes'
        ]
    
    def validate(self, attrs):
        # If billing is not same as shipping, validate billing fields
        if not attrs.get('billing_same_as_shipping', True):
            required_billing_fields = [
                'billing_first_name', 'billing_last_name',
                'billing_address_line1', 'billing_city',
                'billing_state', 'billing_country', 'billing_postal_code'
            ]
            for field in required_billing_fields:
                if not attrs.get(field):
                    raise serializers.ValidationError({field: "This field is required when billing address is different"})
        
        return attrs