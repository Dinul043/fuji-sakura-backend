from fastapi import APIRouter, HTTPException, status, Depends, Header, UploadFile, File
from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.restaurant_menu import RestaurantMenu, MenuCategory
from app.models.restaurant_application import RestaurantApplication, ApplicationStatus
from app.utils.security import verify_token
import os
import uuid
from pathlib import Path

router = APIRouter()

class MenuItemRequest(BaseModel):
    item_name: str
    description: Optional[str] = None
    price: float
    category: str
    image_url: Optional[str] = None
    is_veg: bool = True  # Veg/Non-Veg classification

    @validator('item_name')
    def validate_item_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Item name is required')
        if len(v.strip()) < 2:
            raise ValueError('Item name must be at least 2 characters')
        if len(v.strip()) > 255:
            raise ValueError('Item name must be less than 255 characters')
        return v.strip()

    @validator('price')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('Price must be greater than 0')
        if v > 99999:
            raise ValueError('Price must be less than 99999')
        return round(v, 2)

    @validator('category')
    def validate_category(cls, v):
        if not v or not v.strip():
            raise ValueError('Category is required')
        if not MenuCategory.is_valid_category(v.strip()):
            raise ValueError(f'Invalid category. Must be one of: {", ".join(MenuCategory.get_all_categories())}')
        return v.strip()

class MenuItemResponse(BaseModel):
    id: int
    restaurant_id: int
    item_name: str
    description: Optional[str]
    price: float
    category: str
    image_url: Optional[str]
    is_available: bool
    isVeg: bool  # Veg/Non-Veg classification (camelCase for frontend)
    created_at: str
    updated_at: str

