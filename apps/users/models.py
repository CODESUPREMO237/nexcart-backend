# Location: apps\users\models.py
"""
NexCart User Models
Custom user model with role-based access control
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
import uuid


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model with extended fields"""
    
    ROLE_CHOICES = [
        ('user', 'User'),
        ('seller', 'Seller'),
        ('admin', 'Admin'),
    ]
    
    AUTH_PROVIDER_CHOICES = [
        ('email', 'Email'),
        ('google', 'Google'),
        ('github', 'GitHub'),
        ('microsoft', 'Microsoft'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    auth_provider = models.CharField(
        max_length=20, 
        choices=AUTH_PROVIDER_CHOICES, 
        default='email'
    )
    provider_id = models.CharField(max_length=255, blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    
    # Override groups and user_permissions to fix admin.LogEntry conflict
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']
    
    def __str__(self):
        return self.email
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email
    
    def is_admin(self):
        return self.role == 'admin'

    def is_seller(self):
        return self.role == 'seller'


class UserProfile(models.Model):
    """Extended user profile with preferences and address"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    
    # Address information
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    
    # Preferences
    newsletter_subscribed = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"Profile of {self.user.email}"


class UserActivity(models.Model):
    """Track user interactions for AI recommendations"""
    
    ACTIVITY_TYPES = [
        ('view', 'Product View'),
        ('click', 'Product Click'),
        ('add_cart', 'Add to Cart'),
        ('purchase', 'Purchase'),
        ('wishlist', 'Add to Wishlist'),
        ('review', 'Product Review'),
        ('search', 'Search Query'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='activities',
        null=True,
        blank=True
    )
    session_id = models.CharField(max_length=255, db_index=True)
    
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='activities',
        null=True,
        blank=True
    )
    
    # Additional context
    metadata = models.JSONField(default=dict, blank=True)
    
    # Tracking
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'user_activities'
        verbose_name = 'User Activity'
        verbose_name_plural = 'User Activities'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'activity_type', 'created_at']),
            models.Index(fields=['session_id', 'created_at']),
        ]
    
    def __str__(self):
        user_str = self.user.email if self.user else self.session_id
        return f"{user_str} - {self.activity_type}"


class StoreSettings(models.Model):
    """Global store configuration (Singleton Model)"""
    store_name = models.CharField(max_length=255, default="NexCart")
    support_email = models.EmailField(default="support@nexcart.com")
    maintenance_mode = models.BooleanField(default=False)
    require_email_verification = models.BooleanField(default=True)

    class Meta:
        db_table = 'store_settings'
        verbose_name = 'Store Setting'
        verbose_name_plural = 'Store Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super(StoreSettings, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Global Store Settings"


class SellerKYC(models.Model):
    """KYC identity verification for sellers"""

    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='kyc'
    )

    # Identity documents
    id_front = models.ImageField(upload_to='kyc/id_front/', max_length=500)
    id_back = models.ImageField(upload_to='kyc/id_back/', max_length=500)
    selfie_with_id = models.ImageField(upload_to='kyc/selfies/', max_length=500)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    rejection_reason = models.TextField(blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='kyc_reviews'
    )

    class Meta:
        db_table = 'seller_kyc'
        verbose_name = 'Seller KYC'
        verbose_name_plural = 'Seller KYCs'
        ordering = ['-submitted_at']

    def __str__(self):
        return f"KYC – {self.user.email} [{self.status}]"
