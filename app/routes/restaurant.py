from fastapi import APIRouter, HTTPException, status, Depends, Header, UploadFile, File
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from pathlib import Path
import uuid
import os
from app.core.database import get_db
from app.utils.email import send_restaurant_approval_email, send_restaurant_rejection_email
from app.models.restaurant_application import RestaurantApplication, ApplicationStatus
from app.models.restaurant_menu import RestaurantMenu
from app.utils.security import verify_password, get_password_hash, create_access_token
from app.utils.file_cleanup import delete_old_image, cleanup_restaurant_images
from app.utils.websocket_manager import manager

router = APIRouter()

class RestaurantApplicationRequest(BaseModel):
    businessName: str
    ownerName: str
    email: EmailStr
    password: str
    phone: str
    address: str
    cuisineType: str
    description: str
    businessLicense: str
    foodPermit: str
    
    @validator('businessName', 'ownerName', 'password', 'phone', 'address', 'description', 'businessLicense', 'foodPermit')
    def validate_required_fields(cls, v):
        if not v or not v.strip():
            raise ValueError('This field is required')
        return v.strip()
    
    @validator('password')
    def validate_password(cls, v):
        if not v or len(v.strip()) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v.strip()
    
    @validator('cuisineType')
    def validate_cuisine_type(cls, v):
        if not v or not v.strip():
            raise ValueError('Please select a cuisine type')
        return v.strip()

class RestaurantApplicationResponse(BaseModel):
    id: int
    business_name: str
    owner_name: str
    email: str
    phone: str
    address: str
    cuisine_type: str
    description: str
    business_license: str
    food_permit: str
    status: str
    created_at: str

class RestaurantLoginRequest(BaseModel):
    email: EmailStr
    password: str

class RestaurantLoginResponse(BaseModel):
    access_token: str
    token_type: str
    restaurant: dict

@router.post("/apply", response_model=RestaurantApplicationResponse)
async def submit_restaurant_application(application_data: RestaurantApplicationRequest, db: Session = Depends(get_db)):
    """Submit a new restaurant application"""
    try:
        # STRONG VALIDATION: Check if email already has ANY application (pending, approved, or rejected)
        existing_email_application = RestaurantApplication.get_by_email(db, application_data.email)
        if existing_email_application:
            if existing_email_application.status == ApplicationStatus.PENDING:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An application with this email is already pending review. Please wait for the current application to be processed."
                )
            elif existing_email_application.status == ApplicationStatus.APPROVED:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This email is already registered with an approved restaurant. Please use the login page to access your account."
                )
            elif existing_email_application.status == ApplicationStatus.REJECTED:
                # For rejected applications, allow reapplication but delete the old rejected record first
                print(f"🔄 Removing old rejected application for {application_data.email} to allow reapplication")
                db.delete(existing_email_application)
                db.commit()
        
        # Check if phone number is already used (across ALL applications, not just pending)
        existing_phone_application = RestaurantApplication.get_by_phone(db, application_data.phone)
        if existing_phone_application:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This phone number is already registered with another restaurant application. Each restaurant must have a unique phone number."
            )
        
        # Check if business license is already used (across ALL applications)
        existing_license_application = RestaurantApplication.get_by_business_license(db, application_data.businessLicense)
        if existing_license_application:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This business license number is already registered with another restaurant. Each restaurant must have a unique business license."
            )
        
        # Check if food permit is already used (across ALL applications)
        existing_permit_application = RestaurantApplication.get_by_food_permit(db, application_data.foodPermit)
        if existing_permit_application:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This food permit number is already registered with another restaurant. Each restaurant must have a unique food service permit."
            )
        
        # Create new application
        hashed_password = get_password_hash(application_data.password)
        application = RestaurantApplication.create(
            db=db,
            business_name=application_data.businessName,
            owner_name=application_data.ownerName,
            email=application_data.email,
            password=hashed_password,
            phone=application_data.phone,
            address=application_data.address,
            cuisine_type=application_data.cuisineType,
            description=application_data.description,
            business_license=application_data.businessLicense,
            food_permit=application_data.foodPermit
        )
        
        return RestaurantApplicationResponse(**application.to_dict())
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"Restaurant application error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit application. Please try again."
        )

