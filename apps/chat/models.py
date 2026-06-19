"""
NexCart Chat Models
Buyer-seller messaging system
"""
from django.db import models
import uuid


class Conversation(models.Model):
    """Chat conversation between buyer and seller"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='buyer_conversations'
    )
    seller = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='seller_conversations'
    )
    product = models.ForeignKey(
        'products.Product', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='conversations'
    )
    vendor = models.ForeignKey(
        'vendors.Vendor', on_delete=models.CASCADE,
        related_name='conversations', null=True, blank=True
    )

    # Status
    is_active = models.BooleanField(default=True)
    last_message_at = models.DateTimeField(auto_now=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'conversations'
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
        ordering = ['-last_message_at']
        unique_together = ['buyer', 'seller', 'product']

    def __str__(self):
        return f"Chat: {self.buyer.email} ↔ {self.seller.email}"

    @property
    def unread_count_for_buyer(self):
        return self.messages.filter(sender=self.seller, is_read=False).count()

    @property
    def unread_count_for_seller(self):
        return self.messages.filter(sender=self.buyer, is_read=False).count()


class Message(models.Model):
    """Individual chat message"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages'
    )
    sender = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='sent_messages'
    )
    content = models.TextField()
    image = models.ImageField(upload_to='chat/images/', blank=True, null=True)

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messages'
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', 'is_read']),
        ]

    def __str__(self):
        return f"{self.sender.email}: {self.content[:50]}"


class AdminThread(models.Model):
    """
    Private conversation between an admin and a single user (buyer or seller).
    Separate from the buyer<->seller Conversation thread - this is for an
    admin to reach out to one party individually without the other seeing it.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='admin_threads'
    )
    # Optional link back to the buyer-seller conversation this originated from,
    # so the admin UI can show "Message Buyer"/"Message Seller" in context.
    related_conversation = models.ForeignKey(
        Conversation, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='admin_threads'
    )

    last_message_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin_threads'
        verbose_name = 'Admin Thread'
        verbose_name_plural = 'Admin Threads'
        ordering = ['-last_message_at']
        unique_together = ['user', 'related_conversation']

    def __str__(self):
        return f"Admin <-> {self.user.email}"

    @property
    def unread_count_for_user(self):
        return self.messages.filter(is_from_admin=True, is_read=False).count()

    @property
    def unread_count_for_admin(self):
        return self.messages.filter(is_from_admin=False, is_read=False).count()


class AdminMessage(models.Model):
    """Individual message in an admin <-> user private thread"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(
        AdminThread, on_delete=models.CASCADE, related_name='messages'
    )
    sender = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='sent_admin_messages'
    )
    is_from_admin = models.BooleanField(default=False)
    content = models.TextField()

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin_messages'
        verbose_name = 'Admin Message'
        verbose_name_plural = 'Admin Messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['thread', 'created_at']),
        ]

    def __str__(self):
        return f"[{'Admin' if self.is_from_admin else 'User'}] {self.content[:50]}"
