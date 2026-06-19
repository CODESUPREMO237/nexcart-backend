"""
NexCart Chat Views
REST-based buyer-seller messaging
"""
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone

from .models import Conversation, Message, AdminThread, AdminMessage
from .serializers import (
    ConversationSerializer, MessageSerializer,
    AdminThreadSerializer, AdminMessageSerializer,
)


class ConversationListView(generics.ListAPIView):
    """List user's conversations (admins see every conversation)"""
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return Conversation.objects.all().select_related('buyer', 'seller', 'product', 'vendor')
        return Conversation.objects.filter(
            Q(buyer=self.request.user) | Q(seller=self.request.user)
        ).select_related('buyer', 'seller', 'product', 'vendor')


class ConversationMessagesView(generics.ListAPIView):
    """List messages in a conversation"""
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        conversation_id = self.kwargs['conversation_id']
        conversation = Conversation.objects.get(
            id=conversation_id
        )
        is_admin = self.request.user.role == 'admin'
        # Verify user is part of this conversation, or is an admin
        if not is_admin and self.request.user not in [conversation.buyer, conversation.seller]:
            return Message.objects.none()

        # Only mark messages as read for actual participants - an admin
        # viewing a conversation shouldn't mark the buyer/seller's messages
        # as read on their behalf.
        if not is_admin:
            Message.objects.filter(
                conversation=conversation,
                is_read=False
            ).exclude(sender=self.request.user).update(
                is_read=True,
                read_at=timezone.now()
            )

        return conversation.messages.all()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request):
    """Send a message in a conversation"""
    try:
        conversation_id = request.data.get('conversation_id')
        content = request.data.get('content', '').strip()

        if not content:
            return Response({'error': 'Message content is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Get or create conversation
        if conversation_id:
            conversation = Conversation.objects.get(id=conversation_id)
        else:
            # Create new conversation
            seller_id = request.data.get('seller_id')
            product_id = request.data.get('product_id')
            vendor_id = request.data.get('vendor_id')

            if not seller_id:
                return Response({'error': 'seller_id is required for new conversations'},
                              status=status.HTTP_400_BAD_REQUEST)

            conversation, created = Conversation.objects.get_or_create(
                buyer=request.user,
                seller_id=seller_id,
                product_id=product_id,
                defaults={'vendor_id': vendor_id}
            )

        # Verify user is part of conversation, or is an admin replying on the platform's behalf
        if request.user.role != 'admin' and request.user not in [conversation.buyer, conversation.seller]:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content
        )

        # Update conversation timestamp
        conversation.last_message_at = timezone.now()
        conversation.save(update_fields=['last_message_at'])

        return Response(
            MessageSerializer(message).data,
            status=status.HTTP_201_CREATED
        )
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_count(request):
    """Get total unread message count"""
    count = Message.objects.filter(
        conversation__in=Conversation.objects.filter(
            Q(buyer=request.user) | Q(seller=request.user)
        ),
        is_read=False
    ).exclude(sender=request.user).count()

    return Response({'unread_count': count})


# ────────────────────────────────────────────────────────────────────────────
# Admin private threads
# An admin can message a single buyer or seller directly, separate from the
# buyer<->seller Conversation - the other party never sees these messages.
# ────────────────────────────────────────────────────────────────────────────

class AdminThreadListView(generics.ListAPIView):
    """
    List private admin threads.
    - Admins see every thread (their inbox of private conversations).
    - Regular users see only their own single thread with the admin team.
    """
    serializer_class = AdminThreadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return AdminThread.objects.all().select_related('user', 'related_conversation')
        return AdminThread.objects.filter(user=self.request.user).select_related('user', 'related_conversation')


class AdminThreadMessagesView(generics.ListAPIView):
    """List messages in a private admin thread"""
    serializer_class = AdminMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        thread_id = self.kwargs['thread_id']
        try:
            thread = AdminThread.objects.get(id=thread_id)
        except AdminThread.DoesNotExist:
            return AdminMessage.objects.none()

        is_admin = self.request.user.role == 'admin'
        # Only the admin team or the specific user this thread belongs to can view it
        if not is_admin and thread.user != self.request.user:
            return AdminMessage.objects.none()

        # Mark messages as read for whichever side is viewing
        AdminMessage.objects.filter(
            thread=thread, is_read=False, is_from_admin=not is_admin
        ).update(is_read=True, read_at=timezone.now())

        return thread.messages.all()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_admin_thread(request):
    """
    Admin: open (or fetch existing) private thread with a specific user.
    Body: { user_id, conversation_id (optional) }
    """
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    user_id = request.data.get('user_id')
    conversation_id = request.data.get('conversation_id')

    if not user_id:
        return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    thread, created = AdminThread.objects.get_or_create(
        user_id=user_id,
        related_conversation_id=conversation_id,
    )

    return Response(
        AdminThreadSerializer(thread, context={'request': request}).data,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_admin_message(request):
    """Send a message in a private admin thread (either side can reply)"""
    thread_id = request.data.get('thread_id')
    content = request.data.get('content', '').strip()

    if not content:
        return Response({'error': 'Message content is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not thread_id:
        return Response({'error': 'thread_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        thread = AdminThread.objects.get(id=thread_id)
    except AdminThread.DoesNotExist:
        return Response({'error': 'Thread not found'}, status=status.HTTP_404_NOT_FOUND)

    is_admin = request.user.role == 'admin'
    if not is_admin and thread.user != request.user:
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    message = AdminMessage.objects.create(
        thread=thread,
        sender=request.user,
        is_from_admin=is_admin,
        content=content,
    )

    thread.last_message_at = timezone.now()
    thread.save(update_fields=['last_message_at'])

    return Response(
        AdminMessageSerializer(message).data,
        status=status.HTTP_201_CREATED
    )
