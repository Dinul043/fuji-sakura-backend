"""
Migration: Platform Settings + Tax Categories
- platform_settings: admin-controlled business parameters
- tax_categories: GST rates by food category

Run: python migrate_platform_settings.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sqlalchemy import text
from app.core.database import engine


def run_migration():
    with engine.connect() as conn:
        # 1. Platform Settings table
        print("Creating platform_settings table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS platform_settings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                setting_key VARCHAR(100) NOT NULL UNIQUE,
                setting_value VARCHAR(255) NOT NULL,
                description VARCHAR(500) NULL,
                updated_by INT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        print("✅ platform_settings table created")

        # 2. Tax Categories table
        print("Creating tax_categories table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tax_categories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                display_name VARCHAR(100) NOT NULL,
                tax_percent DECIMAL(5, 2) NOT NULL DEFAULT 5.00,
                description VARCHAR(255) NULL,
                is_active BOOLEAN DEFAULT TRUE,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        print("✅ tax_categories table created")

        # 3. Add tax_category column to restaurant_menus
        print("Adding tax_category to restaurant_menus...")
        try:
            conn.execute(text("""
                ALTER TABLE restaurant_menus 
                ADD COLUMN tax_category VARCHAR(100) DEFAULT 'food'
            """))
            print("✅ tax_category column added to restaurant_menus")
        except Exception as e:
            if "Duplicate column" in str(e):
                print("⚠️ tax_category column already exists, skipping")
            else:
                raise

        # 4. Insert default settings
        print("Inserting default platform settings...")
        defaults = [
            ("delivery_fee", "40.00", "Fixed delivery fee per order (₹)"),
            ("cod_limit", "1500.00", "Maximum COD amount a partner can hold (₹)"),
            ("restaurant_radius_km", "15", "Maximum delivery distance from restaurant to user (km)"),
            ("delivery_radius_km", "10", "Maximum distance for partner to see orders (km)"),
            ("platform_fee", "0.00", "Platform convenience fee per order (₹)"),
            ("default_gst_rate", "5.00", "Default GST rate if no category assigned (%)"),
        ]
        for key, value, desc in defaults:
            conn.execute(text(
                "INSERT IGNORE INTO platform_settings (setting_key, setting_value, description) VALUES (:key, :val, :desc)"
            ), {"key": key, "val": value, "desc": desc})
        print("✅ Default settings inserted")

        # 5. Insert default tax categories
        print("Inserting default tax categories...")
        categories = [
            ("food", "Food Items", 5.00, "Regular food items - 5% GST"),
            ("beverages", "Beverages", 12.00, "Soft drinks, juices, shakes - 12% GST"),
            ("luxury_food", "Premium/Luxury", 18.00, "Premium items, imported food - 18% GST"),
            ("packaged", "Packaged Food", 12.00, "Packaged/branded food items - 12% GST"),
            ("no_tax", "Tax Exempt", 0.00, "Items exempt from GST"),
        ]
        for name, display, percent, desc in categories:
            conn.execute(text(
                "INSERT IGNORE INTO tax_categories (name, display_name, tax_percent, description) VALUES (:name, :display, :percent, :desc)"
            ), {"name": name, "display": display, "percent": percent, "desc": desc})
        print("✅ Default tax categories inserted")

        conn.commit()
        print("\n✅ Migration complete!")


if __name__ == "__main__":
    run_migration()
