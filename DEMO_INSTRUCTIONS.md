# Demo Instructions

## Common Issues During Demo

### 1. Restaurant Owner Can't Login (Session Conflict)

**Problem:** Restaurant owner closed browser without logging out, now can't login again.

**Error Message:** "Account is already logged in on another device. Please logout from the other device first or wait for the session to expire (8 hours)."

**Solution:**
```bash
cd food-delivery-backend
python clear_sessions.py
```

This will clear all active restaurant sessions and allow fresh logins.

---

### 2. Backend Not Running

**Problem:** Frontend shows network errors or "Unable to connect to server"

**Solution:**
```bash
cd food-delivery-backend
python main.py
```

Backend should run on `http://localhost:8000`

---

### 3. Frontend Not Running

**Problem:** Can't access the website

**Solution:**
```bash
cd food-delivery-ui
npm run dev
```

Frontend should run on `http://localhost:3000`

---

### 4. Database Connection Issues

**Problem:** Backend shows database connection errors

**Solution:**
- Check if MySQL is running
- Verify `.env` file has correct database credentials
- Check `DATABASE_URL` in `.env`

---

## Quick Demo Reset Commands

### Clear All Restaurant Sessions
```bash
python clear_sessions.py
```

### Check Database Status
```bash
python scripts/check_is_veg_column.py
```

### Check Specific Menu Item
```bash
python scripts/check_menu_item.py
```

---

## Demo Flow

1. **Start Backend:**
   ```bash
   cd food-delivery-backend
   python main.py
   ```

2. **Start Frontend:**
   ```bash
   cd food-delivery-ui
   npm run dev
   ```

3. **If Session Issues Occur:**
   ```bash
   cd food-delivery-backend
   python clear_sessions.py
   ```

4. **Access Application:**
   - User Side: `http://localhost:3000`
   - Restaurant Login: `http://localhost:3000/restaurant/login`
   - Admin Login: `http://localhost:3000/admin`

---

## Tips for Smooth Demo

1. **Always logout properly** - Click the logout button instead of closing browser
2. **Keep terminal open** - Monitor backend logs for errors
3. **Clear sessions before demo** - Run `clear_sessions.py` before starting
4. **Test login first** - Verify restaurant owner can login before demo
5. **Have backup data** - Keep sample menu items ready

---

## Emergency Commands

### Force Clear Everything
```bash
# Clear all sessions
python clear_sessions.py

# Restart backend
# Press Ctrl+C to stop, then:
python main.py
```

### Check What's Running
```bash
# Windows
netstat -ano | findstr :8000
netstat -ano | findstr :3000

# If ports are blocked, kill the process or restart computer
```
