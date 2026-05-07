"""
Fix orders.status enum — must match Python OrderStatus values exactly.
"""
from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Check current state
    r = conn.execute(text("SHOW COLUMNS FROM orders LIKE 'status'"))
    print("Current orders.status:", r.fetchone())

    # Convert existing data to lowercase first
    conn.execute(text("UPDATE orders SET status = LOWER(status)"))
    print("✅ Lowercased all status values")

    # Fix the enum definition
    conn.execute(text(
        "ALTER TABLE orders MODIFY COLUMN status "
        "ENUM('pending','confirmed','preparing','ready','out_for_delivery','delivered','cancelled') "
        "NOT NULL DEFAULT 'pending'"
    ))
    print("✅ Fixed orders.status enum")

    conn.commit()

    # Verify
    r2 = conn.execute(text("SHOW COLUMNS FROM orders LIKE 'status'"))
    print("New orders.status:", r2.fetchone())
    print("✅ Done — restart server")
