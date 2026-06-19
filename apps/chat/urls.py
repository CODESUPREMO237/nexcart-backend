"""
NexCart Chat URLs
"""
from django.urls import path
from .views import (
    ConversationListView, ConversationMessagesView,
    send_message, unread_count,
    AdminThreadListView, AdminThreadMessagesView,
    start_admin_thread, send_admin_message,
)
from .support_views import support_messages, support_send, admin_support_tickets, admin_support_reply

app_name = 'chat'

urlpatterns = [
    # Buyer-seller chat
    path('chat/conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('chat/conversations/<uuid:conversation_id>/messages/',
         ConversationMessagesView.as_view(), name='conversation-messages'),
    path('chat/send/', send_message, name='send-message'),
    path('chat/unread/', unread_count, name='unread-count'),

    # Admin private threads (admin <-> single buyer or seller)
    path('chat/admin-threads/', AdminThreadListView.as_view(), name='admin-thread-list'),
    path('chat/admin-threads/<uuid:thread_id>/messages/',
         AdminThreadMessagesView.as_view(), name='admin-thread-messages'),
    path('chat/admin-threads/start/', start_admin_thread, name='admin-thread-start'),
    path('chat/admin-threads/send/', send_admin_message, name='admin-thread-send'),

    # Support chat (persisted)
    path('support/messages/', support_messages, name='support-messages'),
    path('support/send/', support_send, name='support-send'),

    # Admin: read & reply to support tickets
    path('support/admin/tickets/', admin_support_tickets, name='admin-support-tickets'),
    path('support/admin/reply/', admin_support_reply, name='admin-support-reply'),
]

