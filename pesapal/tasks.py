from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

from .models import PesapalTransaction
from utils.pesapal import check_transaction_status

# Get an instance of a logger
logger = logging.getLogger(__name__)


@shared_task
def verify_pending_transactions():
    """
    Periodically checks for transactions that are still in a PENDING state
    after a certain amount of time and verifies their status with Pesapal.
    This acts as a fallback for failed IPN callbacks.
    """
    # Check for transactions that are pending, have a tracking ID, and are older than 15 minutes.
    # This delay gives the regular IPN callback a chance to arrive first.
    time_threshold = timezone.now() - timedelta(minutes=15)
    pending_transactions = PesapalTransaction.objects.filter(
        status='PENDING',
        created_at__lt=time_threshold,
        order_tracking_id__isnull=False
    )

    logger.info(f"Found {pending_transactions.count()} pending transactions to verify.")

    for transaction in pending_transactions:
        try:
            logger.info(f"Verifying transaction {transaction.order_tracking_id}...")
            status_data = check_transaction_status(transaction.order_tracking_id)
            payment_status = status_data.get("payment_status_description")

            status_mapping = {"Completed": "COMPLETED", "Failed": "FAILED", "Cancelled": "CANCELLED"}
            new_status = status_mapping.get(payment_status)

            if new_status:
                logger.info(f"Updating transaction {transaction.order_tracking_id} from PENDING to {new_status}")
                transaction.status = new_status
                transaction.save()
        except Exception as e:
            logger.error(f"Error verifying transaction {transaction.order_tracking_id}: {str(e)}")

    return f"Verification task completed. Checked {pending_transactions.count()} transactions."


@shared_task
def send_payment_confirmation_email(transaction_id):
    """
    Sends a payment confirmation email to the user.
    This is triggered after a transaction status is updated to COMPLETED.
    """
    try:
        transaction = PesapalTransaction.objects.get(id=transaction_id)
        user_name = "Customer"
        if transaction.user and transaction.user.first_name:
            user_name = transaction.user.first_name

        logger.info(f"Sending confirmation email for transaction {transaction.order_id} to {transaction.email}")

        # --- Add your email sending logic here ---
        # from django.core.mail import send_mail
        #
        # subject = f"Your Payment for Order {transaction.order_id} is Confirmed!"
        # message = (
        #     f"Hi {user_name},\n\n"
        #     f"This is to confirm that we have received your payment of KES {transaction.amount}.\n"
        #     f"Your order is now being processed.\n\n"
        #     f"Thank you for your purchase!\n"
        # )
        # send_mail(subject, message, 'noreply@yourdomain.com', [transaction.email])
        # -----------------------------------------

        return f"Email queued for transaction ID {transaction_id}"
    except PesapalTransaction.DoesNotExist:
        logger.error(f"Cannot send email. Transaction with ID {transaction_id} not found.")
    except Exception as e:
        logger.error(f"Failed to send confirmation email for transaction ID {transaction_id}: {e}")
        # Celery can be configured to retry the task on failure.
        raise
