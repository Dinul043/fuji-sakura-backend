# Fuji Sakura Food Delivery — Tester Document

**App URL:** http://localhost:3000  
**Backend:** http://localhost:8000  
**Test Date:** May 2026

---

## HOW TO START

1. Start backend: `cd food-delivery-backend` → `python main.py`
2. Start frontend: `cd food-delivery-ui` → `npm run dev`
3. Open browser: `http://localhost:3000`

---

## SECTION 1 — USER SIDE

### 1.1 Signup

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Open app → click "Sign Up" | Signup form appears |
| 2 | Enter email → click Continue | OTP sent to email |
| 3 | Enter wrong OTP | Error: "Invalid OTP" |
| 4 | Enter correct OTP | Move to name/phone/password step |
| 5 | Enter first name (required) | Accepted |
| 6 | Leave last name empty | Should be accepted (optional) |
| 7 | Enter phone — try letters | Only digits allowed, max 10 |
| 8 | Enter password less than 8 chars | Error shown inline |
| 9 | Enter valid password → Submit | Account created, logged in, goes to home |

### 1.2 Login

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Enter wrong email → Submit | Error: "Invalid email or password" |
| 2 | Correct the email → start typing | Error message clears immediately |
| 3 | Enter correct email + wrong password | Error: "Invalid email or password" |
| 4 | Enter correct credentials | Logged in, goes to home page |
| 5 | Check "Remember Me" | Session lasts 30 days |
| 6 | Don't check "Remember Me" | Session lasts 1 day |

### 1.3 Forgot Password

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Click "Forgot Password" | Email input appears |
| 2 | Enter unregistered email | Error: "No account found" |
| 3 | Enter registered email | Reset code sent to email |
| 4 | Enter wrong code | Error shown |
| 5 | Enter correct code | New password step |
| 6 | Enter password less than 8 chars | Error shown |
| 7 | Enter valid new password | Password changed, can login |

### 1.4 Browse Restaurants

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Open home page | Restaurant list loads |
| 2 | Search by name | Filtered results shown |
| 3 | Click a category | Restaurants filtered by category |
| 4 | Click "More" on categories | Shows all categories |
| 5 | Click a restaurant | Restaurant menu page opens |

### 1.5 Place Order — COD

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Open restaurant → Add items to cart | Cart count updates in header |
| 2 | Click "Proceed to Checkout" | Checkout page opens |
| 3 | Fill delivery address | Form accepts input |
| 4 | Select "Cash on Delivery" | COD option selected |
| 5 | Click "Place Order" | Order placed, goes to order success page |
| 6 | Check order history | New order appears with status "Confirmed" |

### 1.6 Place Order — Online Payment

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Add items → Checkout | Checkout page |
| 2 | Select "Online Payment" | Razorpay option shown |
| 3 | Click "Place Order" | Razorpay popup opens |
| 4 | Complete payment | Order confirmed, success page |
| 5 | Cancel payment in Razorpay | Order cancelled, stays in cart |

### 1.7 Cancel Order

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Place order → go to order tracking | Cancel button visible (status: Confirmed) |
| 2 | Click Cancel → confirm | Order cancelled |
| 3 | COD order cancelled | Status: Cancelled, no refund needed |
| 4 | Online order cancelled | Status: Cancelled, refund initiated (5-7 days) |
| 5 | Wait for restaurant to click "Start Preparing" | Cancel button disappears automatically |
| 6 | Try to cancel after preparing | Error: "Restaurant has started preparing" |

### 1.8 Order Tracking (Real-time)

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Place order → open tracking page | Status: Order Confirmed |
| 2 | Restaurant clicks "Start Preparing" | Status updates live → Preparing |
| 3 | Restaurant clicks "Ready for Pickup" | Status updates live → Ready for Pickup |
| 4 | Delivery partner accepts order | Status updates live → Out for Delivery |
| 5 | Delivery partner marks delivered | Status updates live → Delivered |
| 6 | After delivery | Review section appears |

### 1.9 Submit Review

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Open delivered order | Review section visible |
| 2 | Click stars to rate | Stars highlight |
| 3 | Add comment (optional) | Text accepted |
| 4 | Submit | Review saved, shows "Your Review" |
| 5 | Try to submit again | Already submitted, shows existing review |

### 1.10 Profile

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Open profile page | Name, email, phone shown |
| 2 | Edit name/phone | Saved successfully |
| 3 | Change password | Old password required, new password saved |

---

