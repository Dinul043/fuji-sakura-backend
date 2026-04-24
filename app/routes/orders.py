"""
Order API endpoints for order management
Production-ready order system with proper error handling
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime, timezone
from app.core.database import get_db
from app.models.user import User
from app.models.orders import Order, OrderItem, OrderStatus, PaymentStatus as OrderPaymentStatus
from app.models.payment import Payment, PaymentStatus, PaymentMethod
from app.models.user_cart import UserCart
from app.models.restaurant_menu import RestaurantMenu
from app.models.restaurant_application import RestaurantApplication
from app.utils.security import get_current_user
from app.utils.websocket_manager import manager

router = APIRouter()

class DeliveryAddressModel(BaseModel):
    fullName: str
    phone: str
    address: str
    landmark: Optional[str] = ""
    city: str
    pincode: str

class CreateOrderRequest(BaseModel):
    delivery_address: DeliveryAddressModel
    payment_method: str
    special_instructions: Optional[str] = ""
    cart_items: List[int]  # List of cart item IDs to order

@router.post("/create")
async def create_order(
    request: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new order from cart items"""
    try:
        # Validate cart items exist and belong to user
        cart_items = db.query(UserCart).filter(
            UserCart.id.in_(request.cart_items),
            UserCart.user_id == current_user.id
        ).all()
        
        if not cart_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid cart items found"
            )
        
        # Group items by restaurant
        restaurants = {}
        for item in cart_items:
            if item.restaurant_id not in restaurants:
                restaurants[item.restaurant_id] = []
            restaurants[item.restaurant_id].append(item)
        
        # Create orders (one per restaurant)
        created_orders = []
        
        for restaurant_id, items in restaurants.items():
            # Get restaurant details
            restaurant = db.query(RestaurantApplication).filter(
                RestaurantApplication.id == restaurant_id
            ).first()
            
            if not restaurant:
                continue

            # Calculate totals
            subtotal = sum(item.total_price for item in items)
            delivery_fee = 40.00  # Fixed delivery fee — paid to delivery partner
            tax_amount = subtotal * 0.08
            total_amount = subtotal + delivery_fee + tax_amount
            
            # Generate order number
            # Generate unique order number using max ID to avoid duplicates after deletions
            from sqlalchemy import func
            max_id = db.query(func.max(Order.id)).scalar() or 0
            order_number = f"ORD-{datetime.now().year}-{max_id + 1:06d}"
            # Ensure uniqueness — if somehow still duplicate, add timestamp
            existing = db.query(Order).filter(Order.order_number == order_number).first()
            if existing:
                import time
                order_number = f"ORD-{datetime.now().year}-{int(time.time()) % 1000000:06d}"
            
            # Format delivery address
            addr = request.delivery_address
            delivery_address_text = f"{addr.address}"
            if addr.landmark:
                delivery_address_text += f", {addr.landmark}"
            delivery_address_text += f", {addr.city} - {addr.pincode}"
            
            # Create order
            order = Order(
                order_number=order_number,
                user_id=current_user.id,
                restaurant_id=restaurant_id,
                status=OrderStatus.CONFIRMED if request.payment_method == 'cod' else OrderStatus.PENDING,
                payment_status=OrderPaymentStatus.PENDING,
                subtotal=subtotal,
                delivery_fee=delivery_fee,
                tax_amount=tax_amount,
                total_amount=total_amount,
                delivery_address=delivery_address_text,
                delivery_phone=addr.phone,
                customer_name=addr.fullName,
                customer_email=current_user.email,
                restaurant_name=restaurant.business_name,
                estimated_delivery_time=30,
                payment_method=request.payment_method,
                special_instructions=request.special_instructions,
                confirmed_at=datetime.now() if request.payment_method == 'cod' else None
            )
            
            db.add(order)
            db.flush()  # Get order ID
            
            # Create payment record
            # Map payment method string to enum (case-insensitive)
            payment_method_map = {
                'cod': PaymentMethod.COD,
                'online': PaymentMethod.ONLINE,
                'cash on delivery': PaymentMethod.COD,
                # Legacy support (in case old values come through)
                'card': PaymentMethod.ONLINE,
                'upi': PaymentMethod.ONLINE,
                'wallet': PaymentMethod.ONLINE,
                'credit card': PaymentMethod.ONLINE,
                'debit card': PaymentMethod.ONLINE,
            }
            
            payment_method_str = request.payment_method.lower().strip()
            payment_method_enum = payment_method_map.get(payment_method_str, PaymentMethod.ONLINE)
            
            payment = Payment(
                order_id=order.id,
                payment_method=payment_method_enum,
                amount=total_amount,
                payment_status=PaymentStatus.PENDING
            )
            db.add(payment)
            
            # Create order items
            for cart_item in items:
                order_item = OrderItem(
                    order_id=order.id,
                    menu_item_id=cart_item.menu_item_id,
                    item_name=cart_item.item_name,
                    item_description=cart_item.item_description,
                    item_price=cart_item.item_price,
                    item_image_url=cart_item.item_image_url,
                    item_category=cart_item.item_category,
                    is_veg=cart_item.is_veg,
                    quantity=cart_item.quantity,
                    special_instructions=""
                )
                db.add(order_item)
            
            # For COD orders, remove items from cart immediately
            # For online payments, cart will be cleared after successful payment
            if request.payment_method == 'cod':
                for cart_item in items:
                    db.delete(cart_item)
            
            created_orders.append(order)
        
        db.commit()
        
        # Refresh orders to get all relationships
        for order in created_orders:
            db.refresh(order)

        # Notify restaurant via WebSocket — ONLY for COD orders (confirmed immediately)
        # For online payment orders, notification is sent after Razorpay payment verification
        for order in created_orders:
            if order.payment_method and order.payment_method.lower() == 'cod':
                await manager.send_restaurant_notification(order.restaurant_id, {
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "customer_name": order.customer_name,
                    "total_amount": order.total_amount,
                    "payment_method": order.payment_method,
                    "special_instructions": order.special_instructions,
                    "items": [item.to_dict() for item in order.order_items],
                    "created_at": order.created_at.isoformat() if order.created_at else None
                })
                # Also notify delivery partners that a new order is available
                await manager.broadcast_to_delivery_partners({
                    "type": "new_order",
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "restaurant_name": order.restaurant_name,
                    "total_amount": order.total_amount,
                    "payment_method": order.payment_method,
                })
        
        return {
            "message": "Order placed successfully",
            "orders": [order.to_dict() for order in created_orders]
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import traceback
        print(f"❌ Error creating order: {str(e)}")
        print(f"❌ Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create order: {str(e)}"
        )

@router.get("/", response_model=List[Dict[str, Any]])
async def get_user_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all orders for the current user (excluding pending unpaid orders)"""
    try:
        # Only show orders that are confirmed or beyond
        # Exclude PENDING orders (waiting for payment)
        orders = db.query(Order).filter(
            Order.user_id == current_user.id,
            Order.status != OrderStatus.PENDING  # Exclude pending orders
        ).order_by(Order.created_at.desc()).all()
        
        return [order.to_dict() for order in orders]
        
    except Exception as e:
        print(f"❌ Error fetching orders: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch orders"
        )

@router.get("/{order_id}")
async def get_order_details(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get details of a specific order"""
    try:
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == current_user.id
        ).first()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        return order.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching order details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch order details"
        )

