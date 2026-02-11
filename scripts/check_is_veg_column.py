"""
Check if is_veg column exists in restaurant_menus table
"""
from sqlalchemy import create_engine, text, inspect
from app.core.config import settings

def check_column():
    """Check if is_veg column exists"""
    engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(engine)
    
    # Get all columns in restaurant_menus table
    columns = inspector.get_columns('restaurant_menus')
    
    print("Columns in restaurant_menus table:")
    for col in columns:
        print(f"  - {col['name']}: {col['type']}")
    
    # Check if is_veg exists
    has_is_veg = any(col['name'] == 'is_veg' for col in columns)
    
    if has_is_veg:
        print("\n✅ is_veg column exists!")
        
        # Check some sample data
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT id, item_name, is_veg 
                FROM restaurant_menus 
                LIMIT 5
            """))
            
            print("\nSample menu items:")
            for row in result:
                print(f"  ID {row[0]}: {row[1]} - {'Veg' if row[2] else 'Non-Veg'}")
    else:
        print("\n❌ is_veg column does NOT exist!")

if __name__ == "__main__":
    check_column()
