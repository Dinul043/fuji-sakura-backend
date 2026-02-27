"""
Payment routes for handling payment processing
Mock payment implementation with gateway-ready structure
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from uuid import uuid4

from app.core.database import get_db
from app.models.orders import Order, OrderStatus, PaymentStatus as OrderPaymentStatus
from app.models.payment import Payment, PaymentStatus, PaymentMethod
from app.utils.security import get_current_user
from app.models.user import User

router = APIRouter()

# Request/Response Models
class PaymentInitiateRequest(BaseModel):
    order_id: int

class PaymentSuccessRequest(BaseModel):
    order_id: int

class PaymentFailureRequest(BaseModel):
    order_id: int
    failure_reason: str = "Payment failed"

@router.post("/initiate")
async def initiate_payment(
    request: PaymentInitiateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Initiate payment for an order
    This marks the payment as initiated (user clicked Pay Now)
    """
    try:
        # Get order
        order = db.query(Order).filter(
            Order.id == request.order_id,
            Order.user_id == current_user.id
        ).first()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Check if order is in correct state
        if order.status != OrderStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot initiate payment for order with status: {order.status.value}"
            )
        
        # Get or create payment record
        payment = db.query(Payment).filter(
            Payment.order_id == order.id,
            Payment.payment_status == PaymentStatus.PENDING
        ).first()
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment record not found"
            )
        
        # Mark payment as initiated
        payment.payment_initiated_at = datetime.now()
        payment.updated_at = datetime.now()
        db.commit()
        db.refresh(payment)
        
        return {
            "message": "Payment initiated successfully",
            "order_id": order.id,
            "order_number": order.order_number,
            "amount": payment.amount,
            "payment_method": payment.payment_method.value,
            "payment_id": payment.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Payment initiation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate payment"
        )

@router.post("/success")
async def payment_success(
    request: PaymentSuccessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark payment as successful (Mock implementation)
    In production, this will verify payment with gateway
    """
    try:
        # Get order
        order = db.query(Order).filter(
            Order.id == request.order_id,
            Order.user_id == current_user.id
        ).first()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Get payment record
        payment = db.query(Payment).filter(
            Payment.order_id == order.id
        ).order_by(Payment.created_at.desc()).first()
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment record not found"
            )
        
        # Check if already paid
        if payment.payment_status == PaymentStatus.PAID:
            return {
                "message": "Payment already completed",
                "order_id": order.id,
                "order_number": order.order_number,
                "payment_status": "paid"
            }
        
        # Generate mock transaction reference
        mock_transaction_ref = f"MOCK-{uuid4().hex[:16].upper()}"
        
        # Update payment record
        payment.payment_status = PaymentStatus.PAID
        payment.transaction_reference = mock_transaction_ref
        payment.payment_completed_at = datetime.now()
        payment.updated_at = datetime.now()
        
        # Update order
        order.payment_status = OrderPaymentStatus.PAID
        order.status = OrderStatus.CONFIRMED
        order.payment_reference = mock_transaction_ref
        order.confirmed_at = datetime.now()
        order.updated_at = datetime.now()
        
        db.commit()
        db.refresh(order)
        db.refresh(payment)
        
        # Clear user's cart (optional - if cart items belong to this order)
        # This can be done in order creation instead
        
        return {
            "message": "Payment successful",
            "order_id": order.id,
            "order_number": order.order_number,
            "transaction_reference": mock_transaction_ref,
            "payment_status": "paid",
            "order_status": "confirmed",
            "confirmed_at": order.confirmed_at.isoformat() if order.confirmed_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Payment success error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process payment success"
        )

@router.post("/failure")
async def payment_failure(
    request: PaymentFailureRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark payment as failed (Mock implementation)
    Allows user to retry payment
    """
    try:
        # Get order
        order = db.query(Order).filter(
            Order.id == request.order_id,
            Order.user_id == current_user.id
        ).first()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Get payment record
        payment = db.query(Payment).filter(
            Payment.order_id == order.id
        ).order_by(Payment.created_at.desc()).first()
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment record not found"
            )
        
        # Update payment record
        payment.payment_status = PaymentStatus.FAILED
        payment.failure_reason = request.failure_reason
        payment.retry_count += 1
        payment.updated_at = datetime.now()
        
        # Update order - keep as PENDING (allow retry)
        order.payment_status = OrderPaymentStatus.FAILED
        # Don't change order.status - keep as PENDING so user can retry
        order.updated_at = datetime.now()
        
        db.commit()
        db.refresh(order)
        db.refresh(payment)
        
        return {
            "message": "Payment failed",
            "order_id": order.id,
            "order_number": order.order_number,
            "payment_status": "failed",
            "failure_reason": request.failure_reason,
            "retry_count": payment.retry_count,
            "can_retry": payment.retry_count < 3  # Allow max 3 retries
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Payment failure error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process payment failure"
        )

@router.get("/status/{order_id}")
async def get_payment_status(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get payment status for an order
    """
    try:
        # Get order
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == current_user.id
        ).first()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Get latest payment record
        payment = db.query(Payment).filter(
            Payment.order_id == order.id
        ).order_by(Payment.created_at.desc()).first()
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment record not found"
            )
        
        return {
            "order_id": order.id,
            "order_number": order.order_number,
            "order_status": order.status.value,
            "payment_status": payment.payment_status.value,
            "payment_method": payment.payment_method.value,
            "amount": payment.amount,
            "transaction_reference": payment.transaction_reference,
            "failure_reason": payment.failure_reason,
            "retry_count": payment.retry_count,
            "can_retry": payment.retry_count < 3 and payment.payment_status == PaymentStatus.FAILED,
            "created_at": payment.created_at.isoformat() if payment.created_at else None,
            "payment_completed_at": payment.payment_completed_at.isoformat() if payment.payment_completed_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get payment status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get payment status"
        )
