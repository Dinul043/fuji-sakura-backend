"""
Fix: payments.payment_status enum uses UPPERCASE but Python model uses lowercase.
This aligns the DB enum to match the Python PaymentStatus enum values.
"""
from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # First update any existing uppercase values to lowercase
    conn.execute(text("UPDATE payments SET payment_status = LOWER(payment_status)"))
    print("✅ Converted existing values to lowercase")

    # Then change the enum definition to lowercase
    conn.execute(text(
        "ALTER TABLE payments MODIFY COLUMN payment_status "
        "ENUM('pending','paid','failed','refunded') NOT NULL DEFAULT 'pending'"
    ))
    print("✅ payments.payment_status enum updated to lowercase")

    conn.commit()
    print("✅ Done")
