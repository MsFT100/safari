from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch
import uuid

from .models import PesapalTransaction

User = get_user_model()


class PesapalInitPaymentViewTests(APITestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword123",
            first_name="Test",
            last_name="User",
        )
        # Authenticate the client for subsequent requests
        self.client.force_authenticate(user=self.user)
        self.initiate_url = reverse("pesapal-initiate")
        self.payment_data = {"amount": "150.00", "phone_number": "0712345678"}

    def test_unauthenticated_user_cannot_initiate_payment(self):
        """
        Ensure unauthenticated users receive a 401 Unauthorized response.
        """
        self.client.force_authenticate(user=None)  # Log out the user
        response = self.client.post(self.initiate_url, self.payment_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_initiate_payment_fails_without_amount(self):
        """
        Ensure the request fails with a 400 error if 'amount' is not provided.
        """
        data = {"phone_number": "0712345678"}  # Missing 'amount'
        response = self.client.post(self.initiate_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Amount is required")

    @patch("pesapal.views.submit_order")
    def test_initiate_payment_success(self, mock_submit_order):
        """
        Test successful payment initiation for an authenticated user.
        """
        mock_response = {
            "order_tracking_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
            "redirect_url": "https://cybqa.pesapal.com/pesapaliframe/...",
        }
        mock_submit_order.return_value = mock_response

        response = self.client.post(self.initiate_url, self.payment_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, mock_response)

        transaction = PesapalTransaction.objects.first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.user, self.user)
        self.assertEqual(str(transaction.amount), self.payment_data["amount"])
        self.assertEqual(transaction.status, "PENDING")
        self.assertEqual(transaction.order_tracking_id, mock_response["order_tracking_id"])

    @patch("pesapal.views.submit_order")
    def test_initiate_payment_fails_on_pesapal_api_error(self, mock_submit_order):
        """
        Test that the transaction is marked as FAILED if the Pesapal API call fails.
        """
        mock_submit_order.side_effect = Exception("Pesapal API is down")

        response = self.client.post(self.initiate_url, self.payment_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["error"], "Pesapal API is down")

        transaction = PesapalTransaction.objects.first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.status, "FAILED")
        self.assertIsNone(transaction.order_tracking_id)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class PesapalCallbackViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="callbackuser",
            email="callback@example.com",
            password="testpassword123",
        )
        self.order_id = str(uuid.uuid4())
        self.order_tracking_id = "a1b2c3d4-e5f6-7890-1234-567890abcdef"
        self.transaction = PesapalTransaction.objects.create(
            user=self.user,
            order_id=self.order_id,
            order_tracking_id=self.order_tracking_id,
            amount="150.00",
            email=self.user.email,
            status="PENDING",
        )
        self.callback_url = reverse("pesapal-callback")
        self.callback_data = {
            "OrderTrackingId": self.order_tracking_id,
            "OrderMerchantReference": self.order_id,
        }

    @patch("pesapal.views.check_transaction_status")
    def test_callback_success_updates_status_to_completed(self, mock_check_status):
        """
        Test that a successful callback updates the transaction status to COMPLETED.
        """
        mock_check_status.return_value = {"payment_status_description": "Completed"}

        response = self.client.post(self.callback_url, self.callback_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, "COMPLETED")
        mock_check_status.assert_called_once_with(self.order_tracking_id)

    @patch("pesapal.views.check_transaction_status")
    def test_callback_failure_updates_status_to_failed(self, mock_check_status):
        """
        Test that a failed callback updates the transaction status to FAILED.
        """
        mock_check_status.return_value = {"payment_status_description": "Failed"}

        response = self.client.post(self.callback_url, self.callback_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, "FAILED")

    def test_callback_with_missing_data_returns_400(self):
        """
        Test that a callback with missing data returns a 400 Bad Request.
        """
        invalid_data = {"OrderTrackingId": self.order_tracking_id}  # Missing OrderMerchantReference
        response = self.client.post(self.callback_url, invalid_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_callback_for_nonexistent_transaction_returns_404(self):
        """
        Test that a callback for a transaction that doesn't exist returns a 404 Not Found.
        """
        nonexistent_data = {
            "OrderTrackingId": "some-other-tracking-id",
            "OrderMerchantReference": "nonexistent-order-id",
        }
        response = self.client.post(self.callback_url, nonexistent_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("pesapal.views.check_transaction_status")
    def test_callback_handles_pesapal_api_error_gracefully(self, mock_check_status):
        """
        Test that the view handles an exception during the status check and returns a 500 error.
        """
        mock_check_status.side_effect = Exception("Pesapal status check API is down")

        response = self.client.post(self.callback_url, self.callback_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        # Ensure the transaction status was not changed
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, "PENDING")
