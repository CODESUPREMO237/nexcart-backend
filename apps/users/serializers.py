# Location: apps\users\serializers.py
"""
NexCart User Serializers
"""
import re
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, UserProfile, UserActivity, StoreSettings


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'avatar', 'bio', 'address_line1', 'address_line2',
            'city', 'state', 'country', 'postal_code',
            'newsletter_subscribed', 'email_notifications'
        ]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'role', 'auth_provider', 'is_verified', 'is_active',
            'is_staff', 'date_joined', 'profile'
        ]
        read_only_fields = ['id', 'auth_provider', 'date_joined']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirm', 'first_name', 'last_name', 'phone']

    def validate_email(self, value):
        if not value or '@' not in value:
            raise serializers.ValidationError("Adresse email invalide.")
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("Un compte avec cet email existe déjà.")
        return value.lower()

    def validate_phone(self, value):
        if value:
            cleaned = re.sub(r'\s', '', value)
            if not re.match(r'^(\+?237)?[6][0-9]{8}$', cleaned):
                raise serializers.ValidationError(
                    "Numéro de téléphone camerounais invalide (ex: +237 6XX XXX XXX)."
                )
        return value

    def validate_first_name(self, value):
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError("Le prénom doit comporter au moins 2 caractères.")
        return value.strip() if value else value

    def validate_last_name(self, value):
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError("Le nom doit comporter au moins 2 caractères.")
        return value.strip() if value else value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone=validated_data.get('phone', '')
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
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
