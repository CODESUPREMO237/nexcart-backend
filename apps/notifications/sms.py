"""
NexCart SMS Notification Service
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class SMSService:
    """SMS notification service - configurable provider"""

    @staticmethod
    def send_sms(phone_number, message):
        """Send SMS notification"""
        try:
            provider = getattr(settings, 'SMS_PROVIDER', 'log')

            if provider == 'twilio':
                return SMSService._send_twilio(phone_number, message)
            elif provider == 'nexmo':
                return SMSService._send_nexmo(phone_number, message)
            else:
                # Log-only mode for development
                logger.info(f"[SMS to {phone_number}]: {message}")
                return {'success': True, 'provider': 'log', 'message': 'SMS logged (dev mode)'}

        except Exception as e:
            logger.error(f"SMS send failed to {phone_number}: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def _send_twilio(phone_number, message):
        """Send via Twilio"""
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        return {'success': True, 'provider': 'twilio', 'sid': msg.sid}

    @staticmethod
    def _send_nexmo(phone_number, message):
        """Send via Vonage/Nexmo"""
        response = requests.post('https://rest.nexmo.com/sms/json', data={
            'api_key': settings.NEXMO_API_KEY,
            'api_secret': settings.NEXMO_API_SECRET,
            'from': settings.NEXMO_FROM_NUMBER,
            'to': phone_number,
            'text': message
        })
        return {'success': True, 'provider': 'nexmo', 'data': response.json()}

    # Convenience methods
    @staticmethod
    def send_order_confirmation(phone, order_number, total):
        message = (
            f"🛒 NexCart: Your order {order_number} has been placed! "
            f"Total: {total} FCFA. "
            f"We'll notify you when it ships. Thank you!"
        )
        return SMSService.send_sms(phone, message)

    @staticmethod
    def send_order_shipped(phone, order_number, tracking=''):
        message = (
            f"📦 NexCart: Your order {order_number} has been shipped! "
            f"{f'Tracking: {tracking}' if tracking else ''} "
            f"Estimated delivery: 1-3 days."
        )
        return SMSService.send_sms(phone, message)

    @staticmethod
    def send_order_delivered(phone, order_number):
        message = (
            f"✅ NexCart: Your order {order_number} has been delivered! "
            f"Thank you for shopping with us. Rate your experience!"
        )
        return SMSService.send_sms(phone, message)

    @staticmethod
    def send_price_alert(phone, product_name, new_price):
        message = (
            f"💰 NexCart Price Drop! {product_name} is now {new_price} FCFA. "
            f"Shop now before it's gone!"
        )
        return SMSService.send_sms(phone, message)
