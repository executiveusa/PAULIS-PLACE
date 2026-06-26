"""
402 PAYMENT GATEWAY - Bitcoin (BTCPay) & Creem
===============================================
Middleware logic for HTTP 402 Payment Required.

Flow:
1. User requests premium asset
2. Backend returns 402 with X-Payment-Required header
3. Frontend shows payment modal (Card via Creem, or BTC via BTCPay)
4. Webhook hits backend -> DB updated -> asset released
"""

import httpx
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Float, Boolean
from enum import Enum
from models.base import Base, SessionLocal
from config import SETTINGS


class PaymentProvider(str, Enum):
    CREEM = "creem"
    BTCPAY = "btcpay"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    EXPIRED = "expired"
    REFUNDED = "refunded"


class Payment(Base):
    """Payment records for 402-gated assets"""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(String(100), unique=True, index=True)  # Internal ID
    external_id = Column(String(200), nullable=True)  # Provider's ID

    # What's being purchased
    product_id = Column(Integer, nullable=True)
    asset_type = Column(String(50))  # "pro_template", "premium_design", etc.
    asset_id = Column(String(200), nullable=True)

    # Payment details
    provider = Column(String(50))  # "creem" or "btcpay"
    amount = Column(Float)
    currency = Column(String(10), default="USD")
    status = Column(String(50), default=PaymentStatus.PENDING.value)

    # BTC-specific
    btc_address = Column(String(200), nullable=True)
    btc_amount = Column(Float, nullable=True)
    btc_invoice_url = Column(String(1000), nullable=True)

    # Creem-specific
    creem_checkout_url = Column(String(1000), nullable=True)

    # Metadata
    customer_email = Column(String(200), nullable=True)
    payment_metadata = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "payment_id": self.payment_id,
            "external_id": self.external_id,
            "product_id": self.product_id,
            "asset_type": self.asset_type,
            "provider": self.provider,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
            "btc_address": self.btc_address,
            "btc_amount": self.btc_amount,
            "btc_invoice_url": self.btc_invoice_url,
            "creem_checkout_url": self.creem_checkout_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
        }


