# urls.py
from django.urls import path
from .views import PesapalInitPaymentView, PesapalCallbackView, PesapalCheckStatusView

urlpatterns = [
    path("pesapal/initiate/", PesapalInitPaymentView.as_view(), name="pesapal-initiate"),
    path("pesapal/callback/", PesapalCallbackView.as_view(), name="pesapal-callback"),
    path("pesapal/status/<str:order_tracking_id>/", PesapalCheckStatusView.as_view(), name="pesapal-status"),
]
