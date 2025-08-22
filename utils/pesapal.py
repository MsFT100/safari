import requests
from django.conf import settings

def get_access_token():
    """Get Pesapal OAuth token"""
    url = f"{settings.PESAPAL_BASE_URL}/Auth/RequestToken"
    data = {
        "consumer_key": settings.PESAPAL_CONSUMER_KEY,
        "consumer_secret": settings.PESAPAL_CONSUMER_SECRET
    }
    res = requests.post(url, json=data)
    res.raise_for_status()
    return res.json().get("token")


def submit_order(payload: dict):
    """Submit order request to Pesapal"""
    url = f"{settings.PESAPAL_BASE_URL}/Transactions/SubmitOrderRequest"
    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    res = requests.post(url, json=payload, headers=headers)
    res.raise_for_status()
    return res.json()


def check_transaction_status(order_tracking_id: str):
    """Check payment status"""
    url = f"{settings.PESAPAL_BASE_URL}/Transactions/GetTransactionStatus?orderTrackingId={order_tracking_id}"
    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "Accept": "application/json",
    }
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.json()
