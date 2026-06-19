"""
NexCart Chat Admin
"""
from django.contrib import admin
from .models import Conversation, Message, AdminThread, AdminMessage
from .support_models import SupportTicket, SupportMessage


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['buyer', 'seller', 'product', 'is_active', 'last_message_at', 'created_at']
    list_filter = ['is_active']
    search_fields = ['buyer__email', 'seller__email']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'conversation', 'content_preview', 'is_read', 'created_at']
    list_filter = ['is_read']

    def content_preview(self, obj):
        return obj.content[:80]
    content_preview.short_description = 'Content'


@admin.register(AdminThread)
class AdminThreadAdmin(admin.ModelAdmin):
    list_display = ['user', 'related_conversation', 'last_message_at', 'created_at']
    search_fields = ['user__email']


@admin.register(AdminMessage)
class AdminMessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'thread', 'is_from_admin', 'content_preview', 'is_read', 'created_at']
    list_filter = ['is_from_admin', 'is_read']

    def content_preview(self, obj):
        return obj.content[:80]
    content_preview.short_description = 'Content'


class SupportMessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 0
    readonly_fields = ['sender_type', 'content', 'created_at']


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['id_short', 'user', 'session_key_short', 'status', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__email', 'session_key']
    list_editable = ['status']
    inlines = [SupportMessageInline]

    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = 'Ticket ID'

    def session_key_short(self, obj):
        return (obj.session_key or '')[:20]
    session_key_short.short_description = 'Session'


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ['ticket_short', 'sender_type', 'content_preview', 'created_at']
    list_filter = ['sender_type', 'created_at']
    search_fields = ['content']

    def ticket_short(self, obj):
        return str(obj.ticket_id)[:8]
    ticket_short.short_description = 'Ticket'

    def content_preview(self, obj):
        return obj.content[:80]
    content_preview.short_description = 'Content'

