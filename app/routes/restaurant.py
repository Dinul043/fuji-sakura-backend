from fastapi import APIRouter, HTTPException, status, Depends, Header
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.utils.email import send_restaurant_approval_email, send_restaurant_rejection_email
from app.models.restaurant_application import RestaurantApplication, ApplicationStatus
from app.utils.security import verify_password, get_password_hash, create_access_token

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
        # Check if email already has a pending application
        existing_email_application = RestaurantApplication.get_by_email(db, application_data.email)
        if existing_email_application and existing_email_application.status == ApplicationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An application with this email is already pending review. Please wait for the current application to be processed."
            )
        
        # Check if phone number is already used
        existing_phone_application = RestaurantApplication.get_by_phone(db, application_data.phone)
        if existing_phone_application:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This phone number is already registered with another restaurant application. Each restaurant must have a unique phone number."
            )
        
        # Check if business license is already used
        existing_license_application = RestaurantApplication.get_by_business_license(db, application_data.businessLicense)
        if existing_license_application:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This business license number is already registered with another restaurant. Each restaurant must have a unique business license."
            )
        
        # Check if food permit is already used
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
        restaurant_app.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        
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
        if application.has_active_session():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Restaurant account is already logged in elsewhere. Please logout from the other device first or wait for the session to expire."
            )
        
        # Create access token with 8-hour expiry
        expires_delta = timedelta(hours=8)
        access_token = create_access_token(
            data={"sub": application.email, "type": "restaurant", "restaurant_id": application.id},
            expires_delta=expires_delta
        )
        
        # Calculate session expiry time
        session_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + expires_delta
        
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

@router.get("/check-permit/{permit_number}")
async def check_permit_availability(permit_number: str, db: Session = Depends(get_db)):
    """Check if food permit number is already used"""
    try:
        existing_application = RestaurantApplication.get_by_food_permit(db, permit_number)
        return {
            "available": existing_application is None,
            "message": "Food permit is available" if existing_application is None else "This food permit number is already registered with another restaurant"
        }
    except Exception as e:
        print(f"Permit check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check permit availability"
        )


