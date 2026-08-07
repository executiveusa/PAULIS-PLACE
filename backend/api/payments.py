"""Payments API - 402 flow for premium assets"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from models.base import get_db
from services.payment_service import payment_service, Payment, PaymentStatus
from services.ledger_service import reconcile_event

router = APIRouter(prefix="/api/payments", tags=["payments"])


class CreatePaymentRequest(BaseModel):
    asset_type: str
    asset_id: str
    amount: float
    product_id: Optional[int] = None


class WebhookPayload(BaseModel):
    # Generic - actual payload shape varies by provider
    payload: dict


@router.post("/create")
def create_payment(req: CreatePaymentRequest):
    """Create a 402 payment requirement for an asset"""
    response = payment_service.create_402_response(
        asset_type=req.asset_type,
        asset_id=req.asset_id,
        amount=req.amount,
        product_id=req.product_id
    )
    return response["body"]


@router.get("/status/{payment_id}")
def get_payment_status(payment_id: str, db: Session = Depends(get_db)):
    """Check payment status"""
    payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    if not payment:
        raise HTTPException(404, "Payment not found")
    return payment.to_dict()


@router.post("/creem/create/{payment_id}")
async def create_creem_checkout(payment_id: str):
    """Create a Creem checkout session"""
    result = await payment_service.create_creem_checkout(payment_id)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/btcpay/create/{payment_id}")
async def create_btcpay_invoice(payment_id: str):
    """Create a BTCPay invoice"""
    result = await payment_service.create_btcpay_invoice(payment_id)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/webhooks/creem")
async def creem_webhook(req: Request):
    """Handle Creem webhook — pass 1) payment_service for DB write, 2) ledger_service for R-05 orchestration."""
    payload = await req.json()
    result = await payment_service.handle_creem_webhook(payload)

    # If status=paid, also run the spec-compliant R-05 pipeline
    status = payload.get("status", "").lower()
    if status in ("paid", "succeeded", "completed"):
        payment_id = payload.get("metadata", {}).get("payment_id") or payload.get("order_id")
        amount = payload.get("amount_total", payload.get("amount", 0)) or 0
        # Convert cents → dollars if needed
        if amount > 1000:
            amount = amount / 100.0
        product_id = payload.get("metadata", {}).get("product_id")
        customer_ref = payload.get("customer_email") or payload.get("customer")
        try:
            await reconcile_event(
                payment_id=payment_id or "pay_creem_unknown",
                provider="creem",
                amount_usd=float(amount),
                customer_ref=customer_ref,
                product_id=product_id,
                granted_access=["asset_download"],
            )
        except Exception as e:
            result["ledger_orchestration_error"] = str(e)[:300]

    return result


@router.post("/webhooks/btcpay")
async def btcpay_webhook(req: Request):
    """Handle BTCPay Server webhook — same pattern."""
    payload = await req.json()
    result = await payment_service.handle_btcpay_webhook(payload)

    status = (payload.get("type", "") or payload.get("status", "")).lower()
    if "paid" in status or "confirmed" in status:
        payment_id = payload.get("orderId") or payload.get("metadata", {}).get("payment_id")
        amount = float(payload.get("amount", 0) or 0)
        product_id = payload.get("metadata", {}).get("product_id")
        try:
            await reconcile_event(
                payment_id=payment_id or "pay_btcpay_unknown",
                provider="btcpay",
                amount_usd=amount,
                product_id=product_id,
                granted_access=["asset_download"],
            )
        except Exception as e:
            result["ledger_orchestration_error"] = str(e)[:300]

    return result


@router.get("/access/{asset_id}")
def check_access(asset_id: str):
    """Check if an asset has been paid for"""
    has_access = payment_service.check_access(asset_id)
    return {"asset_id": asset_id, "access": has_access}
