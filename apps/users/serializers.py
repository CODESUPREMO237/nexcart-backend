# Location: apps\users\serializers.py
"""
NexCart User Serializers
"""
import re
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, UserProfile, UserActivity, StoreSettings, SellerKYC


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'avatar', 'bio', 'address_line1', 'address_line2',
            'city', 'state', 'country', 'postal_code',
            'newsletter_subscribed', 'email_notifications'
        ]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'role', 'auth_provider', 'is_verified', 'is_active',
            'is_staff', 'date_joined', 'profile'
        ]
        read_only_fields = ['id', 'email', 'auth_provider', 'date_joined', 'role', 'is_verified', 'is_active', 'is_staff']

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        
        # Fallback if DRF strips the nested profile dictionary during validation
        if profile_data is None and hasattr(self, 'initial_data') and 'profile' in self.initial_data:
            profile_data = self.initial_data['profile']
            
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if profile_data is not None:
            from .models import UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                if hasattr(profile, attr):
                    setattr(profile, attr, value)
            profile.save()

        return instance


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    # Accepted at registration time only — determines initial role
    intended_role = serializers.ChoiceField(
        choices=['buyer', 'seller'],
        default='buyer',
        required=False,
        write_only=True,
    )

    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirm', 'first_name', 'last_name', 'phone', 'intended_role']

    def validate_email(self, value):
        if not value or '@' not in value:
            raise serializers.ValidationError("Invalid email address.")
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.lower()

    def validate_phone(self, value):
        if value:
            cleaned = re.sub(r'\s', '', value)
            if not re.match(r'^(\+?237)?[6][0-9]{8}$', cleaned):
                raise serializers.ValidationError(
                    "Invalid Cameroonian phone number (e.g. +237 6XX XXX XXX)."
                )
        return value

    def validate_first_name(self, value):
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError("First name must be at least 2 characters.")
        return value.strip() if value else value

    def validate_last_name(self, value):
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError("Last name must be at least 2 characters.")
        return value.strip() if value else value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        intended_role = validated_data.pop('intended_role', 'buyer')

        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone=validated_data.get('phone', ''),
            # Sellers get the 'seller' role immediately; KYC gate controls access
            role='seller' if intended_role == 'seller' else 'user',
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate_email(self, value):
        return value.lower() if value else value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "Passwords do not match."})
        return attrs


class UserActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActivity
        fields = ['id', 'activity_type', 'product', 'metadata', 'created_at']
        read_only_fields = ['id', 'created_at']


class StoreSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreSettings
        fields = '__all__'


# ── KYC Serializers ──────────────────────────────────────────────────────────

class SellerKYCSerializer(serializers.ModelSerializer):
    """Seller-facing KYC serializer (hides admin-only fields)"""
    id_front_url = serializers.SerializerMethodField()
    id_back_url = serializers.SerializerMethodField()
    selfie_url = serializers.SerializerMethodField()

    class Meta:
        model = SellerKYC
        fields = [
            'id', 'status', 'rejection_reason',
            'id_front_url', 'id_back_url', 'selfie_url',
            'submitted_at', 'reviewed_at',
        ]
        read_only_fields = fields

    def _abs_url(self, field):
        if field and field.name:
            if str(field.name).startswith('http'):
                return field.name
            try:
                request = self.context.get('request')
                return request.build_absolute_uri(field.url) if request else field.url
            except Exception:
                return None
        return None

    def get_id_front_url(self, obj):
        return self._abs_url(obj.id_front)

    def get_id_back_url(self, obj):
        return self._abs_url(obj.id_back)

    def get_selfie_url(self, obj):
        return self._abs_url(obj.selfie_with_id)


class SellerKYCAdminSerializer(SellerKYCSerializer):
    """Admin-facing KYC serializer with full user details"""
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    reviewed_by_email = serializers.SerializerMethodField()

    class Meta(SellerKYCSerializer.Meta):
        fields = [
            'id', 'user_id', 'user_email', 'user_name',
            'status', 'rejection_reason',
            'id_front_url', 'id_back_url', 'selfie_url',
            'submitted_at', 'reviewed_at', 'reviewed_by_email',
        ]
        read_only_fields = fields

    def get_reviewed_by_email(self, obj):
        return obj.reviewed_by.email if obj.reviewed_by else None
