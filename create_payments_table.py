"""
Database migration script to create payments table
Run this script to add the payments table to your database
"""

from app.core.database import engine, Base
from app.models.payment import Payment
from app.models.orders import Order

def create_payments_table():
    """Create payments table in database"""
    try:
        print("Creating payments table...")
        
        # Create only the payments table
        Payment.__table__.create(engine, checkfirst=True)
        
        print("✅ Payments table created successfully!")
        print("\nTable structure:")
        print("- id (Primary Key)")
        print("- order_id (Foreign Key → orders.id)")
        print("- payment_method (ENUM: card, upi, wallet, cod)")
        print("- amount (Float)")
        print("- payment_status (ENUM: pending, paid, failed, refunded)")
        print("- transaction_reference (String, nullable)")
        print("- gateway_order_id (String, nullable) - For Razorpay later")
        print("- gateway_payment_id (String, nullable) - For Razorpay later")
        print("- gateway_signature (String, nullable) - For Razorpay later")
        print("- failure_reason (Text, nullable)")
        print("- retry_count (Integer, default 0)")
        print("- created_at (DateTime)")
        print("- payment_initiated_at (DateTime, nullable)")
        print("- payment_completed_at (DateTime, nullable)")
        print("- updated_at (DateTime)")
        
    except Exception as e:
        print(f"❌ Error creating payments table: {e}")
        raise

if __name__ == "__main__":
    create_payments_table()
