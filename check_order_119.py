from app.core.database import SessionLocal
from app.models.orders import Order
from app.models.payment import Payment

db = SessionLocal()
order = db.query(Order).filter(Order.order_number == 'ORD-2026-000119').first()
if order:
    print(f"Order: {order.order_number}")
    print(f"  status: {order.status}")
    print(f"  payment_method: {repr(order.payment_method)}")
    print(f"  payment_status: {order.payment_status}")
    print(f"  cancelled_by: {order.cancelled_by}")
    
    p = db.query(Payment).filter(Payment.order_id == order.id).first()
    if p:
        print(f"Payment:")
        print(f"  payment_status: {p.payment_status}")
        print(f"  gateway_payment_id: {p.gateway_payment_id}")
        print(f"  failure_reason: {p.failure_reason}")
    else:
        print("No payment record found")
else:
    print("Order not found")
db.close()
