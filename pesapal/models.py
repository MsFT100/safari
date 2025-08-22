from django.db import models
from django.conf import settings


class PesapalTransaction(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,  # Keep transaction record if user is deleted
        null=True,
        blank=True,
    )
    order_id = models.CharField(max_length=100, unique=True)  # UUID from your system
    order_tracking_id = models.CharField(max_length=100, blank=True, null=True)  # From Pesapal
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    description = models.CharField(max_length=255, default="Payment for goods")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.order_id} - {self.status}"
