# Location: apps\payments\services.py
"""
NexCart Payment Service
Uses the official pymesomb SDK for mobile money payments.
Install: pip install pymesomb
"""
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional

from django.conf import settings
from apps.orders.models import Order

logger = logging.getLogger(__name__)


class MeSombPaymentService:
    """
    MeSomb Payment Gateway using the official pymesomb SDK.
    SDK handles all HMAC signature / Authorization header formatting.
    """

    def __init__(self):
        self.app_key    = settings.MESOMB_APP_KEY
        self.access_key = settings.MESOMB_ACCESS_KEY
        self.secret_key = settings.MESOMB_SECRET_KEY

    def _get_client(self):
        from pymesomb.operations import PaymentOperation
        return PaymentOperation(self.app_key, self.access_key, self.secret_key)

    def initiate_payment(
        self,
        order: Order,
        phone_number: str,
        service: str = 'MTN',
        currency: str = 'XAF'
    ) -> Dict:
        """Initiate a mobile money collect via MeSomb."""
        try:
            client = self._get_client()
            from pymesomb.utils import RandomGenerator
            response = client.make_collect(
                int(order.total),   # positional: some SDK versions don't accept 'amount' as kwarg
                service,
                phone_number,
                nonce=RandomGenerator.nonce(),
                country='CM',
                currency=currency,
                trx_id=str(order.order_number),
            )

            logger.info(
                f"MeSomb collect for order {order.order_number}: "
                f"operation={response.is_operation_success()}, "
                f"transaction={response.is_transaction_success()}"
            )

            if not response.is_operation_success():
                raise PaymentException(f"MeSomb operation failed: {response}")

            # Extract transaction ID from SDK response
            txn_id = None
            try:
                txn_id = str(response.transaction.pk)
            except Exception:
                txn_id = str(order.id)

            # Determine status from synchronous response
            is_done = response.is_transaction_success()
            initial_status = 'completed' if is_done else 'pending'

            # Persist payment record
            from .models import Payment
            Payment.objects.create(
                order=order,
                transaction_id=txn_id,
                payment_method=service,
                amount=order.total,
                currency=currency,
                status=initial_status,
                raw_response={'operation': True, 'transaction': is_done},
            )

            # If MeSomb confirmed success synchronously, update order immediately
            if is_done:
                order.payment_status = 'completed'
                order.status = 'processing'
                order.save(update_fields=['payment_status', 'status'])
                logger.info(f"Order {order.order_number} marked completed synchronously")

            return {
                'success':        True,
                'transaction_id': txn_id,
                'status':         'SUCCESS' if is_done else 'PENDING',
                'message':        'Payment initiated successfully',
            }

        except PaymentException:
            raise
        except Exception as e:
            logger.error(f"Payment initiation failed: {e}")
            raise PaymentException(str(e))

    def check_payment_status(self, transaction_id: str) -> Dict:
        """Check transaction status."""
        try:
            client = self._get_client()
            transactions = client.get_transactions([transaction_id])
            if transactions:
                t = transactions[0]
                return {
                    'transaction_id': transaction_id,
                    'status':         getattr(t, 'status', 'PENDING'),
                    'amount':         getattr(t, 'amount', None),
                    'currency':       getattr(t, 'currency', 'XAF'),
                    'data':           {},
                }
            return {'transaction_id': transaction_id, 'status': 'PENDING'}
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            raise PaymentException(str(e))

    def process_webhook(self, payload: Dict, signature: str) -> Dict:
        transaction_id = payload.get('transaction', {}).get('pk') or payload.get('transaction_id')
        status         = payload.get('status')

        if not all([transaction_id, status]):
            raise PaymentException("Invalid webhook data")

        from .models import Payment
        try:
            payment = Payment.objects.get(transaction_id=transaction_id)
            payment.status       = self._map_status(status)
            payment.raw_response = payload
            payment.save()

            order = Order.objects.get(id=payment.order_id)
            if payment.status == 'completed':
                order.payment_status = 'completed'
                order.status         = 'processing'
                from apps.orders.tasks import process_order
                process_order.delay(str(order.id))
            elif payment.status == 'failed':
                order.payment_status = 'failed'
            order.save()

            return {'success': True, 'order_id': str(order.id), 'payment_status': payment.status}
        except Exception as e:
            logger.error(f"Webhook processing error: {e}")
            raise PaymentException(str(e))

    def _map_status(self, mesomb_status: str) -> str:
        return {
            'SUCCESS': 'completed',
            'PENDING': 'pending',
            'FAILED':  'failed',
            'EXPIRED': 'failed',
        }.get(mesomb_status.upper(), 'pending')


class PaymentException(Exception):
    pass
