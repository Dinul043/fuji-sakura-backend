"""
Geocoding API routes — reverse geocode, address search, user saved addresses.
Used by all frontend modules for location detection and address management.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.utils.geocoding import reverse_geocode, search_address, validate_coordinates
from app.utils.security import get_current_user
from app.models.user_address import UserAddress

router = APIRouter(prefix="/api/geocode", tags=["Geocoding"])


# ── Public Geocoding Endpoints ─────────────────────────────────────────────────

@router.get("/reverse")
def api_reverse_geocode(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
):
    """
    Reverse geocode: convert lat/lng to a structured address.
    Used when user clicks "Use My Location" — browser gives GPS, we return address.
    """
    result = reverse_geocode(lat, lng)
    if not result:
        raise HTTPException(status_code=404, detail="Could not determine address for this location")
    return result


@router.get("/search")
def api_search_address(
    q: str = Query(..., min_length=3, max_length=200),
    limit: int = Query(5, ge=1, le=10),
):
    """
    Address search autocomplete.
    User types an address → returns suggestions with lat/lng.
    """
    results = search_address(q, limit=limit)
    return {"suggestions": results}


# ── User Saved Addresses ───────────────────────────────────────────────────────

class SaveAddressRequest(BaseModel):
    label: str = "Home"  # Home, Work, Other
    full_address: str
    city: Optional[str] = None
    area: Optional[str] = None
    latitude: float
    longitude: float
    is_default: bool = False


@router.post("/addresses")
async def save_user_address(
    data: SaveAddressRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save a delivery address for the logged-in user."""
    if not validate_coordinates(data.latitude, data.longitude):
        raise HTTPException(status_code=400, detail="Invalid coordinates")

    # If marking as default, unset other defaults
    if data.is_default:
        existing_defaults = db.query(UserAddress).filter(
            UserAddress.user_id == current_user.id,
            UserAddress.is_default == True
        ).all()
        for addr in existing_defaults:
            addr.is_default = False

    # Limit to 5 saved addresses per user
    count = db.query(UserAddress).filter(UserAddress.user_id == current_user.id).count()
    if count >= 5:
        raise HTTPException(status_code=400, detail="Maximum 5 saved addresses allowed. Please delete one first.")

    address = UserAddress(
        user_id=current_user.id,
        label=data.label.strip(),
        full_address=data.full_address.strip(),
        city=data.city.strip() if data.city else None,
        area=data.area.strip() if data.area else None,
        latitude=data.latitude,
        longitude=data.longitude,
        is_default=data.is_default,
    )
    db.add(address)
    db.commit()
    db.refresh(address)

    return address.to_dict()


@router.get("/addresses")
async def get_user_addresses(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all saved addresses for the logged-in user."""
    addresses = db.query(UserAddress).filter(
        UserAddress.user_id == current_user.id
    ).order_by(UserAddress.is_default.desc(), UserAddress.created_at.desc()).all()

    return [addr.to_dict() for addr in addresses]


@router.delete("/addresses/{address_id}")
async def delete_user_address(
    address_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a saved address."""
    address = db.query(UserAddress).filter(
        UserAddress.id == address_id,
        UserAddress.user_id == current_user.id
    ).first()

    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    db.delete(address)
    db.commit()
    return {"detail": "Address deleted"}


@router.put("/addresses/{address_id}/default")
async def set_default_address(
    address_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set an address as the default delivery address."""
    address = db.query(UserAddress).filter(
        UserAddress.id == address_id,
        UserAddress.user_id == current_user.id
    ).first()

    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    # Unset all other defaults
    db.query(UserAddress).filter(
        UserAddress.user_id == current_user.id,
        UserAddress.id != address_id
    ).update({"is_default": False})

    address.is_default = True
    db.commit()

    return address.to_dict()
