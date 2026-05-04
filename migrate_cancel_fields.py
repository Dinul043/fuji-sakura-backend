"""
Migration: Add cancellation tracking fields to orders table
Run once: python migrate_cancel_fields.py
"""
from app.core.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        # Add cancelled_by column
        try:
            conn.execute(text("ALTER TABLE orders ADD COLUMN cancelled_by VARCHAR(20) NULL"))
            print("✅ Added cancelled_by")
        except Exception as e:
            print(f"⚠️ cancelled_by: {e}")

        # Add cancel_reason column
        try:
            conn.execute(text("ALTER TABLE orders ADD COLUMN cancel_reason VARCHAR(255) NULL"))
            print("✅ Added cancel_reason")
        except Exception as e:
            print(f"⚠️ cancel_reason: {e}")

        # Add cancelled_at column
        try:
            conn.execute(text("ALTER TABLE orders ADD COLUMN cancelled_at DATETIME NULL"))
            print("✅ Added cancelled_at")
        except Exception as e:
            print(f"⚠️ cancelled_at: {e}")

        conn.commit()
        print("✅ Migration complete")

if __name__ == "__main__":
    migrate()