@router.get("/restaurant/{restaurant_id}")
async def get_restaurant_orders(
    restaurant_id: int,
    db: Session = Depends(get_db)
):
    """Get all orders for a specific restaurant (for restaurant dashboard)"""
    try:
        from app.models.delivery_partner import DeliveryPartner
        orders = db.query(Order).filter(
            Order.restaurant_id == restaurant_id,
            Order.status != OrderStatus.PENDING
        ).order_by(Order.created_at.desc()).all()

        result = []
        for order in orders:
            d = order.to_dict()
            # Include delivery partner name if assigned
            if order.delivery_partner_id:
                partner = db.query(DeliveryPartner).filter(DeliveryPartner.id == order.delivery_partner_id).first()
                if partner:
                    d["delivery_partner_name"] = partner.name
                    d["delivery_partner_phone"] = partner.phone
            result.append(d)

        return result

    except Exception as e:
        print(f"❌ Error fetching restaurant orders: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch restaurant orders"
        )

class UpdateOrderStatusRequest(BaseModel):
    status: str

@router.put("/{order_id}/status")
async def update_order_status(
    order_id: int,
    request: UpdateOrderStatusRequest,
    db: Session = Depends(get_db)
):
    """Update order status (for restaurant dashboard)"""
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Validate status
        try:
            new_status = OrderStatus(request.status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid order status"
            )
        
        # Handle cancellation with refund for online payments
        if new_status == OrderStatus.CANCELLED:
            # Check if payment was made online
            if order.payment_method and order.payment_method.lower() == 'online':
                # Get the payment record
                from app.models.payment import Payment, PaymentStatus as PayStatus
                payment = db.query(Payment).filter(
                    Payment.order_id == order_id,
                    Payment.payment_status == PayStatus.PAID
                ).first()
                
                if payment and payment.gateway_payment_id:
                    print(f"💰 Initiating refund for order {order.order_number}")
                    print(f"   Payment ID: {payment.gateway_payment_id}")
                    print(f"   Amount: ₹{order.total_amount}")
                    
                    # Initiate refund via Razorpay
                    from app.services.razorpay_service import razorpay_service
                    refund_result = razorpay_service.refund_payment(
                        payment_id=payment.gateway_payment_id,
                        amount=order.total_amount
                    )
                    
                    if refund_result.get('success'):
                        print(f"✅ Refund initiated successfully")
                        print(f"   Refund ID: {refund_result['refund'].get('id')}")
                        
                        # Update payment status to refunded
                        payment.payment_status = PayStatus.REFUNDED
                        payment.failure_reason = "Order cancelled by restaurant - Refund initiated"
                        
                        # Update order payment status (use the Order model's PaymentStatus)
                        order.payment_status = PaymentStatus.REFUNDED
                    else:
                        error_msg = refund_result.get('error', 'Unknown error')
                        print(f"❌ Refund failed: {error_msg}")
                        
                        # Check if already refunded
                        if 'already' in error_msg.lower() and 'refund' in error_msg.lower():
                            print(f"ℹ️ Payment already refunded, updating status")
                            payment.payment_status = PayStatus.REFUNDED
                            order.payment_status = OrderPaymentStatus.REFUNDED
                        else:
                            # For other errors, just log but still cancel the order
                            print(f"⚠️ Continuing with cancellation despite refund failure")
                            payment.failure_reason = f"Refund failed: {error_msg}"
                            # Don't change payment_status if refund fails
                elif order.payment_status == PaymentStatus.REFUNDED:
                    print(f"ℹ️ Order already has refunded status, skipping refund")
        
        # Update order status
        order.status = new_status
        
        # Update delivered_at if status is delivered
        if new_status == OrderStatus.DELIVERED:
            order.delivered_at = datetime.now()
            # Auto-create restaurant payout record (dedup protected by unique order_id)
            try:
                from app.models.restaurant_payout import RestaurantPayout, PLATFORM_COMMISSION_RATE
                existing_payout = db.query(RestaurantPayout).filter(
                    RestaurantPayout.order_id == order.id
                ).first()
                if not existing_payout:
                    commission_amount = round(order.subtotal * PLATFORM_COMMISSION_RATE / 100, 2)
                    payout_amount = round(order.subtotal - commission_amount, 2)
                    payout = RestaurantPayout(
                        restaurant_id=order.restaurant_id,
                        order_id=order.id,
                        order_amount=order.subtotal,
                        commission_rate=PLATFORM_COMMISSION_RATE,
                        commission_amount=commission_amount,
                        payout_amount=payout_amount,
                        status="pending"
                    )
                    db.add(payout)
            except Exception as e:
                print(f"⚠️ Failed to create restaurant payout for order {order.id}: {e}")
        
        db.commit()
        db.refresh(order)
        
        # Broadcast update via WebSocket to user tracking
        await manager.send_order_update(order_id, {
            "type": "order_status_update",
            "order_id": order_id,
            "status": new_status.value,
            "order": order.to_dict()
        })

        # When READY — notify delivery partners via channel 0 (delivery partner dashboard)
        if new_status == OrderStatus.READY:
            await manager.broadcast_to_delivery_partners({
                "type": "order_ready_for_pickup",
                "order_id": order.id,
                "order_number": order.order_number,
                "restaurant_name": order.restaurant_name,
                "total_amount": order.total_amount,
                "payment_method": order.payment_method,
                "delivery_address": order.delivery_address,
                "items": [item.to_dict() for item in order.order_items]
            })

        # When PREPARING — also notify delivery partners (new order available)
        if new_status == OrderStatus.PREPARING:
            await manager.broadcast_to_delivery_partners({
                "type": "new_order",
                "order_id": order.id,
                "order_number": order.order_number,
                "restaurant_name": order.restaurant_name,
                "total_amount": order.total_amount,
                "payment_method": order.payment_method,
            })
        
        return {
            "success": True,
            "message": "Order status updated successfully",
            "order": order.to_dict(),
            "refund_initiated": new_status == OrderStatus.CANCELLED and order.payment_method and order.payment_method.lower() == 'online'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating order status: {str(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update order status: {str(e)}"
        )
        
        return {
            "message": "Order status updated successfully",
            "order": order.to_dict()
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error updating order status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update order status"
        )

@router.delete("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel an order — only within 1 minute of placement and only if CONFIRMED"""
    try:
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == current_user.id
        ).first()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Only CONFIRMED orders can be cancelled by user
        if order.status not in [OrderStatus.CONFIRMED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order cannot be cancelled at this stage"
            )
        
        # Enforce 1-minute cancellation window from order creation
        if order.created_at:
            elapsed_seconds = (datetime.now() - order.created_at).total_seconds()
            if elapsed_seconds > 60:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cancellation window has expired. Orders can only be cancelled within 1 minute of placement."
                )
        
        order.status = OrderStatus.CANCELLED
        db.commit()
        db.refresh(order)
        
        # Notify restaurant via WebSocket
        await manager.send_restaurant_status_update(order.restaurant_id, {
            "type": "order_status_update",
            "order_id": order.id,
            "status": "cancelled",
            "order": order.to_dict()
        })
        
        # Notify delivery partner if one was assigned
        if order.delivery_partner_id:
            await manager.broadcast_to_delivery_partners({
                "type": "order_cancelled",
                "order_id": order.id,
                "order_number": order.order_number,
                "message": "Order was cancelled by the customer"
            })
        
        # Notify user tracking page
        await manager.send_order_update(order_id, {
            "type": "order_status_update",
            "order_id": order_id,
            "status": "cancelled",
            "order": order.to_dict()
        })
        
        return {
            "message": "Order cancelled successfully",
            "order": order.to_dict()
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error cancelling order: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel order"
        )
    
    