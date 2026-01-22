# SQL Queries Reference - Two Table Structure

## 📋 **Basic Table Queries**

### **View Users Table Only:**
```sql
-- All users
SELECT * FROM users;

-- Recent users
SELECT * FROM users ORDER BY created_at DESC LIMIT 5;

-- Verified users only
SELECT id, email, name, is_verified FROM users WHERE is_verified = 1;

-- Unverified users only
SELECT id, email, name, is_verified FROM users WHERE is_verified = 0;
```

### **View User Tokens Table Only:**
```sql
-- All tokens
SELECT * FROM user_tokens;

-- Active OTPs only
SELECT * FROM user_tokens WHERE otp IS NOT NULL;

-- Expired OTPs
SELECT * FROM user_tokens WHERE otp_expires_at < NOW();

-- Valid OTPs (not expired)
SELECT * FROM user_tokens WHERE otp_expires_at > NOW();
```

## 🔗 **Combined Queries (JOIN)**

### **1. Show All Users with Their Tokens (LEFT JOIN):**
```sql
SELECT 
    u.id,
    u.email,
    u.name,
    u.is_verified,
    u.created_at,
    ut.otp,
    ut.otp_expires_at,
    ut.reset_token
FROM users u
LEFT JOIN user_tokens ut ON u.id = ut.user_id
ORDER BY u.created_at DESC;
```

### **2. Show Only Users Who Have Active Tokens (INNER JOIN):**
```sql
SELECT 
    u.id,
    u.email,
    u.name,
    ut.otp,
    ut.otp_expires_at
FROM users u
INNER JOIN user_tokens ut ON u.id = ut.user_id
WHERE ut.otp IS NOT NULL
ORDER BY ut.created_at DESC;
```

### **3. Show Users with Valid (Non-Expired) OTPs:**
```sql
SELECT 
    u.id,
    u.email,
    u.name,
    ut.otp,
    ut.otp_expires_at,
    TIMEDIFF(ut.otp_expires_at, NOW()) as time_remaining
FROM users u
INNER JOIN user_tokens ut ON u.id = ut.user_id
WHERE ut.otp IS NOT NULL 
  AND ut.otp_expires_at > NOW()
ORDER BY ut.otp_expires_at ASC;
```

## 🔍 **Specific User Queries**

### **Find User by Email with Tokens:**
```sql
SELECT 
    u.*,
    ut.otp,
    ut.otp_expires_at,
    ut.reset_token
FROM users u
LEFT JOIN user_tokens ut ON u.id = ut.user_id
WHERE u.email = 'dinul@gmail.com';
```

### **Find User by OTP:**
```sql
SELECT 
    u.id,
    u.email,
    u.name,
    ut.otp,
    ut.otp_expires_at
FROM users u
INNER JOIN user_tokens ut ON u.id = ut.user_id
WHERE ut.otp = '5298';
```

## 📊 **Statistics & Counts**

### **User Statistics:**
```sql
SELECT 
    COUNT(*) as total_users,
    SUM(CASE WHEN is_verified = 1 THEN 1 ELSE 0 END) as verified_users,
    SUM(CASE WHEN is_verified = 0 THEN 1 ELSE 0 END) as unverified_users,
    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_users
FROM users;
```

### **Token Statistics:**
```sql
SELECT 
    COUNT(*) as total_tokens,
    COUNT(otp) as active_otps,
    COUNT(reset_token) as active_reset_tokens,
    SUM(CASE WHEN otp_expires_at > NOW() THEN 1 ELSE 0 END) as valid_otps,
    SUM(CASE WHEN otp_expires_at <= NOW() THEN 1 ELSE 0 END) as expired_otps
FROM user_tokens;
```

## 🧹 **Cleanup Queries**

### **Remove Expired OTPs:**
```sql
DELETE FROM user_tokens 
WHERE otp_expires_at <= NOW();
```

### **Remove Expired Reset Tokens:**
```sql
DELETE FROM user_tokens 
WHERE reset_token_expires_at <= NOW();
```

### **Remove All Tokens for Verified Users:**
```sql
DELETE ut FROM user_tokens ut
INNER JOIN users u ON ut.user_id = u.id
WHERE u.is_verified = 1;
```

