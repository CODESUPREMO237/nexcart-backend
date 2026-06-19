"""
NexCart Coupon Models
Discount code system for promotions
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid


class Coupon(models.Model):
    """Discount coupon/promo code"""

    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True)

    # Discount
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES, default='percentage')
    discount_value = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Percentage (0-100) or fixed amount in FCFA"
    )

    # Constraints
    min_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
        help_text="Minimum order amount to apply coupon"
    )
    max_discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
        help_text="Maximum discount for percentage coupons"
    )
    max_uses = models.IntegerField(default=0, help_text="0 = unlimited")
    max_uses_per_user = models.IntegerField(default=1)
    used_count = models.IntegerField(default=0)

    # Validity
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    # Targeting
    vendor = models.ForeignKey(
        'vendors.Vendor', on_delete=models.CASCADE,
        related_name='coupons', null=True, blank=True,
        help_text="Vendor-specific coupon (null = platform-wide)"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'coupons'
        verbose_name = 'Coupon'
        verbose_name_plural = 'Coupons'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} ({self.get_discount_type_display()})"

    @property
    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from or now > self.valid_until:
            return False
        if self.max_uses > 0 and self.used_count >= self.max_uses:
            return False
        return True

    def calculate_discount(self, order_total):
        """Calculate discount amount for given order total"""
        if order_total < self.min_order_amount:
            return 0

        if self.discount_type == 'percentage':
            discount = order_total * (self.discount_value / 100)
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
        else:
            discount = min(self.discount_value, order_total)

        return discount


class CouponUsage(models.Model):
    """Track coupon usage per user"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='coupon_usages')
    order = models.ForeignKey(
        'orders.Order', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='coupon_usage'
    )
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'coupon_usages'
        verbose_name = 'Coupon Usage'
        verbose_name_plural = 'Coupon Usages'

    def __str__(self):
        return f"{self.user.email} used {self.coupon.code}"
