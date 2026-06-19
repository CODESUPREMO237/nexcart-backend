"""
NexCart Delivery Zone Models
Zone-based delivery pricing and estimation for Cameroon
"""
from django.db import models
from django.core.validators import MinValueValidator
import uuid


class DeliveryZone(models.Model):
    """Delivery zone with pricing tiers"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    region = models.CharField(max_length=100, help_text="e.g. South West, Littoral, Centre")
    description = models.TextField(blank=True)

    # Pricing
    base_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=500,
        validators=[MinValueValidator(0)],
        help_text="Base delivery fee in FCFA"
    )
    free_delivery_threshold = models.DecimalField(
        max_digits=10, decimal_places=2, default=25000,
        validators=[MinValueValidator(0)],
        help_text="Free delivery for orders above this amount"
    )

    # Estimated delivery time
    estimated_days_min = models.IntegerField(default=1, validators=[MinValueValidator(0)])
    estimated_days_max = models.IntegerField(default=3, validators=[MinValueValidator(1)])

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'delivery_zones'
        verbose_name = 'Delivery Zone'
        verbose_name_plural = 'Delivery Zones'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.region})"


class DeliveryArea(models.Model):
    """Specific delivery area (town/quarter) within a zone"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zone = models.ForeignKey(DeliveryZone, on_delete=models.CASCADE, related_name='areas')
    name = models.CharField(max_length=200, help_text="Town or quarter name")
    city = models.CharField(max_length=100)

    # Optional surcharge for specific areas
    surcharge = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
        help_text="Additional fee for this area"
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'delivery_areas'
        verbose_name = 'Delivery Area'
        verbose_name_plural = 'Delivery Areas'
        ordering = ['city', 'name']
        unique_together = ['zone', 'name', 'city']

    def __str__(self):
        return f"{self.name}, {self.city}"

    @property
    def total_delivery_fee(self):
        return self.zone.base_fee + self.surcharge
