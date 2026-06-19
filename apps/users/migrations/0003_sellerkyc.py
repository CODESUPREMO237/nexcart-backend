# Generated migration for SellerKYC model
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_user_role'),
    ]

    operations = [
        migrations.CreateModel(
            name='SellerKYC',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('id_front', models.ImageField(max_length=500, upload_to='kyc/id_front/')),
                ('id_back', models.ImageField(max_length=500, upload_to='kyc/id_back/')),
                ('selfie_with_id', models.ImageField(max_length=500, upload_to='kyc/selfies/')),
                ('status', models.CharField(
                    choices=[('pending', 'Pending Review'), ('approved', 'Approved'), ('rejected', 'Rejected')],
                    db_index=True, default='pending', max_length=10
                )),
                ('rejection_reason', models.TextField(blank=True)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='kyc',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('reviewed_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='kyc_reviews',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Seller KYC',
                'verbose_name_plural': 'Seller KYCs',
                'db_table': 'seller_kyc',
                'ordering': ['-submitted_at'],
            },
        ),
    ]
