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
            delivery_fee = 2.99
            tax_amount = subtotal * 0.08
            total_amount = subtotal + delivery_fee + tax_amount
            
            # Generate order number
            order_count = db.query(Order).count()
            order_number = f"ORD-{datetime.now().year}-{order_count + 1:06d}"
            
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
                discount_amount=0.0,
                total_amount=total_amount,
                delivery_address=delivery_address_text,
                delivery_phone=addr.phone,
                delivery_instructions=request.special_instructions,
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
        orders = db.query(Order).filter(
            Order.restaurant_id == restaurant_id
        ).order_by(Order.created_at.desc()).all()
        
        return [order.to_dict() for order in orders]
        
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
        
        order.status = new_status
        
        # Update delivered_at if status is delivered
        if new_status == OrderStatus.DELIVERED:
            order.delivered_at = datetime.now()
        
        db.commit()
        db.refresh(order)
        
        # Broadcast update via WebSocket
        await manager.send_order_update(order_id, {
            "type": "order_status_update",
            "order_id": order_id,
            "status": new_status.value,
            "order": order.to_dict()
        })
        
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
    """Cancel an order (only if not yet preparing)"""
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
        
        # Check if order can be cancelled
        if order.status not in [OrderStatus.PENDING, OrderStatus.CONFIRMED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order cannot be cancelled at this stage"
            )
        
        order.status = OrderStatus.CANCELLED
        db.commit()
        db.refresh(order)
        
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
    
    