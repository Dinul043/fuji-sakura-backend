"""
Quick script to add is_online column to restaurant_applications table
Run this once: python add_is_online_column.py
"""

from sqlalchemy import text
from app.core.database import engine

def add_is_online_column():
    try:
        with engine.connect() as connection:
            # Check if column already exists
            check_query = text("""
                SELECT COUNT(*) as count
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = 'fuji_sakura_db' 
                AND TABLE_NAME = 'restaurant_applications' 
                AND COLUMN_NAME = 'is_online'
            """)
            result = connection.execute(check_query)
            exists = result.fetchone()[0] > 0
            
            if exists:
                print("✅ Column 'is_online' already exists!")
                return
            
            # Add the column
            alter_query = text("""
                ALTER TABLE restaurant_applications 
                ADD COLUMN is_online BOOLEAN NOT NULL DEFAULT TRUE
            """)
            connection.execute(alter_query)
            connection.commit()
            
            print("✅ Successfully added 'is_online' column to restaurant_applications table!")
            print("   All existing restaurants are now set to ONLINE by default.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nAlternatively, run this SQL command directly in MySQL:")
        print("ALTER TABLE restaurant_applications ADD COLUMN is_online BOOLEAN NOT NULL DEFAULT TRUE;")

if __name__ == "__main__":
    add_is_online_column()
