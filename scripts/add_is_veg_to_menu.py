"""
Migration script to add is_veg column to restaurant_menus table
"""
from sqlalchemy import create_engine, text
from app.core.config import settings

def add_is_veg_column():
    """Add is_veg column to restaurant_menus table"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as connection:
        # Check if column already exists
        result = connection.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_name='restaurant_menus' 
            AND column_name='is_veg'
        """))
        
        column_exists = result.scalar() > 0
        
        if not column_exists:
            print("Adding is_veg column to restaurant_menus table...")
            connection.execute(text("""
                ALTER TABLE restaurant_menus 
                ADD COLUMN is_veg BOOLEAN NOT NULL DEFAULT TRUE
            """))
            connection.commit()
            print("✅ Successfully added is_veg column")
        else:
            print("ℹ️  is_veg column already exists")

if __name__ == "__main__":
    add_is_veg_column()