class PaymentService:
    """
    402 Payment Gateway.

    Usage in FastAPI:
        @app.get("/api/assets/{asset_id}")
        async def get_asset(asset_id: str, request: Request):
            payment_required = payment_service.check_payment_required(asset_id, request)
            if payment_required:
                return payment_required  # Returns 402 response
            return asset_data
    """

    def __init__(self):
        self.creem_api_key = SETTINGS.creem_api_key
        self.btcpay_url = SETTINGS.btcpay_api_url
        self.btcpay_store_id = SETTINGS.btcpay_store_id
        self.btcpay_api_key = SETTINGS.btcpay_api_key

    def create_402_response(self, asset_type: str, asset_id: str, amount: float, product_id: Optional[int] = None) -> Dict:
        """Create a 402 Payment Required response payload"""
        payment_id = f"pay_{uuid.uuid4().hex[:16]}"

        # Create pending payment record
        db = SessionLocal()
        try:
            payment = Payment(
                payment_id=payment_id,
                product_id=product_id,
                asset_type=asset_type,
                asset_id=asset_id,
                amount=amount,
                currency="USD",
                status=PaymentStatus.PENDING.value,
                payment_metadata={"created_by": "402_middleware"}
            )
            db.add(payment)
            db.commit()
        finally:
            db.close()

        return {
            "status_code": 402,
            "detail": "Payment Required",
            "headers": {
                "X-Payment-Required": "creem|btcpay",
                "X-Payment-Id": payment_id,
                "X-Payment-Amount": str(amount),
                "X-Payment-Currency": "USD",
            },
            "body": {
                "payment_id": payment_id,
                "amount": amount,
                "currency": "USD",
                "providers": ["creem", "btcpay"],
                "message": f"Pay ${amount:.2f} via Card (Creem) or Bitcoin to access this asset.",
                "endpoints": {
                    "creem": f"/api/payments/creem/create/{payment_id}",
                    "btcpay": f"/api/payments/btcpay/create/{payment_id}",
                }
            }
        }

    async def create_creem_checkout(self, payment_id: str) -> Dict:
        """Create a Creem checkout session"""
        db = SessionLocal()
        try:
            payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
            if not payment:
                return {"error": "Payment not found"}

            # Call Creem API
            headers = {
                "Authorization": f"Bearer {self.creem_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "amount": int(payment.amount * 100),  # Cents
                "currency": payment.currency.lower(),
                "metadata": {
                    "payment_id": payment_id,
                    "asset_type": payment.asset_type,
                    "asset_id": payment.asset_id,
                },
                "success_url": f"{SETTINGS.app_url}/payment/success?payment_id={payment_id}",
                "cancel_url": f"{SETTINGS.app_url}/payment/cancel?payment_id={payment_id}",
            }

            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(
                        "https://api.creem.io/v1/checkout/sessions",
                        headers=headers,
                        json=payload
                    )
                    if response.status_code in (200, 201):
                        data = response.json()
                        payment.external_id = data.get("id")
                        payment.creem_checkout_url = data.get("url") or data.get("checkout_url")
                        payment.provider = PaymentProvider.CREEM.value
                        db.commit()

                        return {
                            "checkout_url": payment.creem_checkout_url,
                            "payment_id": payment_id
                        }
                    return {"error": f"Creem API error: {response.text}"}
            except Exception as e:
                return {"error": f"Creem request failed: {e}"}
        finally:
            db.close()

    async def create_btcpay_invoice(self, payment_id: str) -> Dict:
        """Create a BTCPay Server invoice"""
        db = SessionLocal()
        try:
            payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
            if not payment:
                return {"error": "Payment not found"}

            headers = {
                "Authorization": f"token {self.btcpay_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "amount": payment.amount,
                "currency": payment.currency,
                "orderId": payment_id,
                "buyer": {},
                "metadata": {
                    "payment_id": payment_id,
                    "asset_type": payment.asset_type,
                    "asset_id": payment.asset_id,
                },
                "checkout": {
                    "redirectURL": f"{SETTINGS.app_url}/payment/success?payment_id={payment_id}",
                }
            }

            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(
                        f"{self.btcpay_url}/api/v1/stores/{self.btcpay_store_id}/invoices",
                        headers=headers,
                        json=payload
                    )
                    if response.status_code in (200, 201):
                        data = response.json()
                        payment.external_id = data.get("id")
                        payment.btc_address = data.get("bitcoinAddress")
                        payment.btc_amount = float(data.get("amount", 0)) if data.get("amount") else None
                        payment.btc_invoice_url = data.get("checkoutLink") or data.get("url")
                        payment.provider = PaymentProvider.BTCPAY.value
                        db.commit()

                        return {
                            "invoice_url": payment.btc_invoice_url,
                            "btc_address": payment.btc_address,
                            "btc_amount": payment.btc_amount,
                            "payment_id": payment_id
                        }
                    return {"error": f"BTCPay API error: {response.text}"}
            except Exception as e:
                return {"error": f"BTCPay request failed: {e}"}
        finally:
            db.close()

    async def handle_creem_webhook(self, payload: Dict) -> Dict:
        """Handle Creem webhook"""
        payment_id = payload.get("metadata", {}).get("payment_id") or payload.get("order_id")
        status = payload.get("status", "").lower()

        db = SessionLocal()
        try:
            payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
            if not payment:
                return {"error": "Payment not found"}

            if status in ("paid", "succeeded", "completed"):
                payment.status = PaymentStatus.PAID.value
                payment.paid_at = datetime.utcnow()
            elif status in ("failed", "cancelled"):
                payment.status = PaymentStatus.FAILED.value

            db.commit()
            return {"status": "ok", "payment_status": payment.status}
        finally:
            db.close()

    async def handle_btcpay_webhook(self, payload: Dict) -> Dict:
        """Handle BTCPay Server webhook"""
        invoice_id = payload.get("invoiceId") or payload.get("id")
        status = payload.get("type", "").lower()  # "invoice_paid", "invoice_confirmed", etc.

        db = SessionLocal()
        try:
            payment = db.query(Payment).filter(Payment.external_id == invoice_id).first()
            if not payment:
                # Try by metadata
                payment = db.query(Payment).filter(
                    Payment.payment_metadata['btcpay_invoice_id'].as_string() == invoice_id
                ).first()
            if not payment:
                return {"error": "Payment not found"}

            if "paid" in status or "confirmed" in status:
                payment.status = PaymentStatus.PAID.value
                payment.paid_at = datetime.utcnow()
            elif "expired" in status:
                payment.status = PaymentStatus.EXPIRED.value
            elif "failed" in status or "invalid" in status:
                payment.status = PaymentStatus.FAILED.value

            db.commit()
            return {"status": "ok", "payment_status": payment.status}
        finally:
            db.close()

    def check_access(self, asset_id: str, user_token: Optional[str] = None) -> bool:
        """Check if user has paid for an asset"""
        db = SessionLocal()
        try:
            payment = db.query(Payment).filter(
                Payment.asset_id == asset_id,
                Payment.status == PaymentStatus.PAID.value
            ).first()
            return payment is not None
        finally:
            db.close()


payment_service = PaymentService()
