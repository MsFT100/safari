import uuid
from cairo import Status
from django.conf import settings
from django.shortcuts import render
from requests import Response

from utils.pesapal import submit_order



class PesapalInitPaymentView(APIView):
    """
    Receive total amount + user details from frontend,
    and initiate payment with Pesapal.
    """

    def post(self, request):
        amount = request.data.get("amount")
        email = request.data.get("email")
        phone_number = request.data.get("phone_number", "")

        if not amount or not email:
            return Response(
                {"error": "Amount and email are required"},
                status=Status.HTTP_400_BAD_REQUEST
            )

        order_id = str(uuid.uuid4())  # unique order ID

        payload = {
            "id": order_id,
            "currency": "KES",
            "amount": amount,
            "description": "Payment for goods",
            "callback_url": settings.PESAPAL_CALLBACK_URL,
            "notification_id": "your-notification-id",  # from Pesapal portal
            "billing_address": {
                "email_address": email,
                "phone_number": phone_number,
                "country_code": "KE",
                "first_name": "John",
                "last_name": "Doe",
            }
        }

        try:
            response_data = submit_order(payload)
            return Response(response_data, status=Status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=Status.HTTP_500_INTERNAL_SERVER_ERROR)


class PesapalCallbackView(APIView):
    """
    Handle callback notification from Pesapal after payment.
    """

    def post(self, request):
        data = request.data
        # Example payload: {"order_tracking_id": "...", "status": "COMPLETED"}
        # Update your order/payment model here
        return Response({"message": "Callback received", "data": data}, status=status.HTTP_200_OK)


class PesapalCheckStatusView(APIView):
    """
    Check transaction status from your system
    """

    def get(self, request, order_tracking_id):
        try:
            status_data = check_transaction_status(order_tracking_id)
            return Response(status_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