## 🔧 **Management Queries**

### **Recently Registered Users (Last 24 Hours):**
```sql
SELECT 
    u.id,
    u.email,
    u.name,
    u.is_verified,
    u.created_at,
    ut.otp
FROM users u
LEFT JOIN user_tokens ut ON u.id = ut.user_id
WHERE u.created_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)
ORDER BY u.created_at DESC;
```

### **Users Pending Verification (with OTP):**
```sql
SELECT 
    u.id,
    u.email,
    u.name,
    ut.otp,
    ut.otp_expires_at,
    CASE 
        WHEN ut.otp_expires_at > NOW() THEN 'Valid'
        ELSE 'Expired'
    END as otp_status
FROM users u
INNER JOIN user_tokens ut ON u.id = ut.user_id
WHERE u.is_verified = 0 
  AND ut.otp IS NOT NULL
ORDER BY ut.created_at DESC;
```

### **Complete User Profile (All Data):**
```sql
SELECT 
    u.id,
    u.email,
    u.name,
    u.is_verified,
    u.is_active,
    u.created_at,
    u.updated_at,
    u.last_login,
    u.deleted_at,
    ut.otp,
    ut.otp_expires_at,
    ut.reset_token,
    ut.reset_token_expires_at,
    CASE 
        WHEN ut.otp_expires_at > NOW() THEN 'Valid OTP'
        WHEN ut.otp_expires_at <= NOW() THEN 'Expired OTP'
        ELSE 'No OTP'
    END as otp_status
FROM users u
LEFT JOIN user_tokens ut ON u.id = ut.user_id
WHERE u.email = 'your-email@example.com';
```

## 🚀 **Quick Commands for MySQL Workbench**

### **1. View Recent Activity:**
```sql
SELECT 
    u.email,
    u.name,
    u.is_verified,
    ut.otp,
    CASE 
        WHEN ut.otp_expires_at > NOW() THEN CONCAT('Valid for ', TIMESTAMPDIFF(MINUTE, NOW(), ut.otp_expires_at), ' minutes')
        WHEN ut.otp_expires_at <= NOW() THEN 'Expired'
        ELSE 'No OTP'
    END as otp_status
FROM users u
LEFT JOIN user_tokens ut ON u.id = ut.user_id
ORDER BY u.created_at DESC
LIMIT 10;
```

### **2. Debug Specific User:**
```sql
-- Replace 'user@example.com' with actual email
SELECT 
    'USER INFO' as section, u.id, u.email, u.name, u.is_verified, u.created_at, NULL as otp, NULL as expires_at
FROM users u WHERE u.email = 'dinul@gmail.com'
UNION ALL
SELECT 
    'TOKEN INFO' as section, ut.user_id, NULL, NULL, NULL, ut.created_at, ut.otp, ut.otp_expires_at
FROM user_tokens ut 
INNER JOIN users u ON ut.user_id = u.id 
WHERE u.email = 'dinul@gmail.com';
```

## 💡 **Tips for MySQL Workbench:**

1. **Use LIMIT** to avoid large results: `LIMIT 10`
2. **Use WHERE** to filter: `WHERE is_verified = 1`
3. **Use ORDER BY** to sort: `ORDER BY created_at DESC`
4. **Use LEFT JOIN** to see all users (even without tokens)
5. **Use INNER JOIN** to see only users with tokens

---

**Quick Copy-Paste Commands:**

```sql
-- See all users with their tokens
SELECT u.id, u.email, u.name, u.is_verified, ut.otp, ut.otp_expires_at 
FROM users u LEFT JOIN user_tokens ut ON u.id = ut.user_id 
ORDER BY u.created_at DESC LIMIT 10;

-- See only users with active OTPs
SELECT u.email, u.name, ut.otp, ut.otp_expires_at 
FROM users u INNER JOIN user_tokens ut ON u.id = ut.user_id 
WHERE ut.otp IS NOT NULL ORDER BY ut.created_at DESC;

-- Clean up expired tokens
DELETE FROM user_tokens WHERE otp_expires_at <= NOW();
```