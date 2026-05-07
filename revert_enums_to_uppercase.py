"""
REVERT: Put enum values back to UPPERCASE to match what the running server expects.
The server was working fine before — we broke it by lowercasing the data.
"""
from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Revert orders.status back to UPPERCASE
    conn.execute(text("UPDATE orders SET status = UPPER(status)"))
    print("✅ Reverted orders.status to UPPERCASE")

    # Revert orders.payment_status back to UPPERCASE  
    conn.execute(text("UPDATE orders SET payment_status = UPPER(payment_status)"))
    print("✅ Reverted orders.payment_status to UPPERCASE")

    # Revert payments.payment_status back to UPPERCASE
    conn.execute(text("UPDATE payments SET payment_status = UPPER(payment_status)"))
    print("✅ Reverted payments.payment_status to UPPERCASE")

    # Revert payments.payment_method back to UPPERCASE
    conn.execute(text("UPDATE payments SET payment_method = UPPER(payment_method)"))
    print("✅ Reverted payments.payment_method to UPPERCASE")

    # Fix the enum definitions back to UPPERCASE
    conn.execute(text(
        "ALTER TABLE orders MODIFY COLUMN status "
        "ENUM('PENDING','CONFIRMED','PREPARING','READY','OUT_FOR_DELIVERY','DELIVERED','CANCELLED') "
        "NOT NULL DEFAULT 'PENDING'"
    ))
    print("✅ Fixed orders.status enum to UPPERCASE")

    conn.execute(text(
        "ALTER TABLE orders MODIFY COLUMN payment_status "
        "ENUM('PENDING','PAID','FAILED','REFUNDED') NOT NULL DEFAULT 'PENDING'"
    ))
    print("✅ Fixed orders.payment_status enum to UPPERCASE")

    conn.execute(text(
        "ALTER TABLE payments MODIFY COLUMN payment_status "
        "ENUM('PENDING','PAID','FAILED','REFUNDED') NOT NULL DEFAULT 'PENDING'"
    ))
    print("✅ Fixed payments.payment_status enum to UPPERCASE")

    conn.execute(text(
        "ALTER TABLE payments MODIFY COLUMN payment_method "
        "ENUM('ONLINE','COD') NOT NULL"
    ))
    print("✅ Fixed payments.payment_method enum to UPPERCASE")

    conn.commit()
    print("\n✅ All reverted — restart server now")
