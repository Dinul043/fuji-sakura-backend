"""
Fix image URLs in database - convert relative paths to full URLs
Run this once: python scripts/fix_image_urls_to_full.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine

def fix_image_urls():
    try:
        with engine.connect() as connection:
            # Fix menu images
            print("🔧 Fixing menu item image URLs...")
            result = connection.execute(text("""
                UPDATE restaurant_menus 
                SET image_url = CONCAT('http://localhost:8000', image_url)
                WHERE image_url LIKE '/uploads/%'
            """))
            connection.commit()
            print(f"✅ Fixed {result.rowcount} menu item images")
            
            # Fix restaurant images
            print("🔧 Fixing restaurant image URLs...")
            result = connection.execute(text("""
                UPDATE restaurant_applications 
                SET restaurant_image = CONCAT('http://localhost:8000', restaurant_image)
                WHERE restaurant_image LIKE '/uploads/%'
            """))
            connection.commit()
            print(f"✅ Fixed {result.rowcount} restaurant images")
            
            # Fix cart images
            print("🔧 Fixing cart item image URLs...")
            result = connection.execute(text("""
                UPDATE user_cart 
                SET item_image_url = CONCAT('http://localhost:8000', item_image_url)
                WHERE item_image_url LIKE '/uploads/%'
            """))
            connection.commit()
            print(f"✅ Fixed {result.rowcount} cart item images")
            
            print("\n✅ All image URLs fixed successfully!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_image_urls()
