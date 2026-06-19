"""
NexCart Support Chat Views
Handles support ticket creation, message sending, and auto-replies
Works for both authenticated users and guests (via session key)
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import serializers

from .support_models import SupportTicket, SupportMessage

import random


# ── Serializers ──────────────────────────────────────────────

class SupportMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportMessage
        fields = ['id', 'sender_type', 'content', 'created_at']


class SupportUserSerializer(serializers.Serializer):
    """Minimal user info for admin ticket list"""
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField()

    def get_full_name(self, obj):
        return getattr(obj, 'full_name', '') or f"{getattr(obj, 'first_name', '')} {getattr(obj, 'last_name', '')}".strip() or obj.email


class SupportTicketSerializer(serializers.ModelSerializer):
    messages = SupportMessageSerializer(many=True, read_only=True)
    user = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = ['id', 'subject', 'status', 'created_at', 'updated_at', 'messages', 'user']

    def get_user(self, obj):
        if obj.user:
            name = (
                getattr(obj.user, 'full_name', None)
                or f"{getattr(obj.user, 'first_name', '')} {getattr(obj.user, 'last_name', '')}".strip()
                or obj.user.email
            )
            return {'full_name': name, 'email': obj.user.email}
        # Guest — use session key as identifier
        if obj.session_key:
            return {'full_name': f'Guest ({obj.session_key[:8]})', 'email': ''}
        return None


# ── Auto-reply logic ────────────────────────────────────────

REPLY_MAP = {
    'track': [
        'To track your order, go to "My Orders" from your profile menu. You\'ll see real-time status updates for each order.',
        'You can check your order status in the My Orders section. Each order shows its current delivery stage.',
        'Head to My Orders in your account — you\'ll find tracking info and estimated delivery dates there.',
    ],
    'payment': [
        'We accept MTN MoMo and Orange Money. If your payment failed, check your balance and try again in a few minutes.',
        'Payment issues? Make sure you have enough balance on your MoMo account and that you entered the correct number.',
        'For payment problems: 1) Check your MoMo balance 2) Verify your phone number 3) Try again after a few minutes.',
    ],
    'return': [
        'We have a 30-day return policy. Go to My Orders → select order → Request Return. Refunds go to your MoMo in 3-5 days.',
        'To return an item: visit My Orders, choose the order, and click Request Return. Pack it in the original packaging.',
        'Returns are easy! Just go to My Orders, select the item, and request a return. We process refunds within 3-5 business days.',
    ],
    'delivery': [
        'Delivery times: Tiko 1-2 days, Buea/Limbe 1-3 days, Douala 2-5 days, Yaoundé 3-7 days. Free delivery on orders above 25,000 FCFA!',
        'We deliver across Cameroon! Tiko area is fastest (1-2 days). Douala takes 2-5 days, Yaoundé 3-7 days.',
        'Shipping depends on your zone. Local Tiko delivery is 1-2 days. Check the delivery estimator on any product page for exact times.',
    ],
    'seller': [
        'To become a seller: click "Seller Dashboard" in the menu → Register your store → Add MoMo details → Wait for approval (24-48h).',
        'Want to sell on NexCart? Go to Seller Dashboard from the menu, fill in your store info, and submit. Approval takes 24-48 hours!',
        'Becoming a seller is easy! Navigate to Seller Dashboard, register your store with your details and MoMo number, then wait for approval.',
    ],
    'price': [
        'You can track price changes on any product page. Click "Set Price Alert" and we\'ll notify you when the price drops!',
        'We have a price tracking feature! On any product, you can see price history and set alerts for price drops.',
    ],
    'coupon': [
        'Enter your coupon code at checkout in the "Apply Coupon" field. The discount will be applied automatically to your total.',
        'Got a coupon? Add it during checkout — look for the coupon input field above the payment section.',
    ],
    'hello': [
        'Hello! 😊 Welcome to NexCart Support! How can I help you today?',
        'Hey there! 👋 Great to have you. What can I help you with?',
        'Hi! Welcome to NexCart. I\'m here to help — what do you need?',
    ],
}


def get_auto_reply(message):
    """Return a bot reply for recognised FAQ topics only. Returns None otherwise."""
    lower = message.lower()
    for keyword_group, keywords in [
        ('track',    ['track', 'order status', 'where is my', 'my order']),
        ('payment',  ['payment', 'pay', 'momo', 'money', 'orange money', 'mtn']),
        ('return',   ['return', 'refund', 'send back', 'exchange']),
        ('delivery', ['delivery', 'shipping', 'ship', 'how long', 'when will']),
        ('seller',   ['seller', 'sell', 'vendor', 'store', 'open shop']),
        ('price',    ['price', 'discount', 'cheaper', 'cost', 'alert']),
        ('coupon',   ['coupon', 'promo', 'code', 'voucher']),
        ('hello',    ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'bonjour', 'salut']),
    ]:
        if any(kw in lower for kw in keywords):
            return random.choice(REPLY_MAP[keyword_group])
    return None


# ── Admin views ───────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_support_tickets(request):
    """Admin: list all support tickets with their messages"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    tickets = (
        SupportTicket.objects
        .prefetch_related('messages')
        .select_related('user')
        .order_by('-updated_at')
    )
    return Response(SupportTicketSerializer(tickets, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_support_reply(request):
    """Admin: reply to a support ticket as an agent"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    ticket_id = request.data.get('ticket_id')
    content = request.data.get('content', '').strip()
    if not ticket_id or not content:
        return Response({'error': 'ticket_id and content are required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)
    ticket.status = 'in_progress'
    ticket.save(update_fields=['status', 'updated_at'])
    msg = SupportMessage.objects.create(ticket=ticket, sender_type='agent', content=content)
    return Response(SupportMessageSerializer(msg).data, status=status.HTTP_201_CREATED)


# ── User/guest views ──────────────────────────────────────────

def _get_or_create_ticket(request):
    """Get the user's existing open ticket or create a new one."""
    if request.user and request.user.is_authenticated:
        ticket = SupportTicket.objects.filter(
            user=request.user, status__in=['open', 'in_progress']
        ).first()
        if not ticket:
            ticket = SupportTicket.objects.create(user=request.user)
        return ticket
    else:
        session_key = request.data.get('session_key') or request.query_params.get('session_key')
        if not session_key:
            return None
        ticket = SupportTicket.objects.filter(
            session_key=session_key, status__in=['open', 'in_progress']
        ).first()
        if not ticket:
            ticket = SupportTicket.objects.create(session_key=session_key)
        return ticket


@api_view(['GET'])
@permission_classes([AllowAny])
def support_messages(request):
    """Get the current user/guest's support chat history."""
    if request.user and request.user.is_authenticated:
        ticket = SupportTicket.objects.filter(
            user=request.user, status__in=['open', 'in_progress']
        ).first()
    else:
        session_key = request.query_params.get('session_key')
        if not session_key:
            return Response({'messages': []})
        ticket = SupportTicket.objects.filter(
            session_key=session_key, status__in=['open', 'in_progress']
        ).first()

    if not ticket:
        return Response({'messages': []})

    msgs = ticket.messages.all()
    return Response({
        'ticket_id': str(ticket.id),
        'messages': SupportMessageSerializer(msgs, many=True).data,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def support_send(request):
    """
    Send a support message.
    Bot only auto-replies to recognised FAQ keywords.
    For everything else the message is saved and the admin sees it — no repeated bot noise.
    """
    content = request.data.get('content', '').strip()
    if not content:
        return Response({'error': 'Message content is required'}, status=status.HTTP_400_BAD_REQUEST)

    ticket = _get_or_create_ticket(request)
    if not ticket:
        return Response({'error': 'Session key is required for guest users'}, status=status.HTTP_400_BAD_REQUEST)

    # Save user message
    user_msg = SupportMessage.objects.create(
        ticket=ticket,
        sender_type='user',
        content=content,
    )

    # Update ticket timestamp so admin sees it at the top
    ticket.save(update_fields=['updated_at'])

    # Bot only replies to recognised FAQ topics — nothing else
    reply_content = get_auto_reply(content)

    result = {
        'ticket_id': str(ticket.id),
        'user_message': SupportMessageSerializer(user_msg).data,
        'bot_reply': None,
    }

    if reply_content:
        bot_msg = SupportMessage.objects.create(
            ticket=ticket,
            sender_type='bot',
            content=reply_content,
        )
        result['bot_reply'] = SupportMessageSerializer(bot_msg).data

    return Response(result, status=status.HTTP_201_CREATED)
