"""
NexCart Support Chat Models
Support ticket system with message persistence
"""
from django.db import models
import uuid


class SupportTicket(models.Model):
    """Support chat session - works for both authenticated and guest users"""

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='support_tickets'
    )
    # For guest users, track by session
    session_key = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    subject = models.CharField(max_length=255, default='Live Chat Support')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'support_tickets'
        verbose_name = 'Support Ticket'
        verbose_name_plural = 'Support Tickets'
        ordering = ['-updated_at']

    def __str__(self):
        if self.user:
            return f"Support #{str(self.id)[:8]} - {self.user.email}"
        return f"Support #{str(self.id)[:8]} - Guest ({self.session_key})"


class SupportMessage(models.Model):
    """Individual message in a support chat"""

    SENDER_CHOICES = [
        ('user', 'User'),
        ('bot', 'Bot'),
        ('agent', 'Agent'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        SupportTicket, on_delete=models.CASCADE, related_name='messages'
    )
    sender_type = models.CharField(max_length=10, choices=SENDER_CHOICES)
    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'support_messages'
        verbose_name = 'Support Message'
        verbose_name_plural = 'Support Messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['ticket', 'created_at']),
        ]

    def __str__(self):
        return f"[{self.sender_type}] {self.content[:50]}"