## SECTION 2 — RESTAURANT SIDE

### 2.1 Apply as Restaurant

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Go to `/restaurant/apply` | Application form |
| 2 | Fill all required fields | Form accepts input |
| 3 | Leave required field empty | Inline error shown |
| 4 | Submit | "Application submitted" message |
| 5 | Try same email again | Error: "Already pending" |

### 2.2 Restaurant Login

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Go to `/restaurant/login` | Login form |
| 2 | Login before admin approves | Error: "Application under review" |
| 3 | Login after admin approves | Goes to restaurant dashboard |
| 4 | Wrong password | Error shown, clears when typing |

### 2.3 Restaurant Dashboard

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Open dashboard | Today's orders, revenue, menu count, rating shown |
| 2 | New order placed by user | Notification popup appears (WebSocket) |
| 3 | No UPI ID set | Warning banner shown at top |
| 4 | Click "Add UPI ID" | Goes to profile page |

### 2.4 Manage Orders

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Open Orders page | All orders listed |
| 2 | Filter by status | Filtered correctly |
| 3 | Click "Start Preparing" → confirm | Status → Preparing, user's cancel button disappears |
| 4 | Click "Ready for Pickup" → confirm | Status → Ready, delivery partner can now see order |
| 5 | Cancel confirmed order | Reason dropdown appears, confirm → cancelled |
| 6 | Cancel preparing order | Same as above |
| 7 | Try to cancel ready/out-for-delivery order | Cancel button not shown |
| 8 | Order delivered | Status shows "Delivered" |

### 2.5 Manage Menu

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Open Menu page | All menu items listed |
| 2 | Add new item | Item appears in list |
| 3 | Edit item | Changes saved |
| 4 | Toggle availability | Item shows as unavailable on user side |
| 5 | Delete item | Item removed |
| 6 | Upload image | Image shown on item |

### 2.6 Restaurant Profile

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Open Profile | Business details shown |
| 2 | Add UPI ID | Saved, warning banner disappears from dashboard |
| 3 | Edit business details | Saved successfully |

### 2.7 Earnings

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Open Earnings page | Total revenue, commission, pending payout shown |
| 2 | Check order-wise breakdown | Each order shows: amount, commission, your payout |
| 3 | Pending payout | Shows amount admin hasn't paid yet |
| 4 | Total Received | Shows amount admin already paid |

### 2.8 Reviews

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Open Reviews page | All customer reviews listed |
| 2 | Check rating | Average rating shown |

---

## SECTION 3 — DELIVERY PARTNER SIDE

### 3.1 Apply as Delivery Partner

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Go to `/delivery` → "Join as Delivery Partner" | Application form |
| 2 | Fill all fields | Form accepts input |
| 3 | Submit | "Application submitted" message |

### 3.2 Delivery Partner Login

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Login before admin approves | Error: "Application under review" |
| 2 | Login after admin approves | Goes to delivery dashboard |
| 3 | Forgot password | Reset code sent to email |

### 3.3 Delivery Dashboard

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Open dashboard | Online/Offline toggle, earnings summary shown |
| 2 | No UPI ID set | Warning: "UPI ID required to take orders" |
| 3 | Toggle Online | Status changes to Online |
| 4 | Toggle Offline with active order | Error: "Cannot go offline with active delivery" |

### 3.4 Accept and Deliver Order

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Go Online | Available orders appear (only READY orders) |
| 2 | Restaurant marks order Ready | Order appears in list (WebSocket) |
| 3 | Click "Accept Order" | Order assigned, goes to active delivery |
| 4 | For COD order: click "Mark Collected" | Cash collected confirmed |
| 5 | Click "Mark as Delivered" → confirm | Order delivered, earnings updated |
| 6 | COD order: try to deliver without marking collected | Blocked: "Collect cash first" |

### 3.5 COD Settlement

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Open Settle COD page | Amount due shown |
| 2 | COD due = 0 | "Nothing to settle" message |
| 3 | Click "Pay Now" | Razorpay opens |
| 4 | Complete payment | Settlement recorded, COD due reduces |

### 3.6 Earnings

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Open Earnings page | Today's earnings, total earnings shown |
| 2 | COD to submit | Shows total COD still to return |
| 3 | After admin pays | Pending payout reduces (WebSocket update) |

---

## SECTION 4 — ADMIN SIDE

### 4.1 Admin Login

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Go to `/admin` | Admin login page |
| 2 | Wrong credentials | Error shown |
| 3 | Correct credentials | Goes to admin dashboard |
| 4 | Forgot password | Reset code sent to email |

