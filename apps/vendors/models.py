"""
NexCart Vendor Models
Multi-vendor marketplace with seller registration, approval, and payouts
"""
from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class Vendor(models.Model):
    """Vendor/Seller profile for multi-vendor marketplace"""

    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='vendor_profile'
    )

    # Store Information
    store_name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='vendors/logos/', blank=True, null=True, max_length=500)
    banner = models.ImageField(upload_to='vendors/banners/', blank=True, null=True, max_length=500)

    # Contact
    phone = models.CharField(max_length=20)
    whatsapp = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, default='Tiko')
    region = models.CharField(max_length=100, default='South West')

    # Payment - Mobile Money
    momo_provider = models.CharField(max_length=20, default='MTN',
        choices=[('MTN', 'MTN MoMo'), ('ORANGE', 'Orange Money')])
    momo_number = models.CharField(max_length=20)

    # Business
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.00,
        validators=[MinValueValidator(0), MaxValueValidator(50)],
        help_text="Platform commission percentage"
    )
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_products = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_active = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'vendors'
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'
        ordering = ['-created_at']

    def __str__(self):
        return self.store_name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.store_name)
        super().save(*args, **kwargs)

    @property
    def is_approved(self):
        return self.status == 'approved' and self.is_active


class VendorPayout(models.Model):
    """Track payouts to vendors via mobile money"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=255, blank=True)
    payment_method = models.CharField(max_length=20, default='MTN')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'vendor_payouts'
        verbose_name = 'Vendor Payout'
        verbose_name_plural = 'Vendor Payouts'
        ordering = ['-created_at']

    def __str__(self):
        return f"Payout {self.amount} to {self.vendor.store_name}"
