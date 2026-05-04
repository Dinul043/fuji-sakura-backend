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

# Debug endpoint to test Razorpay
@router.get("/razorpay/test")
async def test_razorpay():
    """Test Razorpay configuration"""
    try:
        from app.core.config import settings
        
        # Test order creation
        result = razorpay_service.create_order(
            amount=100.0,
            order_id=999
        )
        
        return {
            "config": {
                "key_id": settings.RAZORPAY_KEY_ID,
                "payment_mode": settings.PAYMENT_MODE
            },
            "test_result": result
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@router.get("/razorpay/test-with-order/{order_id}")
async def test_razorpay_with_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test Razorpay with actual order"""
    try:
        # Get order
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == current_user.id
        ).first()
        
        if not order:
            return {"error": "Order not found"}
        
        # Get payment
        payment = db.query(Payment).filter(
            Payment.order_id == order.id
        ).order_by(Payment.created_at.desc()).first()
        
        if not payment:
            return {"error": "Payment not found"}
        
        # Try to create Razorpay order
        result = razorpay_service.create_order(
            amount=payment.amount,
            order_id=order.id
        )
        
        return {
            "order": {
                "id": order.id,
                "status": order.status.value,
                "total": payment.amount
            },
            "payment": {
                "id": payment.id,
                "method": payment.payment_method.value,
                "status": payment.payment_status.value
            },
            "razorpay_result": result
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

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


# ============================================
# RAZORPAY INTEGRATION ROUTES
# ============================================

from app.services.razorpay_service import razorpay_service
from app.core.config import settings

class RazorpayOrderRequest(BaseModel):
    order_id: int

class RazorpayVerifyRequest(BaseModel):
    order_id: int
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

@router.post("/razorpay/create-order")
async def create_razorpay_order(
    request: RazorpayOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create Razorpay order for payment
    Returns razorpay_order_id and key_id for frontend
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
                detail=f"Cannot create payment for order with status: {order.status.value}"
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
        
        # Check payment mode
        if settings.PAYMENT_MODE != "razorpay":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Razorpay payment mode is not enabled"
            )
        
        # Create Razorpay order
        print(f"Creating Razorpay order for order_id={order.id}, amount={payment.amount}")
        try:
            razorpay_result = razorpay_service.create_order(
                amount=payment.amount,
                order_id=order.id
            )
            
            print(f"Razorpay result: {razorpay_result}")
            
            if not razorpay_result["success"]:
                error_msg = razorpay_result.get('error', 'Unknown error')
                print(f"❌ Razorpay order creation failed: {error_msg}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create Razorpay order: {error_msg}"
                )
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Exception in Razorpay order creation: {str(e)}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Razorpay error: {str(e)}"
            )
        
        # Update payment record with Razorpay order ID
        payment.gateway_order_id = razorpay_result["razorpay_order_id"]
        payment.payment_initiated_at = datetime.now()
        payment.updated_at = datetime.now()
        db.commit()
        db.refresh(payment)
        
        return {
            "success": True,
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "razorpay_order_id": razorpay_result["razorpay_order_id"],
            "amount": razorpay_result["amount"],  # Amount in paise
            "currency": razorpay_result["currency"],
            "order_id": order.id,
            "order_number": order.order_number
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Create Razorpay order error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create Razorpay order"
        )

@router.post("/razorpay/verify")
async def verify_razorpay_payment(
    request: RazorpayVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Verify Razorpay payment signature and update order status
    This is called after user completes payment in Razorpay popup
    """
    try:
        print(f"\n{'='*60}")
        print(f"PAYMENT VERIFICATION REQUEST")
        print(f"{'='*60}")
        print(f"Order ID: {request.order_id}")
        print(f"User ID: {current_user.id}")
        print(f"Razorpay Order ID: {request.razorpay_order_id}")
        print(f"Razorpay Payment ID: {request.razorpay_payment_id}")
        
        # Get order
        order = db.query(Order).filter(
            Order.id == request.order_id,
            Order.user_id == current_user.id
        ).first()
        
        if not order:
            print(f"❌ Order not found: {request.order_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        print(f"✅ Order found: {order.order_number}")
        
        # Get payment record
        payment = db.query(Payment).filter(
            Payment.order_id == order.id
        ).order_by(Payment.created_at.desc()).first()
        
        if not payment:
            print(f"❌ Payment record not found for order: {order.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment record not found"
            )
        
        print(f"✅ Payment record found: ID={payment.id}")
        
        # Verify payment signature
        is_valid = razorpay_service.verify_payment_signature(
            razorpay_order_id=request.razorpay_order_id,
            razorpay_payment_id=request.razorpay_payment_id,
            razorpay_signature=request.razorpay_signature
        )
        
        if not is_valid:
            # Signature verification failed
            payment.payment_status = PaymentStatus.FAILED
            payment.failure_reason = "Payment signature verification failed"
            payment.retry_count += 1
            payment.updated_at = datetime.now()
            
            order.payment_status = OrderPaymentStatus.FAILED
            order.updated_at = datetime.now()
            
            db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment signature"
            )
        
        # Fetch payment details from Razorpay
        payment_details = razorpay_service.fetch_payment(request.razorpay_payment_id)
        
        if not payment_details["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch payment details from Razorpay"
            )
        
        # Update payment record
        payment.payment_status = PaymentStatus.PAID
        payment.gateway_payment_id = request.razorpay_payment_id
        payment.gateway_signature = request.razorpay_signature
        payment.transaction_reference = request.razorpay_payment_id
        payment.payment_completed_at = datetime.now()
        payment.updated_at = datetime.now()
        
        # Update order
        order.payment_status = OrderPaymentStatus.PAID
        order.status = OrderStatus.CONFIRMED
        order.payment_reference = request.razorpay_payment_id
        order.confirmed_at = datetime.now()
        order.updated_at = datetime.now()
        
        # Clear cart items for this order (only after successful payment)
        from app.models.user_cart import UserCart
        from app.models.orders import OrderItem
        
        # Get order items
        order_items = db.query(OrderItem).filter(
            OrderItem.order_id == order.id
        ).all()
        
        print(f"📦 Found {len(order_items)} order items to clear from cart")
        
        # Delete cart items that match the order items
        for order_item in order_items:
            cart_items_to_delete = db.query(UserCart).filter(
                UserCart.user_id == current_user.id,
                UserCart.menu_item_id == order_item.menu_item_id,
                UserCart.restaurant_id == order.restaurant_id
            ).all()
            
            for cart_item in cart_items_to_delete:
                db.delete(cart_item)
                print(f"🗑️  Deleted cart item: {cart_item.item_name}")
        
        print(f"✅ Cart cleared for user {current_user.id} after successful payment")
        
        db.commit()
        db.refresh(order)
        db.refresh(payment)
        
        # Send real-time notification to restaurant
        from app.utils.websocket_manager import manager
        try:
            await manager.send_restaurant_notification(
                restaurant_id=order.restaurant_id,
                notification_data={
                    "type": "new_order",
                    "id": order.id,
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "customer_name": order.customer_name,
                    "customer_email": order.customer_email,
                    "delivery_phone": order.delivery_phone,
                    "delivery_address": order.delivery_address,
                    "total_amount": float(order.total_amount),
                    "payment_method": order.payment_method,
                    "special_instructions": order.special_instructions,
                    "status": "confirmed",
                    "items_count": len(order_items),
                    "items": [
                        {
                            "name": item.item_name,
                            "quantity": item.quantity,
                            "price": float(item.item_price),
                            "is_veg": item.is_veg
                        }
                        for item in order_items
                    ],
                    "created_at": datetime.now().isoformat()
                }
            )
            print(f"✅ Real-time notification sent to restaurant {order.restaurant_id}")
        except Exception as e:
            print(f"⚠️ Failed to send real-time notification: {e}")
            # Don't fail the payment if notification fails

        # NOTE: Do NOT notify delivery partners here.
        # Partners only see orders when restaurant marks READY (order_ready_for_pickup event).
        # Sending new_order here causes premature notifications before food is prepared.
        
        return {
            "success": True,
            "message": "Payment verified successfully",
            "order_id": order.id,
            "order_number": order.order_number,
            "payment_id": request.razorpay_payment_id,
            "order_status": "confirmed",
            "payment_status": "paid"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Verify Razorpay payment error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify payment"
        )
