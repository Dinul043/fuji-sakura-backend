"""
Backfill script: Geocode existing restaurants and delivery partners
that have address/city/area but no latitude/longitude.

Run: python backfill_coordinates.py

Rate-limited to 1 request per second (Nominatim policy).
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.restaurant_application import RestaurantApplication
from app.models.delivery_partner import DeliveryPartner
from app.utils.geocoding import geocode_address


def backfill_restaurants(db: Session):
    """Geocode restaurants that have address but no coordinates."""
    restaurants = db.query(RestaurantApplication).filter(
        RestaurantApplication.latitude == None,
        RestaurantApplication.address != None,
        RestaurantApplication.address != ""
    ).all()

    print(f"\n📍 Found {len(restaurants)} restaurants without coordinates")

    for i, r in enumerate(restaurants):
        query = f"{r.address}"
        if r.area:
            query += f", {r.area}"
        if r.city:
            query += f", {r.city}"

        print(f"  [{i+1}/{len(restaurants)}] Geocoding: {r.business_name} — {query[:60]}...")
        
        coords = geocode_address(query)
        if coords:
            r.latitude = coords[0]
            r.longitude = coords[1]
            print(f"    ✅ ({coords[0]:.6f}, {coords[1]:.6f})")
        else:
            print(f"    ⚠️ Could not geocode")

        time.sleep(1.1)  # Nominatim rate limit: 1 req/sec

    db.commit()
    print(f"✅ Restaurants backfill complete")


def backfill_partners(db: Session):
    """Geocode delivery partners that have city/area but no coordinates."""
    partners = db.query(DeliveryPartner).filter(
        DeliveryPartner.latitude == None,
        DeliveryPartner.city != None,
        DeliveryPartner.city != ""
    ).all()

    print(f"\n🛵 Found {len(partners)} delivery partners without coordinates")

    for i, p in enumerate(partners):
        query = f"{p.area}, {p.city}" if p.area else p.city
        print(f"  [{i+1}/{len(partners)}] Geocoding: {p.name} — {query}...")

        coords = geocode_address(query)
        if coords:
            p.latitude = coords[0]
            p.longitude = coords[1]
            print(f"    ✅ ({coords[0]:.6f}, {coords[1]:.6f})")
        else:
            print(f"    ⚠️ Could not geocode")

        time.sleep(1.1)  # Nominatim rate limit

    db.commit()
    print(f"✅ Partners backfill complete")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        backfill_restaurants(db)
        backfill_partners(db)
        print("\n🎉 All backfill complete!")
    finally:
        db.close()
