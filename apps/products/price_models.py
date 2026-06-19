"""
NexCart Price Tracking Models
Price history and price drop alerts
"""
from django.db import models
from django.core.validators import MinValueValidator
import uuid


class PriceHistory(models.Model):
    """Track product price changes over time"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE, related_name='price_history'
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    recorded_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'price_history'
        verbose_name = 'Price History'
        verbose_name_plural = 'Price Histories'
        ordering = ['-recorded_at']

    def __str__(self):
        return f"{self.product.name}: {self.price} at {self.recorded_at}"


class PriceAlert(models.Model):
    """User price drop alert"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='price_alerts'
    )
    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE, related_name='price_alerts'
    )
    target_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Alert when price drops to this level"
    )
    is_triggered = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    triggered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'price_alerts'
        verbose_name = 'Price Alert'
        verbose_name_plural = 'Price Alerts'
        unique_together = ['user', 'product']

    def __str__(self):
        return f"{self.user.email} alert for {self.product.name} at {self.target_price}"
