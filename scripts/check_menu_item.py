"""
Check specific menu item in database
"""
from sqlalchemy import create_engine, text
from app.core.config import settings

def check_item():
    """Check menu item ID 2"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as connection:
        result = connection.execute(text("""
            SELECT id, item_name, is_veg, category, price
            FROM restaurant_menus 
            WHERE id = 2
        """))
        
        row = result.fetchone()
        if row:
            print(f"Menu Item ID 2:")
            print(f"  Name: {row[1]}")
            print(f"  Is Veg: {row[2]} ({'Veg ✅' if row[2] else 'Non-Veg ❌'})")
            print(f"  Category: {row[3]}")
            print(f"  Price: {row[4]}")
        else:
            print("Item not found")

if __name__ == "__main__":
    check_item()
