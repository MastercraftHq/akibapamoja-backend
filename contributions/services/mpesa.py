import os
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth
from django.utils import timezone


class MpesaDarajaClient:
    base_url        = "https://sandbox.safaricom.co.ke"
    consumer_key    = os.getenv("MPESA_CONSUMER_KEY")
    consumer_secret = os.getenv("MPESA_CONSUMER_SECRET")
    shortcode       = os.getenv("MPESA_SHORTCODE")        # e.g. "174379"
    lipa_na_mpesa_passkey = os.getenv("MPESA_PASSKEY")

    @classmethod
    def get_token(cls):
        resp = requests.get(
            f"{cls.base_url}/oauth/v1/generate?grant_type=client_credentials",
            auth=HTTPBasicAuth(cls.consumer_key, cls.consumer_secret)
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    @classmethod
    def initiate_stk_push(cls, phone_number, amount, reference, callback_url):
        token = cls.get_token()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = (cls.shortcode + cls.lipa_na_mpesa_passkey + timestamp).encode('utf-8').strip().decode('utf-8')
        payload = {
            "BusinessShortCode": cls.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": str(amount),
            "PartyA": phone_number,
            "PartyB": cls.shortcode,
            "PhoneNumber": phone_number,
            "CallbackURL": callback_url,
            "AccountReference": reference,
            "TransactionDesc": f"Chama contribution {reference}"
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        resp = requests.post(
            f"{cls.base_url}/mpesa/stkpush/v1/processrequest",
            json=payload, headers=headers
        )
        resp.raise_for_status()
        return resp.json()  # Contains CheckoutRequestID, ResponseCode, etc.
