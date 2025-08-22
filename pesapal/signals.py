import logging

from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import PesapalTransaction
from .tasks import send_payment_confirmation_email

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=PesapalTransaction)
def on_transaction_status_change(sender, instance, **kwargs):
    """
    Listens for a change in the transaction status and triggers business logic
    when a payment is successfully completed.
    """
    # We only care about updates to existing transactions, not new ones.
    if instance.pk is None:
        return

    try:
        # Get the state of the object as it is in the database before this save.
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return  # Should not happen for an existing instance, but good to be safe.

    # Check if the status has changed from a non-completed state to COMPLETED.
    if old_instance.status != "COMPLETED" and instance.status == "COMPLETED":
        logger.info(f"Transaction {instance.order_id} completed. Triggering post-payment actions.")
        # Use .delay() to run this as an asynchronous Celery task.
        send_payment_confirmation_email.delay(instance.id)