@router.get("/applications")
async def get_all_applications(status_filter: Optional[str] = None, db: Session = Depends(get_db)):
    """Get all restaurant applications (admin only - we'll add auth later)"""
    try:
        applications = RestaurantApplication.get_all_by_status(db, status_filter)
        return [app.to_dict() for app in applications]
    except Exception as e:
        print(f"Get applications error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve applications"
        )

@router.get("/applications/{application_id}")
async def get_application_by_id(application_id: int, db: Session = Depends(get_db)):
    """Get specific restaurant application by ID"""
    try:
        application = RestaurantApplication.get_by_id(db, application_id)
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        return application.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get application error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve application"
        )

@router.put("/applications/{application_id}/status")
async def update_application_status(
    application_id: int, 
    new_status: str, 
    admin_notes: Optional[str] = None,
    reviewed_by: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Update restaurant application status (admin only)"""
    try:
        # Convert string status to integer
        valid_statuses = ['pending', 'approved', 'rejected']
        if new_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status must be 'pending', 'approved', or 'rejected'"
            )
        
        # Convert to integer
        status_int = ApplicationStatus.from_string(new_status)
        
        application = RestaurantApplication.get_by_id(db, application_id)
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        # Store original status to check if it changed
        original_status = application.status
        
        # For now, use admin ID = 1 (Latheef Dinul's ID from admins table)
        # TODO: Get actual admin ID from JWT token
        admin_id = 1  # This is your admin ID in the admins table
        
        success = application.update_status(db, status_int, admin_notes, admin_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update application status"
            )
        
        # Send email notification if status changed
        if original_status != status_int:
            try:
                if status_int == ApplicationStatus.APPROVED:
                    print(f"📧 Sending approval email to {application.email}")
                    send_restaurant_approval_email(
                        email=application.email,
                        restaurant_name=application.business_name,
                        owner_name=application.owner_name
                    )
                elif status_int == ApplicationStatus.REJECTED:
                    print(f"📧 Sending rejection email to {application.email}")
                    send_restaurant_rejection_email(
                        email=application.email,
                        restaurant_name=application.business_name,
                        owner_name=application.owner_name,
                        rejection_reason=admin_notes or ""
                    )
            except Exception as email_error:
                print(f"⚠️ Email notification failed: {email_error}")
                # Don't fail the status update if email fails
        
        return application.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update application status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update application status"
        )

@router.get("/profile")
async def get_restaurant_profile(authorization: str = Header(None), db: Session = Depends(get_db)):
    """Get restaurant profile data from approved application"""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )
        
        token = authorization.split(" ")[1]
        
        # Import JWT verification here to avoid circular imports
        from app.utils.security import verify_token
        
        # Decode and verify JWT token
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
        
        # Get restaurant application data
        restaurant_app = db.query(RestaurantApplication).filter(
            RestaurantApplication.email == restaurant_email,
            RestaurantApplication.status == 1  # Approved status
        ).first()
        
        if not restaurant_app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant profile not found or not approved"
            )
        
        # Validate session is still active
        if not restaurant_app.is_session_active(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or invalid. Please login again."
            )
        
        # Return restaurant profile data
        return {
            "id": restaurant_app.id,
            "business_name": restaurant_app.business_name,
            "owner_name": restaurant_app.owner_name,
            "email": restaurant_app.email,
            "phone": restaurant_app.phone,
            "address": restaurant_app.address,
            "cuisine_type": restaurant_app.cuisine_type,
            "description": restaurant_app.description,
            "business_license": restaurant_app.business_license,
            "food_permit": restaurant_app.food_permit,
            "restaurant_image": restaurant_app.restaurant_image,  # Add restaurant image field
            "is_online": restaurant_app.is_online,  # Add online status
            "status": "approved",
            "created_at": restaurant_app.created_at.isoformat() if restaurant_app.created_at else None,
            "approved_at": restaurant_app.reviewed_at.isoformat() if restaurant_app.reviewed_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get restaurant profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch restaurant profile"
        )

@router.put("/profile")
async def update_restaurant_profile(
    profile_data: dict,
    authorization: str = Header(None), 
    db: Session = Depends(get_db)
):
    """Update restaurant profile information"""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )
        
        token = authorization.split(" ")[1]
        
        from app.utils.security import verify_token
        
        payload = verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        restaurant_email = payload.get("sub")
        if not restaurant_email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Get restaurant application
        restaurant_app = db.query(RestaurantApplication).filter(
            RestaurantApplication.email == restaurant_email,
            RestaurantApplication.status == 1  # Approved status
        ).first()
        
        if not restaurant_app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant profile not found or not approved"
            )
        
        # Update allowed fields
        allowed_fields = ['business_name', 'owner_name', 'phone', 'address', 'cuisine_type', 'description']
        
        for field in allowed_fields:
            if field in profile_data:
                setattr(restaurant_app, field, profile_data[field])
        
        # Update timestamp
        restaurant_app.updated_at = datetime.now()
        db.commit()
        db.refresh(restaurant_app)
        
        # Broadcast restaurant profile update via WebSocket
        await manager.broadcast_restaurant_update(restaurant_app.id, {
            "type": "restaurant_profile_updated",
            "restaurant_id": restaurant_app.id,
            "restaurant": {
                "id": restaurant_app.id,
                "name": restaurant_app.business_name,
                "cuisine": restaurant_app.cuisine_type,
                "description": restaurant_app.description,
                "address": restaurant_app.address,
                "phone": restaurant_app.phone
            }
        })
        
        return {
            "message": "Restaurant profile updated successfully",
            "profile": {
                "id": restaurant_app.id,
                "business_name": restaurant_app.business_name,
                "owner_name": restaurant_app.owner_name,
                "email": restaurant_app.email,
                "phone": restaurant_app.phone,
                "address": restaurant_app.address,
                "cuisine_type": restaurant_app.cuisine_type,
                "description": restaurant_app.description,
                "updated_at": restaurant_app.updated_at.isoformat() if restaurant_app.updated_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update restaurant profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update restaurant profile"
        )

@router.post("/logout")
async def restaurant_logout(authorization: str = Header(None), db: Session = Depends(get_db)):
    """Restaurant logout - clear active session"""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )
        
        token = authorization.split(" ")[1]
        
        from app.utils.security import verify_token
        
        payload = verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
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
        
        if restaurant_app:
            # Clear the active session
            restaurant_app.clear_session(db)
        
        return {"message": "Logged out successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Restaurant logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.get("/debug/session-status")
async def debug_session_status(authorization: str = Header(None), db: Session = Depends(get_db)):
    """Debug endpoint to check session status"""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return {"error": "No authorization header"}
        
        token = authorization.split(" ")[1]
        
        from app.utils.security import verify_token
        
        payload = verify_token(token)
        if not payload:
            return {"error": "Invalid token"}
        
        restaurant_email = payload.get("sub")
        if not restaurant_email:
            return {"error": "No email in token"}
        
        # Get restaurant application
        restaurant_app = db.query(RestaurantApplication).filter(
            RestaurantApplication.email == restaurant_email,
            RestaurantApplication.status == ApplicationStatus.APPROVED
        ).first()
        
        if not restaurant_app:
            return {"error": "Restaurant not found"}
        
        current_time = datetime.now()
        
        return {
            "restaurant_email": restaurant_email,
            "has_active_session_token": bool(restaurant_app.active_session_token),
            "session_expires_at": restaurant_app.session_expires_at.isoformat() if restaurant_app.session_expires_at else None,
            "current_time": current_time.isoformat(),
            "session_expired": restaurant_app.session_expires_at <= current_time if restaurant_app.session_expires_at else True,
            "has_active_session": restaurant_app.has_active_session(),
            "is_session_active": restaurant_app.is_session_active(token)
        }
        
    except Exception as e:
        return {"error": str(e)}

@router.post("/login", response_model=RestaurantLoginResponse)
async def restaurant_login(login_data: RestaurantLoginRequest, db: Session = Depends(get_db)):
    """Restaurant login endpoint"""
    try:
        # Find restaurant application by email
        application = RestaurantApplication.get_by_email(db, login_data.email)
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check password
        if not verify_password(login_data.password, application.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check application status
        if application.status == ApplicationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your application is under review. You'll be notified once approved."
            )
        elif application.status == ApplicationStatus.REJECTED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your application was not approved. You can submit a new application."
            )
        elif application.status != ApplicationStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account access denied. Please contact support."
            )
        
        # Check if restaurant already has an active session
        # First, clear any expired sessions
        application.force_clear_expired_sessions(db)
        
        # Also clear any sessions that are older than 8 hours (safety cleanup)
        current_time = datetime.now()
        cleanup_time = current_time - timedelta(hours=8)
        
        # Clear old sessions for all restaurants (cleanup)
        db.execute(text("""
            UPDATE restaurant_applications 
            SET active_session_token = NULL, session_expires_at = NULL 
            WHERE session_expires_at < :cleanup_time OR (session_expires_at IS NULL AND active_session_token IS NOT NULL)
        """), {"cleanup_time": cleanup_time})
        db.commit()
        
        # Refresh the application object after cleanup
        db.refresh(application)
        
        # Check if restaurant already has an active session
        if application.has_active_session():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already user is using, wait until logout"
            )
        
        # Create access token with 8-hour expiry
        expires_delta = timedelta(hours=8)
        access_token = create_access_token(
            data={"sub": application.email, "type": "restaurant", "restaurant_id": application.id},
            expires_delta=expires_delta
        )
        
        # Calculate session expiry time
        session_expires_at = datetime.now() + expires_delta
        
        # Set active session in database
        application.set_active_session(db, access_token, session_expires_at)
        
        # Return login response
        return RestaurantLoginResponse(
            access_token=access_token,
            token_type="bearer",
            restaurant={
                "id": application.id,
                "business_name": application.business_name,
                "owner_name": application.owner_name,
                "email": application.email,
                "phone": application.phone,
                "address": application.address,
                "cuisine_type": application.cuisine_type,
                "description": application.description,
                "status": application.status
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Restaurant login error: {e}")
        print(f"Login attempt for email: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )

@router.get("/check-phone/{phone}")
async def check_phone_availability(phone: str, db: Session = Depends(get_db)):
    """Check if phone number is already used"""
    try:
        existing_application = RestaurantApplication.get_by_phone(db, phone)
        return {
            "available": existing_application is None,
            "message": "Phone number is available" if existing_application is None else "This phone number is already registered with another restaurant"
        }
    except Exception as e:
        print(f"Phone check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check phone availability"
        )

@router.get("/check-license/{license_number}")
async def check_license_availability(license_number: str, db: Session = Depends(get_db)):
    """Check if business license number is already used"""
    try:
        existing_application = RestaurantApplication.get_by_business_license(db, license_number)
        return {
            "available": existing_application is None,
            "message": "Business license is available" if existing_application is None else "This business license number is already registered with another restaurant"
        }
    except Exception as e:
        print(f"License check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check license availability"
        )

@router.get("/public/restaurants")
async def get_public_restaurants(db: Session = Depends(get_db)):
    """Get all approved restaurants with images for customer-facing pages"""
    try:
        # Get all approved restaurants that have uploaded restaurant images
        approved_restaurants = db.query(RestaurantApplication).filter(
            RestaurantApplication.status == ApplicationStatus.APPROVED,
            RestaurantApplication.restaurant_image.isnot(None),
            RestaurantApplication.restaurant_image != ""
        ).all()
        
        restaurants_data = []
        for restaurant in approved_restaurants:
            # Get menu items count for this restaurant
            menu_count = db.query(RestaurantMenu).filter(
                RestaurantMenu.restaurant_id == restaurant.id,
                RestaurantMenu.is_available == True
            ).count()
            
            # Calculate average price from menu items
            avg_price_result = db.query(func.avg(RestaurantMenu.price)).filter(
                RestaurantMenu.restaurant_id == restaurant.id,
                RestaurantMenu.is_available == True
            ).scalar()
            avg_price = round(avg_price_result, 2) if avg_price_result else 0
            
            restaurant_data = {
                "id": restaurant.id,
                "name": restaurant.business_name,
                "owner_name": restaurant.owner_name,
                "cuisine": restaurant.cuisine_type,
                "description": restaurant.description,
                "address": restaurant.address,
                "phone": restaurant.phone,
                "email": restaurant.email,
                "restaurant_image": restaurant.restaurant_image,  # Include restaurant image
                "is_online": restaurant.is_online,  # Restaurant online/offline status
                "menu_items_count": menu_count,
                "average_price": avg_price,
                "created_at": restaurant.created_at.isoformat() if restaurant.created_at else None,
                # Mock data for now - can be enhanced later
                "rating": round(4.0 + (restaurant.id % 10) * 0.1, 1),  # 4.0-4.9 rating
                "delivery_time": f"{20 + (restaurant.id % 20)}-{30 + (restaurant.id % 20)} min",
                "delivery_fee": round(2.0 + (restaurant.id % 5) * 0.5, 1),  # $2.0-$4.5
                "reviews": 50 + (restaurant.id % 200),  # 50-250 reviews
                "image": "🍽️",  # Default emoji, can be enhanced with real images
                "tags": [restaurant.cuisine_type, "Popular", "Fast Delivery"],
                "category": restaurant.cuisine_type
            }
            restaurants_data.append(restaurant_data)
        
        return {
            "restaurants": restaurants_data,
            "total_count": len(restaurants_data)
        }
        
    except Exception as e:
        print(f"Get public restaurants error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch restaurants"
        )

@router.get("/public/restaurants/{restaurant_id}")
async def get_public_restaurant_details(restaurant_id: int, db: Session = Depends(get_db)):
    """Get specific restaurant details with menu for customer-facing pages"""
    try:
        # Get restaurant details
        restaurant = db.query(RestaurantApplication).filter(
            RestaurantApplication.id == restaurant_id,
            RestaurantApplication.status == ApplicationStatus.APPROVED
        ).first()
        
        if not restaurant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found or not available"
            )
        
        # Get restaurant's menu items (show ALL items, including unavailable ones)
        menu_items = db.query(RestaurantMenu).filter(
            RestaurantMenu.restaurant_id == restaurant_id
        ).order_by(RestaurantMenu.category, RestaurantMenu.item_name).all()
        
        # Group menu items by category
        menu_by_category = {}
        for item in menu_items:
            if item.category not in menu_by_category:
                menu_by_category[item.category] = []
            menu_by_category[item.category].append({
                "id": item.id,
                "name": item.item_name,
                "description": item.description,
                "price": item.price,
                "image_url": item.image_url,
                "category": item.category,
                "is_available": item.is_available,  # Add availability status
                "isVeg": item.is_veg  # Add veg/non-veg status
            })
        
        # Calculate restaurant stats
        total_items = len(menu_items)
        avg_price = round(sum(item.price for item in menu_items) / total_items, 2) if total_items > 0 else 0
        
        restaurant_details = {
            "id": restaurant.id,
            "name": restaurant.business_name,
            "owner_name": restaurant.owner_name,
            "cuisine": restaurant.cuisine_type,
            "description": restaurant.description,
            "address": restaurant.address,
            "phone": restaurant.phone,
            "menu_by_category": menu_by_category,
            "total_menu_items": total_items,
            "average_price": avg_price,
            # Mock data for now
            "rating": round(4.0 + (restaurant.id % 10) * 0.1, 1),
            "delivery_time": f"{20 + (restaurant.id % 20)}-{30 + (restaurant.id % 20)} min",
            "delivery_fee": round(2.0 + (restaurant.id % 5) * 0.5, 1),
            "reviews": 50 + (restaurant.id % 200),
            "image": "🍽️",
            "tags": [restaurant.cuisine_type, "Popular", "Fast Delivery"],
            "hours": "9:00 AM - 11:00 PM",
            "is_open": True
        }
        
        return restaurant_details
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get restaurant details error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch restaurant details"
        )

@router.get("/public/categories")
async def get_restaurant_categories(db: Session = Depends(get_db)):
    """Get all available restaurant categories for customer-facing pages"""
    try:
        # Get unique cuisine types from approved restaurants
        categories_result = db.query(RestaurantApplication.cuisine_type).filter(
            RestaurantApplication.status == ApplicationStatus.APPROVED
        ).distinct().all()
        
        categories = []
        category_emojis = {
            "Indian": "🍛",
            "Chinese": "🥢", 
            "Italian": "🍝",
            "Japanese": "🍣",
            "Thai": "🍜",
            "Mexican": "🌮",
            "American": "🍔",
            "Mediterranean": "🥙",
            "Korean": "🍲",
            "Vietnamese": "🍲"
        }
        
        for category_tuple in categories_result:
            cuisine_type = category_tuple[0]
            categories.append({
                "id": cuisine_type.lower().replace(" ", "_"),
                "name": cuisine_type,
                "emoji": category_emojis.get(cuisine_type, "🍽️")
            })
        
        return {
            "categories": categories
        }
        
    except Exception as e:
        print(f"Get categories error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch categories"
        )

@router.post("/admin/clear-sessions")
async def admin_clear_all_sessions(db: Session = Depends(get_db)):
    """Admin endpoint to clear all active sessions (for debugging)"""
    try:
        # Clear all active sessions
        result = db.execute(text("UPDATE restaurant_applications SET active_session_token = NULL, session_expires_at = NULL WHERE active_session_token IS NOT NULL"))
        db.commit()
        
        return {
            "message": f"Cleared {result.rowcount} active sessions",
            "cleared_count": result.rowcount
        }
    except Exception as e:
        print(f"Clear sessions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear sessions"
        )

@router.get("/admin/session-status")
async def get_session_status(db: Session = Depends(get_db)):
    """Admin endpoint to check current session status"""
    try:
        # Get all active sessions
        result = db.execute(text("SELECT email, business_name, active_session_token IS NOT NULL as has_token, session_expires_at FROM restaurant_applications WHERE status = 1"))
        sessions = result.fetchall()
        
        return {
            "total_approved_restaurants": len(sessions),
            "restaurants": [
                {
                    "email": session[0],
                    "business_name": session[1],
                    "has_active_session": bool(session[2]),
                    "session_expires_at": session[3].isoformat() if session[3] else None
                }
                for session in sessions
            ]
        }
    except Exception as e:
        print(f"Session status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session status"
        )

@router.get("/admin/integrity-check")
async def check_database_integrity(db: Session = Depends(get_db)):
    """Admin endpoint to check for duplicate records and data integrity"""
    try:
        integrity_report = {
            "duplicate_emails": [],
            "duplicate_phones": [],
            "duplicate_licenses": [],
            "duplicate_permits": [],
            "total_applications": 0,
            "status_breakdown": {"pending": 0, "approved": 0, "rejected": 0}
        }
        
        # Check for duplicate emails
        result = db.execute(text("""
            SELECT email, COUNT(*) as count, GROUP_CONCAT(id) as ids
            FROM restaurant_applications 
            GROUP BY email 
            HAVING COUNT(*) > 1
        """))
        email_dupes = result.fetchall()
        integrity_report["duplicate_emails"] = [
            {"email": dupe[0], "count": dupe[1], "ids": dupe[2]}
            for dupe in email_dupes
        ]
        
        # Check for duplicate phones
        result = db.execute(text("""
            SELECT phone, COUNT(*) as count, GROUP_CONCAT(email) as emails
            FROM restaurant_applications 
            GROUP BY phone 
            HAVING COUNT(*) > 1
        """))
        phone_dupes = result.fetchall()
        integrity_report["duplicate_phones"] = [
            {"phone": dupe[0], "count": dupe[1], "emails": dupe[2]}
            for dupe in phone_dupes
        ]
        
        # Check for duplicate business licenses
        result = db.execute(text("""
            SELECT business_license, COUNT(*) as count, GROUP_CONCAT(email) as emails
            FROM restaurant_applications 
            GROUP BY business_license 
            HAVING COUNT(*) > 1
        """))
        license_dupes = result.fetchall()
        integrity_report["duplicate_licenses"] = [
            {"license": dupe[0], "count": dupe[1], "emails": dupe[2]}
            for dupe in license_dupes
        ]
        
        # Check for duplicate food permits
        result = db.execute(text("""
            SELECT food_permit, COUNT(*) as count, GROUP_CONCAT(email) as emails
            FROM restaurant_applications 
            GROUP BY food_permit 
            HAVING COUNT(*) > 1
        """))
        permit_dupes = result.fetchall()
        integrity_report["duplicate_permits"] = [
            {"permit": dupe[0], "count": dupe[1], "emails": dupe[2]}
            for dupe in permit_dupes
        ]
        
        # Get total applications and status breakdown
        result = db.execute(text("SELECT COUNT(*) FROM restaurant_applications"))
        integrity_report["total_applications"] = result.fetchone()[0]
        
        result = db.execute(text("""
            SELECT status, COUNT(*) as count 
            FROM restaurant_applications 
            GROUP BY status
        """))
        status_counts = result.fetchall()
        for status_count in status_counts:
            status_name = {0: "pending", 1: "approved", 2: "rejected"}.get(status_count[0], "unknown")
            integrity_report["status_breakdown"][status_name] = status_count[1]
        
        # Calculate integrity score
        total_duplicates = (len(integrity_report["duplicate_emails"]) + 
                          len(integrity_report["duplicate_phones"]) + 
                          len(integrity_report["duplicate_licenses"]) + 
                          len(integrity_report["duplicate_permits"]))
        
        integrity_report["integrity_score"] = "EXCELLENT" if total_duplicates == 0 else "NEEDS_ATTENTION"
        integrity_report["issues_found"] = total_duplicates
        
        return integrity_report
        
    except Exception as e:
        print(f"Integrity check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform integrity check"
        )

@router.post("/upload-restaurant-image")
async def upload_restaurant_image(
    file: UploadFile = File(...),
    authorization: str = Header(None), 
    db: Session = Depends(get_db)
):
    """Upload restaurant banner/logo image"""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )
        
        token = authorization.split(" ")[1]
        
        from app.utils.security import verify_token
        
        payload = verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
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
        
        # Delete old image if exists
        if restaurant_app.restaurant_image:
            delete_old_image(restaurant_app.restaurant_image, "restaurant")
        
        # Also cleanup any old restaurant images for this restaurant (keep only latest)
        cleanup_restaurant_images(restaurant_app.id, keep_latest=0)
        
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only JPEG, PNG, and WebP images are allowed"
            )
        
        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024  # 5MB
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size must be less than 5MB"
            )
        
        # Create uploads directory if it doesn't exist
        upload_dir = Path("uploads/restaurant_images")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        unique_filename = f"restaurant_{restaurant_app.id}_{uuid.uuid4().hex}.{file_extension}"
        file_path = upload_dir / unique_filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # Update restaurant record with image URL
        image_url = f"/uploads/restaurant_images/{unique_filename}"
        restaurant_app.restaurant_image = image_url
        restaurant_app.updated_at = datetime.now()
        db.commit()
        
        return {
            "message": "Restaurant image uploaded successfully",
            "image_url": image_url,
            "filename": unique_filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Upload restaurant image error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload restaurant image"
        )



@router.put("/toggle-online-status")
async def toggle_restaurant_online_status(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Toggle restaurant online/offline status"""
    try:
        # Verify authorization token
        if not authorization or not authorization.startswith('Bearer '):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization token"
            )
        
        token = authorization.split(' ')[1]
        
        # Get restaurant from token
        from app.utils.security import verify_token
        payload = verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        restaurant_email = payload.get("sub")
        if not restaurant_email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Get restaurant application
        restaurant_app = RestaurantApplication.get_by_email(db, restaurant_email)
        if not restaurant_app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found"
            )
        
        if restaurant_app.status != ApplicationStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only approved restaurants can toggle online status"
            )
        
        # Toggle the online status
        restaurant_app.is_online = not restaurant_app.is_online
        restaurant_app.updated_at = datetime.now()
        db.commit()
        db.refresh(restaurant_app)
        
        # Broadcast restaurant status update via WebSocket
        await manager.broadcast_restaurant_update(restaurant_app.id, {
            "type": "restaurant_status_update",
            "restaurant_id": restaurant_app.id,
            "is_online": restaurant_app.is_online,
            "restaurant_name": restaurant_app.business_name
        })
        
        return {
            "success": True,
            "message": f"Restaurant is now {'online' if restaurant_app.is_online else 'offline'}",
            "is_online": restaurant_app.is_online
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle online status: {str(e)}"
        )
