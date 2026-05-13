"""Check latest cancelled online order and its refund status"""
from app.core.database import SessionLocal
from app.models.orders import Order, OrderStatus
from app.models.payment import Payment

db = SessionLocal()

# Get latest cancelled online orders
orders = db.query(Order).filter(
    Order.status == OrderStatus.CANCELLED,
    Order.payment_method == 'online'
).order_by(Order.id.desc()).limit(3).all()

for o in orders:
    p = db.query(Payment).filter(Payment.order_id == o.id).first()
    print(f"\nOrder {o.id} ({o.order_number}):")
    print(f"  payment_method = {repr(o.payment_method)}")
    print(f"  payment_status = {repr(o.payment_status)}")
    print(f"  cancelled_by   = {o.cancelled_by}")
    print(f"  cancelled_at   = {o.cancelled_at}")
    if p:
        print(f"  Payment status = {repr(p.payment_status)}")
        print(f"  gateway_id     = {p.gateway_payment_id}")
        print(f"  failure_reason = {p.failure_reason}")
    else:
        print(f"  No payment record found")

db.close()