### 4.2 Admin Dashboard — Stats Cards

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | View dashboard | 4 stat cards: Total, Pending, Approved, Delivery Partners |
| 2 | Click "Pending Review" card | Jumps to restaurants tab, filtered to pending |
| 3 | Click "Delivery Partners" card | Jumps to delivery tab |

### 4.3 Approve/Reject Restaurant

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Click "View Details" on pending restaurant | Detail modal opens |
| 2 | Set commission rate (default 10%) | Rate saved with approval |
| 3 | Add admin notes (optional) | Notes saved |
| 4 | Click "Approve" → confirm | Restaurant approved, email sent |
| 5 | Click "Reject" → confirm | Restaurant rejected, email sent |
| 6 | Update commission rate on approved restaurant | Rate updated for future orders |

### 4.4 Approve/Reject Delivery Partner

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Go to Delivery Partners tab | List of applications |
| 2 | Click "Review" on pending partner | Detail modal opens |
| 3 | Add notes (optional) | Notes saved |
| 4 | Click "Approve" → confirm | Partner approved, can now login |
| 5 | Click "Reject" → confirm | Partner rejected |

### 4.5 Restaurant Payouts

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Click "Restaurant Payouts" button | Payouts page opens |
| 2 | View restaurant list | Pending payout amount shown per restaurant |
| 3 | Click restaurant | Order-wise breakdown shown |
| 4 | No UPI ID set | "Mark Paid" button blocked |
| 5 | Enter UTR/notes | Optional reference saved |
| 6 | Click "Mark Paid" → confirm | Payout marked, restaurant earnings updated |

### 4.6 Delivery Partner Payouts

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Click "Partner Payouts" button | Payouts page opens |
| 2 | View 4-column breakdown | Delivery Earnings / COD Collected / Platform Received / Still Pending |
| 3 | Partner has COD pending | "Mark Paid" button shows "Blocked — COD Pending" |
| 4 | Partner has settled all COD | "Mark Paid" button active |
| 5 | Click "Mark Paid" → confirm | Earnings paid, partner dashboard updates live |
| 6 | View COD Settlement History | All Razorpay settlements listed |

### 4.7 Live Orders

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Click "Live Orders" tab | All active orders shown |
| 2 | Order status shown | Confirmed / Preparing / Ready / Out for Delivery |
| 3 | Delivery partner assigned | Partner name and phone shown |

### 4.8 Manage Admins (Super Admin only)

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Click "Add Admin" | Create admin form |
| 2 | Fill name, email, password | New admin created |
| 3 | Click "Manage Admins" | List of all admins |
| 4 | Deactivate an admin | Admin cannot login |
| 5 | Reactivate an admin | Admin can login again |

---

## IMPORTANT NOTES FOR TESTER

### Order Flow (Correct Sequence)
```
User places order
    ↓
CONFIRMED — User can cancel here
    ↓
Restaurant clicks "Start Preparing"
PREPARING — Restaurant can cancel here, user cannot
    ↓
Restaurant clicks "Ready for Pickup"
READY — Delivery partner sees order now
    ↓
Delivery partner accepts
OUT_FOR_DELIVERY — No one can cancel
    ↓
Delivery partner marks delivered
DELIVERED — User can submit review
```

### COD Flow
```
Partner collects cash from customer
    ↓
Partner marks "Cash Collected"
    ↓
Partner marks "Delivered"
    ↓
Partner settles full COD via Razorpay
    ↓
Admin can now pay delivery earnings to partner
```

### Refund Flow (Online Payment)
```
User cancels confirmed order
    ↓
Razorpay refund initiated automatically
    ↓
Money back to customer in 5-7 business days
```

### Real-time Updates (WebSocket)
- Restaurant gets new order notification instantly
- User's order tracking updates live (no refresh needed)
- Delivery partner sees new orders when restaurant marks Ready
- Admin payout page refreshes when partner settles COD
- Delivery partner dashboard updates when admin pays earnings

---

## TEST ACCOUNTS TO CREATE

| Role | Email | Password |
|------|-------|----------|
| User | testuser@test.com | Test@1234 |
| Restaurant | testrest@test.com | Test@1234 |
| Delivery Partner | testpartner@test.com | Test@1234 |
| Admin | (use existing admin) | (existing password) |

> Note: Restaurant and Delivery Partner accounts need admin approval before they can login.
