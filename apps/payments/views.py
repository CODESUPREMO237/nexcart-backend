# Location: apps\payments\views.py
"""
NexCart Payment Views
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404

from apps.orders.models import Order
from .services import MeSombPaymentService, PaymentException
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    """Initiate payment for an order"""
    try:
        order_id = request.data.get('order_id')
        phone_number = request.data.get('phone_number')
        service = request.data.get('service', 'MTN')
        
        # Validate inputs
        if not all([order_id, phone_number]):
            return Response({
                'error': 'order_id and phone_number are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get order
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        # Check if order is already paid
        if order.payment_status == 'completed':
            return Response({
                'error': 'Order is already paid'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initiate payment
        payment_service = MeSombPaymentService()
        result = payment_service.initiate_payment(
            order=order,
            phone_number=phone_number,
            service=service
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except PaymentException as e:
        logger.error(f"Payment initiation failed: {str(e)}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return Response({
            'error': 'Payment initiation failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_payment_status(request, transaction_id):
    """Check payment status and update order/payment records"""
    try:
        from .models import Payment
        payment_service = MeSombPaymentService()
        result = payment_service.check_payment_status(transaction_id)

        mesomb_status = (result.get('status') or '').upper()

        # Map and persist status change
        if mesomb_status == 'SUCCESS':
            internal_status = 'completed'
        elif mesomb_status in ('FAILED', 'EXPIRED'):
            internal_status = 'failed'
        else:
            internal_status = 'pending'

        # Update Payment + Order records
        try:
            payment = Payment.objects.get(transaction_id=transaction_id)
            if payment.status != internal_status:
                payment.status = internal_status
                payment.save(update_fields=['status'])

                order = payment.order
                if internal_status == 'completed':
                    order.payment_status = 'completed'
                    order.status = 'processing'
                elif internal_status == 'failed':
                    order.payment_status = 'failed'
                order.save(update_fields=['payment_status', 'status'])
                logger.info(f"Order {order.order_number} updated: payment={internal_status}")
        except Payment.DoesNotExist:
            pass

        result['status'] = mesomb_status  # return raw MeSomb status for frontend polling
        return Response(result, status=status.HTTP_200_OK)

    except PaymentException as e:
        logger.error(f"Status check failed: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return Response({'error': 'Status check failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)