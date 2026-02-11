"""
Cart API endpoints for database-driven cart system
Production-ready cart management with user isolation
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel
from app.core.database import get_db
from app.models.user import User
from app.models.user_cart import UserCart
from app.models.restaurant_menu import RestaurantMenu
from app.models.restaurant_application import RestaurantApplication
from app.utils.security import get_current_user

router = APIRouter()

@router.get("/", response_model=List[Dict[str, Any]])
async def get_user_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all cart items for the current user"""
    try:
        cart_items = db.query(UserCart).filter(UserCart.user_id == current_user.id).all()
        return [item.to_dict() for item in cart_items]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch cart items"
        )

class AddToCartRequest(BaseModel):
    menu_item_id: int
    quantity: int = 1

class UpdateCartRequest(BaseModel):
    quantity: int

@router.post("/add")
async def add_to_cart(
    request: AddToCartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add item to user's cart"""
    try:
        # Get menu item details
        menu_item = db.query(RestaurantMenu).filter(RestaurantMenu.id == request.menu_item_id).first()
        if not menu_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found"
            )
        
        # Get restaurant details
        restaurant = db.query(RestaurantApplication).filter(
            RestaurantApplication.id == menu_item.restaurant_id
        ).first()
        if not restaurant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found"
            )
        
        # Check if item already exists in cart
        print(f"🔍 Checking for existing cart item: user_id={current_user.id}, menu_item_id={request.menu_item_id}")
        existing_cart_item = db.query(UserCart).filter(
            UserCart.user_id == current_user.id,
            UserCart.menu_item_id == request.menu_item_id
        ).first()
        
        if existing_cart_item:
            # Update quantity
            print(f"✅ Found existing item, updating quantity: {existing_cart_item.quantity} + {request.quantity}")
            existing_cart_item.quantity += request.quantity
            db.commit()
            db.refresh(existing_cart_item)
            return {
                "message": "Cart updated successfully",
                "cart_item": existing_cart_item.to_dict()
            }
        else:
            # Create new cart item
            print(f"✅ Creating new cart item: {menu_item.item_name} (menu_item_id: {request.menu_item_id})")
            cart_item = UserCart(
                user_id=current_user.id,
                restaurant_id=menu_item.restaurant_id,
                menu_item_id=request.menu_item_id,
                item_name=menu_item.item_name,
                item_description=menu_item.description,
                item_price=menu_item.price,
                item_image_url=menu_item.image_url,
                item_category=menu_item.category,
                is_veg=menu_item.is_veg,  # Use actual value from menu item
                quantity=request.quantity,
                restaurant_name=restaurant.business_name
            )
            
            db.add(cart_item)
            db.commit()
            db.refresh(cart_item)
            
            print(f"✅ Cart item created with cart_id: {cart_item.id}, menu_item_id: {cart_item.menu_item_id}")
            return {
                "message": "Item added to cart successfully",
                "cart_item": cart_item.to_dict()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add item to cart"
        )

@router.put("/update/{cart_id}")
async def update_cart_quantity(
    cart_id: int,
    request: UpdateCartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update quantity of a cart item"""
    try:
        cart_item = db.query(UserCart).filter(
            UserCart.id == cart_id,
            UserCart.user_id == current_user.id
        ).first()
        
        if not cart_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart item not found"
            )
        
        if request.quantity <= 0:
            # Remove item if quantity is 0 or negative
            db.delete(cart_item)
            db.commit()
            return {"message": "Item removed from cart"}
        else:
            cart_item.quantity = request.quantity
            db.commit()
            db.refresh(cart_item)
            return {
                "message": "Cart updated successfully",
                "cart_item": cart_item.to_dict()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update cart item"
        )

@router.delete("/remove/{cart_id}")
async def remove_from_cart(
    cart_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove item from user's cart"""
    try:
        cart_item = db.query(UserCart).filter(
            UserCart.id == cart_id,
            UserCart.user_id == current_user.id
        ).first()
        
        if not cart_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart item not found"
            )
        
        db.delete(cart_item)
        db.commit()
        
        return {"message": "Item removed from cart successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove item from cart"
        )

@router.delete("/clear")
async def clear_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clear all items from user's cart"""
    try:
        db.query(UserCart).filter(UserCart.user_id == current_user.id).delete()
        db.commit()
        
        return {"message": "Cart cleared successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cart"
        )

@router.get("/restaurant/{restaurant_id}")
async def get_cart_by_restaurant(
    restaurant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get cart items for a specific restaurant"""
    try:
        cart_items = db.query(UserCart).filter(
            UserCart.user_id == current_user.id,
            UserCart.restaurant_id == restaurant_id
        ).all()
        
        return [item.to_dict() for item in cart_items]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch restaurant cart items"
        )

@router.get("/summary")
async def get_cart_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get cart summary with totals"""
    try:
        cart_items = db.query(UserCart).filter(UserCart.user_id == current_user.id).all()
        
        total_items = sum(item.quantity for item in cart_items)
        total_price = sum(item.total_price for item in cart_items)
        
        # Group by restaurant
        restaurants = {}
        for item in cart_items:
            if item.restaurant_id not in restaurants:
                restaurants[item.restaurant_id] = {
                    "restaurant_name": item.restaurant_name,
                    "items": [],
                    "total_price": 0
                }
            restaurants[item.restaurant_id]["items"].append(item.to_dict())
            restaurants[item.restaurant_id]["total_price"] += item.total_price
        
        return {
            "total_items": total_items,
            "total_price": total_price,
            "restaurants": list(restaurants.values()),
            "cart_items": [item.to_dict() for item in cart_items]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch cart summary"
        )