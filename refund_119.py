from app.core.database import SessionLocal
from app.models.orders import Order
from app.models.payment import Payment, PaymentStatus
from app.services.razorpay_service import RazorpayService

db = SessionLocal()
order = db.query(Order).filter(Order.order_number == 'ORD-2026-000119').first()
payment = db.query(Payment).filter(Payment.order_id == order.id).first()

print(f"Triggering refund for {order.order_number}: ₹{order.total_amount}")
print(f"Payment ID: {payment.gateway_payment_id}")

r = RazorpayService()
result = r.refund_payment(payment.gateway_payment_id, order.total_amount)
print(f"Result: {result}")

if result.get('success'):
    payment.payment_status = PaymentStatus.REFUNDED
    payment.failure_reason = "Order cancelled by customer — refund initiated"
    order.payment_status = PaymentStatus.REFUNDED
    db.commit()
    print(f"✅ DB updated — refund ID: {result['refund'].get('id')}")
else:
    print(f"❌ Refund failed: {result.get('error')}")

db.close()
