from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, UserProfile, UserActivity, StoreSettings, SellerKYC


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'get_full_name', 'role', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'role', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone')}),
        ('Role & Provider', {'fields': ('role', 'auth_provider', 'provider_id')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions'),
        }),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'role'),
        }),
    )
    
    def get_full_name(self, obj):
        return obj.full_name
    get_full_name.short_description = 'Name'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'avatar_thumbnail', 'bio_snippet', 'city']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'bio']
    readonly_fields = ['avatar_preview', 'created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Profile Information', {
            'fields': ('bio',)
        }),
        ('Avatar', {
            'fields': ('avatar', 'avatar_preview')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country')
        }),
        ('Preferences', {
            'fields': ('newsletter_subscribed', 'email_notifications')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def avatar_thumbnail(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; border-radius: 50%; object-fit: cover;" />',
                obj.avatar.url
            )
        return "No avatar"
    avatar_thumbnail.short_description = 'Avatar'
    
    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px; border-radius: 10px; object-fit: cover;" />',
                obj.avatar.url
            )
        return "No avatar uploaded"
    avatar_preview.short_description = 'Avatar Preview'
    
    def bio_snippet(self, obj):
        if obj.bio:
            return obj.bio[:50] + '...' if len(obj.bio) > 50 else obj.bio
        return '-'
    bio_snippet.short_description = 'Bio'


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user_display', 'activity_type', 'product', 'created_at']
    list_filter = ['activity_type', 'created_at']
    search_fields = ['user__email', 'product__name', 'session_id']
    readonly_fields = ['user', 'session_id', 'activity_type', 'product', 'metadata', 'ip_address', 'user_agent', 'created_at']
    
    fieldsets = (
        ('Activity Information', {
            'fields': ('user', 'session_id', 'activity_type', 'product')
        }),
        ('Tracking Data', {
            'fields': ('ip_address', 'user_agent', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
    
    def user_display(self, obj):
        return obj.user.email if obj.user else f"Guest ({obj.session_id[:8]})"
    user_display.short_description = 'User'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(StoreSettings)
class StoreSettingsAdmin(admin.ModelAdmin):
    list_display = ['store_name', 'support_email', 'maintenance_mode', 'require_email_verification']
    
    def has_add_permission(self, request):
        # Only allow one instance
        return not StoreSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion
        return False


@admin.register(SellerKYC)
class SellerKYCAdmin(admin.ModelAdmin):
    list_display = ['user_email', 'status', 'submitted_at', 'reviewed_at', 'reviewed_by']
    list_filter = ['status', 'submitted_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = [
        'user', 'id_front', 'id_back', 'selfie_with_id',
        'submitted_at', 'updated_at', 'reviewed_at', 'reviewed_by',
    ]
    ordering = ['-submitted_at']

    fieldsets = (
        ('Seller', {'fields': ('user',)}),
        ('Documents', {'fields': ('id_front', 'id_back', 'selfie_with_id')}),
        ('Decision', {'fields': ('status', 'rejection_reason', 'reviewed_by', 'reviewed_at')}),
        ('Timestamps', {'fields': ('submitted_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Seller Email'
    user_email.admin_order_field = 'user__email'

    def has_add_permission(self, request):
        # KYC records are created by sellers, not manually
        return False
