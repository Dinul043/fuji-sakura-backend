from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.models.review import Review
from app.models.orders import Order, OrderStatus
from app.models.user import User
from app.utils.security import get_current_user

router = APIRouter()

class SubmitReviewRequest(BaseModel):
    order_id: int
    rating: int       # 1-5
    comment: Optional[str] = None

@router.post("")
async def submit_review(
    data: SubmitReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit a review for a delivered order"""
    if not (1 <= data.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    # Verify order exists, belongs to user, and is delivered
    order = db.query(Order).filter(
        Order.id == data.order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(status_code=400, detail="You can only review delivered orders")

    # Check no existing review for this order
    existing = db.query(Review).filter(Review.order_id == data.order_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="You have already reviewed this order")

    review = Review(
        order_id=data.order_id,
        user_id=current_user.id,
        restaurant_id=order.restaurant_id,
        rating=data.rating,
        comment=data.comment.strip() if data.comment else None
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    # Broadcast new review to restaurant via WebSocket
    from app.utils.websocket_manager import manager
    user = db.query(User).filter(User.id == current_user.id).first()
    await manager.broadcast_restaurant_update(order.restaurant_id, {
        "type": "new_review",
        "review": {
            **review.to_dict(),
            "user_name": user.name if user else "Anonymous"
        }
    })

    return {"message": "Review submitted successfully", "review": review.to_dict()}


@router.get("/order/{order_id}")
def get_order_review(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if a review exists for a specific order"""
    review = db.query(Review).filter(Review.order_id == order_id).first()
    if not review:
        return {"review": None}
    return {"review": review.to_dict()}


@router.get("/restaurant/{restaurant_id}")
def get_restaurant_reviews(
    restaurant_id: int,
    db: Session = Depends(get_db)
):
    """Get all reviews for a restaurant (public)"""
    reviews = db.query(Review).filter(
        Review.restaurant_id == restaurant_id
    ).order_by(Review.created_at.desc()).all()

    # Attach user name to each review
    result = []
    for r in reviews:
        d = r.to_dict()
        user = db.query(User).filter(User.id == r.user_id).first()
        d["user_name"] = user.name if user else "Anonymous"
        result.append(d)

    avg = round(sum(r["rating"] for r in result) / len(result), 1) if result else 0

    return {
        "reviews": result,
        "total": len(result),
        "average_rating": avg
    }
