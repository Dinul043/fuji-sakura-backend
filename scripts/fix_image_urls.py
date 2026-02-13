"""
Script to fix image URLs in database - remove localhost prefix
Run this once: python scripts/fix_image_urls.py
"""

from sqlalchemy import create_engine, text
from app.core.config import settings

def fix_image_urls():
    """Remove http://localhost:8000 from all image URLs in database"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as connection:
            # Fix restaurant_menus table
            print("🔧 Fixing restaurant_menus image URLs...")
            result = connection.execute(text("""
                UPDATE restaurant_menus 
                SET image_url = REPLACE(image_url, 'http://localhost:8000', '')
                WHERE image_url LIKE 'http://localhost:8000%'
            """))
            connection.commit()
            print(f"✅ Updated {result.rowcount} menu item images")
            
            # Fix restaurant_applications table
            print("🔧 Fixing restaurant_applications image URLs...")
            result = connection.execute(text("""
                UPDATE restaurant_applications 
                SET restaurant_image = REPLACE(restaurant_image, 'http://localhost:8000', '')
                WHERE restaurant_image LIKE 'http://localhost:8000%'
            """))
            connection.commit()
            print(f"✅ Updated {result.rowcount} restaurant images")
            
            # Fix user_cart table
            print("🔧 Fixing user_cart image URLs...")
            result = connection.execute(text("""
                UPDATE user_cart 
                SET item_image_url = REPLACE(item_image_url, 'http://localhost:8000', '')
                WHERE item_image_url LIKE 'http://localhost:8000%'
            """))
            connection.commit()
            print(f"✅ Updated {result.rowcount} cart item images")
            
            # Fix order_items table
            print("🔧 Fixing order_items image URLs...")
            result = connection.execute(text("""
                UPDATE order_items 
                SET item_image_url = REPLACE(item_image_url, 'http://localhost:8000', '')
                WHERE item_image_url LIKE 'http://localhost:8000%'
            """))
            connection.commit()
            print(f"✅ Updated {result.rowcount} order item images")
            
            print("\n✅ All image URLs fixed! Database now stores only relative paths.")
            print("   Example: /uploads/menu_images/image.png")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure:")
        print("1. Database is running")
        print("2. .env file has correct DATABASE_URL")

if __name__ == "__main__":
    fix_image_urls()
