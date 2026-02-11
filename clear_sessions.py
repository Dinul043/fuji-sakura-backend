"""
Quick script to clear all restaurant sessions for demo purposes
Run this when a restaurant owner closes browser without logging out
"""
from sqlalchemy import create_engine, text
from app.core.config import settings

def clear_all_restaurant_sessions():
    """Clear all restaurant sessions"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as connection:
        # Clear all restaurant sessions
        result = connection.execute(text("""
            UPDATE restaurant_applications 
            SET active_session_token = NULL, 
                session_expires_at = NULL
            WHERE active_session_token IS NOT NULL
        """))
        connection.commit()
        
        affected = result.rowcount
        print(f"✅ Cleared {affected} restaurant session(s)")
        
        if affected == 0:
            print("ℹ️  No active sessions found")
        else:
            print("   Restaurant owners can now login again")

if __name__ == "__main__":
    print("🧹 Clearing all restaurant sessions...")
    clear_all_restaurant_sessions()
