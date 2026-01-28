from fastapi import APIRouter, HTTPException, status, Depends, Header
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.restaurant_application import RestaurantApplication
from app.utils.security import verify_password, get_password_hash, create_access_token

router = APIRouter()

class RestaurantApplicationRequest(BaseModel):
    businessName: str
    ownerName: str
    email: EmailStr
    phone: str
    address: str
    cuisineType: str
    description: str
    businessLicense: str
    foodPermit: str
    
    @validator('businessName', 'ownerName', 'phone', 'address', 'description', 'businessLicense', 'foodPermit')
    def validate_required_fields(cls, v):
        if not v or not v.strip():
            raise ValueError('This field is required')
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

@router.post("/apply", response_model=RestaurantApplicationResponse)
async def submit_restaurant_application(application_data: RestaurantApplicationRequest, db: Session = Depends(get_db)):
    """Submit a new restaurant application"""
    try:
        # Check if email already has a pending application
        existing_application = RestaurantApplication.get_by_email(db, application_data.email)
        if existing_application and existing_application.status == 'pending':
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An application with this email is already pending review. Please wait for the current application to be processed."
            )
        
        # Create new application
        application = RestaurantApplication.create(
            db=db,
            business_name=application_data.businessName,
            owner_name=application_data.ownerName,
            email=application_data.email,
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
        if new_status not in ['pending', 'approved', 'rejected']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status must be 'pending', 'approved', or 'rejected'"
            )
        
        application = RestaurantApplication.get_by_id(db, application_id)
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        # For now, use admin ID = 1 (Latheef Dinul's ID from admins table)
        # TODO: Get actual admin ID from JWT token
        admin_id = 1  # This is your admin ID in the admins table
        
        success = application.update_status(db, new_status, admin_notes, admin_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update application status"
            )
        
        return application.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update application status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update application status"
        )