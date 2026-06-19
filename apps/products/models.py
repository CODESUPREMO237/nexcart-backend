# Location: apps\products\models.py
"""
NexCart Product Models
Product catalog with categories, reviews, and inventory
"""
from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class Category(models.Model):
    """Product categories with hierarchical support"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='children',
        null=True,
        blank=True
    )
    
    image = models.ImageField(upload_to='categories/', blank=True, null=True, max_length=500)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    """Main product model"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Information
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField()
    short_description = models.CharField(max_length=500, blank=True)
    
    # Categorization
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name='products',
        null=True
    )
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")

    # Vendor (multi-vendor marketplace)
    vendor = models.ForeignKey(
        'vendors.Vendor',
        on_delete=models.SET_NULL,
        related_name='products',
        null=True,
        blank=True
    )
    
    # Pricing
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    compare_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    
    # Inventory
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    track_inventory = models.BooleanField(default=True)
    allow_backorder = models.BooleanField(default=False)
    
    # Media
    featured_image = models.ImageField(upload_to='products/', blank=True, null=True, max_length=500)
    
    # SEO
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(max_length=500, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False)

    # Admin approval workflow
    APPROVAL_STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    approval_status = models.CharField(
        max_length=10,
        choices=APPROVAL_STATUS_CHOICES,
        default='approved',
        db_index=True,
        help_text='Admin must approve new/updated products before they go live'
    )
    pending_deletion = models.BooleanField(
        default=False,
        help_text='Seller requested deletion, awaiting admin confirmation'
    )
    pending_update_data = models.JSONField(
        null=True,
        blank=True,
        help_text='Stores proposed field changes until admin approves the update'
    )
    
    # Statistics (denormalized for performance)
    view_count = models.IntegerField(default=0)
    purchase_count = models.IntegerField(default=0)
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    review_count = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', '-created_at']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['-purchase_count']),
            models.Index(fields=['-average_rating']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    @property
    def is_in_stock(self):
        if not self.track_inventory:
            return True
        return self.stock_quantity > 0 or self.allow_backorder
    
    @property
    def discount_percentage(self):
        if self.compare_price and self.compare_price > self.price:
            return int(((self.compare_price - self.price) / self.compare_price) * 100)
        return 0


class ProductImage(models.Model):
    """Additional product images"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='products/', max_length=500)
    alt_text = models.CharField(max_length=200, blank=True)
    position = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_images'
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'
        ordering = ['position']
    
    def __str__(self):
        return f"Image for {self.product.name}"


class ProductReview(models.Model):
    """Product reviews and ratings"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=200, blank=True)
    comment = models.TextField()
    
    # Verification
    is_verified_purchase = models.BooleanField(default=False)
    
    # Moderation
    is_approved = models.BooleanField(default=True)
    
    # Helpfulness
    helpful_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_reviews'
        verbose_name = 'Product Review'
        verbose_name_plural = 'Product Reviews'
        ordering = ['-created_at']
        unique_together = ['product', 'user']
    
    def __str__(self):
        return f"Review by {self.user.email} for {self.product.name}"


class Wishlist(models.Model):
    """User wishlist"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='wishlist_items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='wishlisted_by'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'wishlists'
        verbose_name = 'Wishlist'
        verbose_name_plural = 'Wishlists'
        unique_together = ['user', 'product']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.product.name}"