def get_authenticated_restaurant(authorization: str, db: Session) -> RestaurantApplication:
    """Get authenticated restaurant from token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.split(" ")[1]
    
    # Verify JWT token
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Extract restaurant email from token
    restaurant_email = payload.get("sub")
    if not restaurant_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Get restaurant application
    restaurant_app = db.query(RestaurantApplication).filter(
        RestaurantApplication.email == restaurant_email,
        RestaurantApplication.status == ApplicationStatus.APPROVED
    ).first()
    
    if not restaurant_app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found or not approved"
        )
    
    # Validate session is still active
    if not restaurant_app.is_session_active(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please login again."
        )
    
    return restaurant_app

@router.get("/categories")
async def get_menu_categories():
    """Get all available menu categories"""
    return {
        "categories": MenuCategory.get_all_categories()
    }

@router.get("/", response_model=List[MenuItemResponse])
async def get_restaurant_menu(
    available_only: bool = False,
    category: Optional[str] = None,
    authorization: str = Header(None), 
    db: Session = Depends(get_db)
):
    """Get all menu items for authenticated restaurant"""
    try:
        restaurant = get_authenticated_restaurant(authorization, db)
        
        if category:
            if not MenuCategory.is_valid_category(category):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid category. Must be one of: {', '.join(MenuCategory.get_all_categories())}"
                )
            menu_items = RestaurantMenu.get_by_category(db, restaurant.id, category, available_only)
        else:
            menu_items = RestaurantMenu.get_restaurant_menu(db, restaurant.id, available_only)
        
        return [MenuItemResponse(**item.to_dict()) for item in menu_items]
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get menu error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch menu items"
        )

@router.post("/", response_model=MenuItemResponse)
async def create_menu_item(
    menu_item: MenuItemRequest,
    authorization: str = Header(None), 
    db: Session = Depends(get_db)
):
    """Create a new menu item"""
    try:
        restaurant = get_authenticated_restaurant(authorization, db)
        
        # Create menu item
        new_item = RestaurantMenu.create_menu_item(
            db=db,
            restaurant_id=restaurant.id,
            item_name=menu_item.item_name,
            description=menu_item.description,
            price=menu_item.price,
            category=menu_item.category,
            image_url=menu_item.image_url,
            is_veg=menu_item.is_veg
        )
        
        return MenuItemResponse(**new_item.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Create menu item error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create menu item"
        )

@router.get("/{item_id}", response_model=MenuItemResponse)
async def get_menu_item(
    item_id: int,
    authorization: str = Header(None), 
    db: Session = Depends(get_db)
):
    """Get a specific menu item"""
    try:
        restaurant = get_authenticated_restaurant(authorization, db)
        
        menu_item = RestaurantMenu.get_by_id(db, item_id)
        if not menu_item or menu_item.restaurant_id != restaurant.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found"
            )
        
        return MenuItemResponse(**menu_item.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get menu item error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch menu item"
        )

@router.put("/{item_id}", response_model=MenuItemResponse)
async def update_menu_item(
    item_id: int,
    menu_item: MenuItemRequest,
    authorization: str = Header(None), 
    db: Session = Depends(get_db)
):
    """Update a menu item"""
    try:
        restaurant = get_authenticated_restaurant(authorization, db)
        
        existing_item = RestaurantMenu.get_by_id(db, item_id)
        if not existing_item or existing_item.restaurant_id != restaurant.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found"
            )
        
        print(f"🔄 Updating menu item {item_id}")
        print(f"   Current is_veg: {existing_item.is_veg}")
        print(f"   New is_veg: {menu_item.is_veg}")
        
        # Update the item
        existing_item.update_item(
            db=db,
            item_name=menu_item.item_name,
            description=menu_item.description,
            price=menu_item.price,
            category=menu_item.category,
            image_url=menu_item.image_url,
            is_veg=menu_item.is_veg
        )
        
        print(f"   Updated is_veg: {existing_item.is_veg}")
        
        return MenuItemResponse(**existing_item.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update menu item error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update menu item"
        )

@router.put("/{item_id}/toggle")
async def toggle_menu_item_availability(
    item_id: int,
    authorization: str = Header(None), 
    db: Session = Depends(get_db)
):
    """Toggle menu item availability"""
    try:
        restaurant = get_authenticated_restaurant(authorization, db)
        
        menu_item = RestaurantMenu.get_by_id(db, item_id)
        if not menu_item or menu_item.restaurant_id != restaurant.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found"
            )
        
        new_availability = menu_item.toggle_availability(db)
        
        return {
            "message": f"Menu item {'enabled' if new_availability else 'disabled'} successfully",
            "item_id": item_id,
            "is_available": new_availability
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Toggle menu item error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle menu item availability"
        )

@router.delete("/{item_id}")
async def delete_menu_item(
    item_id: int,
    authorization: str = Header(None), 
    db: Session = Depends(get_db)
):
    """Delete a menu item"""
    try:
        restaurant = get_authenticated_restaurant(authorization, db)
        
        menu_item = RestaurantMenu.get_by_id(db, item_id)
        if not menu_item or menu_item.restaurant_id != restaurant.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found"
            )
        
        item_name = menu_item.item_name
        menu_item.delete_item(db)
        
        return {
            "message": f"Menu item '{item_name}' deleted successfully",
            "item_id": item_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete menu item error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete menu item"
        )

@router.get("/search/{search_term}")
async def search_menu_items(
    search_term: str,
    authorization: str = Header(None), 
    db: Session = Depends(get_db)
):
    """Search menu items by name or description"""
    try:
        restaurant = get_authenticated_restaurant(authorization, db)
        
        if len(search_term.strip()) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search term must be at least 2 characters"
            )
        
        menu_items = RestaurantMenu.search_items(db, restaurant.id, search_term.strip())
        
        return {
            "search_term": search_term,
            "results": [MenuItemResponse(**item.to_dict()) for item in menu_items],
            "count": len(menu_items)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Search menu items error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search menu items"
        )

# Image upload endpoint (basic implementation)
@router.post("/upload-image")
async def upload_menu_image(
    file: UploadFile = File(...),
    authorization: str = Header(None), 
    db: Session = Depends(get_db)
):
    """Upload menu item image"""
    try:
        restaurant = get_authenticated_restaurant(authorization, db)
        
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only JPEG, PNG, and WebP images are allowed."
            )
        
        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024  # 5MB
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size too large. Maximum size is 5MB."
            )
        
        # Generate unique filename
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        unique_filename = f"menu_{restaurant.id}_{uuid.uuid4().hex}.{file_extension}"
        
        # Create uploads directory if it doesn't exist
        upload_dir = Path("uploads/menu_images")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = upload_dir / unique_filename
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # Return the file URL (accessible via the static file mount)
        image_url = f"http://localhost:8000/uploads/menu_images/{unique_filename}"
        
        return {
            "message": "Image uploaded successfully",
            "image_url": image_url,
            "filename": unique_filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Upload image error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image"
        )