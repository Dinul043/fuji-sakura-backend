"""
Fix ALL enum case mismatches across all tables.
Run this once, then restart the server.
"""
from app.core.database import engine
from sqlalchemy import text

fixes = [
    # orders table
    ("orders", "status",
     "ENUM('pending','confirmed','preparing','ready','out_for_delivery','delivered','cancelled') NOT NULL DEFAULT 'pending'"),
    ("orders", "payment_status",
     "ENUM('pending','paid','failed','refunded') NOT NULL DEFAULT 'pending'"),
    # payments table
    ("payments", "payment_status",
     "ENUM('pending','paid','failed','refunded') NOT NULL DEFAULT 'pending'"),
    ("payments", "payment_method",
     "ENUM('online','cod') NOT NULL"),
]

with engine.connect() as conn:
    # First convert all existing data to lowercase
    for table, col, _ in fixes:
        try:
            conn.execute(text(f"UPDATE {table} SET {col} = LOWER({col})"))
            print(f"✅ Lowercased {table}.{col}")
        except Exception as e:
            print(f"⚠️ {table}.{col} update: {e}")

    # Then fix the enum definitions
    for table, col, enum_def in fixes:
        try:
            conn.execute(text(f"ALTER TABLE {table} MODIFY COLUMN {col} {enum_def}"))
            print(f"✅ Fixed {table}.{col} enum")
        except Exception as e:
            print(f"⚠️ {table}.{col} alter: {e}")

    conn.commit()
    print("\n✅ All done — restart the server now")
