"""
Migration: Add geolocation support
- user_addresses table (saved delivery addresses)
- delivery_partners: live_latitude, live_longitude, location_updated_at
- Backfill existing restaurants/partners with geocoded coordinates

Run: python migrate_geolocation.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.core.database import engine


def run_migration():
    with engine.connect() as conn:
        # 1. Create user_addresses table
        print("Creating user_addresses table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_addresses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                label VARCHAR(50) NOT NULL DEFAULT 'Home',
                full_address TEXT NOT NULL,
                city VARCHAR(100) NULL,
                area VARCHAR(100) NULL,
                latitude DECIMAL(10, 8) NOT NULL,
                longitude DECIMAL(11, 8) NOT NULL,
                is_default BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))
        print("✅ user_addresses table created")

        # 2. Add live location columns to delivery_partners
        print("Adding live location columns to delivery_partners...")
        try:
            conn.execute(text("""
                ALTER TABLE delivery_partners 
                ADD COLUMN live_latitude DECIMAL(10, 8) NULL,
                ADD COLUMN live_longitude DECIMAL(11, 8) NULL,
                ADD COLUMN location_updated_at DATETIME NULL
            """))
            print("✅ live location columns added to delivery_partners")
        except Exception as e:
            if "Duplicate column" in str(e):
                print("⚠️ live location columns already exist, skipping")
            else:
                raise

        conn.commit()
        print("\n✅ Migration complete!")


if __name__ == "__main__":
    run_migration()
