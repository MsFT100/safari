import uuid
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from utils.pesapal import submit_order, check_transaction_status
from .models import PesapalTransaction

# It's good practice to use serializers for data validation and deserialization.
# For simplicity, we are doing it manually here.


class PesapalInitPaymentView(APIView):
    """
    Receive total amount + user details from frontend,
    and initiate payment with Pesapal.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        amount = request.data.get("amount")
        # Phone number can be optional in the request body
        phone_number = request.data.get("phone_number", "")

        if not amount:
            return Response(
                {"error": "Amount is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order_id = str(uuid.uuid4())  # unique order ID

        # Create a transaction record in your database first
        try:
            transaction = PesapalTransaction.objects.create(
                user=user,
                order_id=order_id,
                amount=amount,
                email=user.email,
                phone_number=phone_number,
                description="Payment for goods",
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to create transaction record: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = {
            "id": order_id,
            "currency": "KES",
            "amount": float(amount),
            "description": "Payment for goods",
            "callback_url": settings.PESAPAL_CALLBACK_URL,
            "notification_id": settings.PESAPAL_NOTIFICATION_ID,
            "billing_address": {
                "email_address": user.email,
                "phone_number": phone_number,
                "country_code": "KE",
                "first_name": user.first_name or "Guest",
                "last_name": user.last_name or "User",
            },
        }

        try:
            response_data = submit_order(payload)

            # Update transaction with Pesapal's tracking ID
            if response_data.get("order_tracking_id"):
                transaction.order_tracking_id = response_data.get("order_tracking_id")
                transaction.save()

            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            # If submission fails, mark our transaction as FAILED
            transaction.status = "FAILED"
            transaction.save()
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PesapalCallbackView(APIView):
    """
    Handle IPN (Instant Payment Notification) callback from Pesapal.
    This view is called by Pesapal to notify of a transaction status change.
    """

    def post(self, request):
        data = request.data
        order_tracking_id = data.get("OrderTrackingId")
        merchant_reference = data.get("OrderMerchantReference")  # This is our order_id

        if not order_tracking_id or not merchant_reference:
            return Response(
                {"error": "Missing OrderTrackingId or OrderMerchantReference"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            transaction = PesapalTransaction.objects.get(order_id=merchant_reference)

            # To be certain, query Pesapal for the final transaction status
            status_data = check_transaction_status(order_tracking_id)
            payment_status = status_data.get("payment_status_description")

            if payment_status:
                status_mapping = {
                    "Completed": "COMPLETED",
                    "Failed": "FAILED",
                    "Cancelled": "CANCELLED",
                }
                new_status = status_mapping.get(payment_status)
                if new_status:
                    transaction.status = new_status
                    transaction.save()

            return Response({"message": "Callback processed"}, status=status.HTTP_200_OK)
        except PesapalTransaction.DoesNotExist:
            return Response(
                {"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            # Log this error
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PesapalCheckStatusView(APIView):
    """
    Allows the frontend to check the transaction status from our system.
    """

    def get(self, request, order_tracking_id):
        try:
            # First, check our local database
            transaction = PesapalTransaction.objects.get(
                order_tracking_id=order_tracking_id
            )

            # If status is still pending, re-check with Pesapal to get the latest update
            if transaction.status == "PENDING":
                status_data = check_transaction_status(order_tracking_id)
                payment_status = status_data.get("payment_status_description")

                if payment_status:
                    status_mapping = {
                        "Completed": "COMPLETED",
                        "Failed": "FAILED",
                        "Cancelled": "CANCELLED",
                    }
                    new_status = status_mapping.get(payment_status)
                    if new_status and new_status != transaction.status:
                        transaction.status = new_status
                        transaction.save()

            # Return the status from our database
            response_data = {
                "order_id": transaction.order_id,
                "order_tracking_id": transaction.order_tracking_id,
                "status": transaction.status,
                "updated_at": transaction.updated_at.isoformat(),
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except PesapalTransaction.DoesNotExist:
            return Response(
                {"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
