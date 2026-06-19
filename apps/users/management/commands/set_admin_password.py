"""
Management command to set admin password and promote user to admin role.
Usage:
    python manage.py set_admin_password
    python manage.py set_admin_password --email admin@nexcart.com --password MySecret123
"""
from django.core.management.base import BaseCommand
from apps.users.models import User


class Command(BaseCommand):
    help = 'Set the admin user password and ensure admin role'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default='admin@nexcart.com',
            help='Admin email address (default: admin@nexcart.com)',
        )
        parser.add_argument(
            '--password',
            type=str,
            default='admin123',
            help='New password for the admin user (default: admin123)',
        )

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']

        try:
            user = User.objects.get(email=email)
            user.set_password(password)
            user.role = 'admin'
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.is_verified = True
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f'[OK] Admin password updated for {email}'
            ))
            self.stdout.write(self.style.WARNING(
                f'   Login: {email} / {password}'
            ))
        except User.DoesNotExist:
            # Create the admin user from scratch
            user = User.objects.create_superuser(
                email=email,
                password=password,
                first_name='NexCart',
                last_name='Admin',
                role='admin',
            )
            user.is_verified = True
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f'[OK] Admin user created: {email}'
            ))
            self.stdout.write(self.style.WARNING(
                f'   Login: {email} / {password}'
            ))

        # Also update the role for all existing vendor users to 'seller'
        from apps.vendors.models import Vendor
        seller_count = 0
        for vendor in Vendor.objects.filter(status='approved'):
            if vendor.user.role not in ('admin', 'seller'):
                vendor.user.role = 'seller'
                vendor.user.save(update_fields=['role'])
                seller_count += 1

        if seller_count:
            self.stdout.write(self.style.SUCCESS(
                f'[OK] Promoted {seller_count} vendor(s) to seller role'
            ))
