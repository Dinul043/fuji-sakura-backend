"""
Database Setup Script — Run this ONCE after cloning to create all tables.

Usage:
    python setup_database.py

This will:
1. Create the database if it doesn't exist
2. Create all tables
3. Insert default platform settings and tax categories
4. Create a default admin account
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env first
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from app.core.config import settings


def get_db_url_without_db():
    """Extract connection URL without the database name."""
    url = settings.DATABASE_URL
    # Remove the database name from the URL
    # Format: mysql+pymysql://user:pass@host:port/dbname
    parts = url.rsplit('/', 1)
    return parts[0]


def setup():
    print("=" * 60)
    print("Fuji Sakura — Database Setup")
    print("=" * 60)

    # Step 1: Create database
    print("\n1. Creating database if not exists...")
    try:
        base_url = get_db_url_without_db()
        engine_root = create_engine(base_url, echo=False)
        with engine_root.connect() as conn:
            conn.execute(text("CREATE DATABASE IF NOT EXISTS fuji_sakura_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            conn.commit()
        print("   ✅ Database 'fuji_sakura_db' ready")
    except Exception as e:
        print(f"   ❌ Failed to create database: {e}")
        print("   Make sure MySQL is running and your .env credentials are correct")
        sys.exit(1)

    # Step 2: Create all tables
    print("\n2. Creating all tables...")
    try:
        from app.core.database import engine, Base
        # Import all models to register them
        from app.models import (
            admin, admin_token, cod_settlement, delivery_partner,
            orders, payment, platform_settings, refresh_token,
            restaurant_application, restaurant_menu, restaurant_payout,
            restaurant_token, review, user, user_address, user_cart,
            user_token
        )
        Base.metadata.create_all(bind=engine)
        print("   ✅ All tables created")
    except Exception as e:
        print(f"   ❌ Failed to create tables: {e}")
        sys.exit(1)

    # Step 3: Insert default platform settings
    print("\n3. Inserting default platform settings...")
    try:
        from app.core.database import SessionLocal
        db = SessionLocal()
        engine2 = engine

        with engine2.connect() as conn:
            defaults = [
                ("delivery_fee", "40.00", "Fixed delivery fee per order (Rs)"),
                ("cod_limit", "1500.00", "Maximum COD amount a partner can hold (Rs)"),
                ("restaurant_radius_km", "15", "Maximum delivery distance from restaurant to user (km)"),
                ("delivery_radius_km", "10", "Maximum distance for partner to see orders (km)"),
                ("platform_fee", "0.00", "Platform convenience fee per order (Rs)"),
                ("default_gst_rate", "5.00", "Default GST rate if no category assigned (%)"),
            ]
            for key, value, desc in defaults:
                conn.execute(text(
                    "INSERT IGNORE INTO platform_settings (setting_key, setting_value, description) VALUES (:k, :v, :d)"
                ), {"k": key, "v": value, "d": desc})

            categories = [
                ("food", "Food Items", 5.00, "Regular food items - 5% GST"),
                ("beverages", "Beverages", 12.00, "Soft drinks, juices, shakes - 12% GST"),
                ("luxury_food", "Premium/Luxury", 18.00, "Premium items - 18% GST"),
                ("packaged", "Packaged Food", 12.00, "Packaged/branded food - 12% GST"),
                ("no_tax", "Tax Exempt", 0.00, "Items exempt from GST"),
            ]
            for name, display, percent, desc in categories:
                conn.execute(text(
                    "INSERT IGNORE INTO tax_categories (name, display_name, tax_percent, description) VALUES (:n, :d, :p, :desc)"
                ), {"n": name, "d": display, "p": percent, "desc": desc})

            conn.commit()
        print("   ✅ Default settings and tax categories inserted")
    except Exception as e:
        print(f"   ⚠️  Could not insert defaults: {e}")

    # Step 4: Create default admin
    print("\n4. Creating default admin account...")
    try:
        from app.models.admin import Admin
        from app.utils.security import get_password_hash
        from app.core.database import SessionLocal

        db = SessionLocal()
        existing = db.query(Admin).filter(Admin.email == "admin@fujisakura.com").first()
        if not existing:
            admin_obj = Admin(
                name="Super Admin",
                email="admin@fujisakura.com",
                password=get_password_hash("Admin@123"),
                is_active=True,
                role="super_admin"
            )
            db.add(admin_obj)
            db.commit()
            print("   ✅ Admin created:")
            print("      Email: admin@fujisakura.com")
            print("      Password: Admin@123")
            print("      ⚠️  CHANGE THIS PASSWORD after first login!")
        else:
            print("   ✅ Admin account already exists")
        db.close()
    except Exception as e:
        print(f"   ⚠️  Could not create admin: {e}")

    print("\n" + "=" * 60)
    print("✅ Setup complete! You can now run: python main.py")
    print("=" * 60)


if __name__ == "__main__":
    setup()
