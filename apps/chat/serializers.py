"""
NexCart Chat Serializers
"""
from rest_framework import serializers
from .models import Conversation, Message, AdminThread, AdminMessage


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    sender_email = serializers.CharField(source='sender.email', read_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'sender_name', 'sender_email',
            'content', 'is_read', 'read_at', 'created_at'
        ]
        read_only_fields = ['id', 'sender', 'is_read', 'read_at', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    buyer_name = serializers.CharField(source='buyer.full_name', read_only=True)
    buyer_email = serializers.CharField(source='buyer.email', read_only=True)
    seller_name = serializers.CharField(source='seller.full_name', read_only=True)
    seller_email = serializers.CharField(source='seller.email', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True, default=None)
    vendor_name = serializers.CharField(source='vendor.store_name', read_only=True, default=None)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'buyer', 'buyer_name', 'buyer_email', 'seller', 'seller_name', 'seller_email',
            'product', 'product_name', 'vendor', 'vendor_name',
            'is_active', 'last_message_at', 'last_message',
            'unread_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'last_message_at']

    def get_last_message(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        if msg:
            return {
                'content': msg.content[:100],
                'sender_name': msg.sender.full_name,
                'created_at': msg.created_at,
                'is_read': msg.is_read
            }
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.messages.filter(is_read=False).exclude(sender=request.user).count()
        return 0


class AdminMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    sender_email = serializers.CharField(source='sender.email', read_only=True)

    class Meta:
        model = AdminMessage
        fields = [
            'id', 'thread', 'sender', 'sender_name', 'sender_email',
            'is_from_admin', 'content', 'is_read', 'read_at', 'created_at'
        ]
        read_only_fields = ['id', 'sender', 'is_from_admin', 'is_read', 'read_at', 'created_at']


class AdminThreadSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = AdminThread
        fields = [
            'id', 'user', 'user_name', 'user_email', 'user_role',
            'related_conversation', 'last_message_at', 'last_message',
            'unread_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'last_message_at']

    def get_last_message(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        if msg:
            return {
                'content': msg.content[:100],
                'is_from_admin': msg.is_from_admin,
                'created_at': msg.created_at,
            }
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.role == 'admin':
            return obj.unread_count_for_admin
        return obj.unread_count_for_user
