"""Fix: Add REFUNDED to orders.payment_status enum in MySQL"""
from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE orders MODIFY COLUMN payment_status "
        "ENUM('pending','paid','failed','refunded') NOT NULL DEFAULT 'pending'"
    ))
    conn.commit()
    print("✅ orders.payment_status enum updated — REFUNDED added")
