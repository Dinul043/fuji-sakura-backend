-- Database Migration Script: Split users table into users + user_tokens
-- This script safely migrates existing data to the new two-table structure

-- Database Migration Script: Split users table into users + user_tokens
-- This script safely migrates existing data to the new two-table structure

-- Step 1: Create the new user_tokens table
CREATE TABLE user_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    otp VARCHAR(6) NULL,  -- Keep same size as original
    otp_expires_at TIMESTAMP NULL,
    reset_token VARCHAR(6) NULL,  -- Keep same size as original
    reset_token_expires_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_otp_expires (otp_expires_at),
    INDEX idx_reset_expires (reset_token_expires_at)
);

-- Step 2: Migrate existing OTP/token data from users to user_tokens
INSERT INTO user_tokens (user_id, otp, otp_expires_at, reset_token, reset_token_expires_at, created_at)
SELECT 
    id as user_id,
    otp,
    otp_expires_at,
    reset_token,
    reset_token_expires_at,
    created_at
FROM users 
WHERE otp IS NOT NULL 
   OR otp_expires_at IS NOT NULL 
   OR reset_token IS NOT NULL 
   OR reset_token_expires_at IS NOT NULL;

-- Step 3: Add new columns to users table
ALTER TABLE users 
ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
ADD COLUMN deleted_at TIMESTAMP NULL;

-- Step 4: Remove OTP/token columns from users table (after confirming migration worked)
-- UNCOMMENT THESE LINES AFTER VERIFYING THE MIGRATION:
-- ALTER TABLE users DROP COLUMN otp;
-- ALTER TABLE users DROP COLUMN otp_expires_at;
-- ALTER TABLE users DROP COLUMN reset_token;
-- ALTER TABLE users DROP COLUMN reset_token_expires_at;

-- Step 5: Create restaurant_applications table
CREATE TABLE restaurant_applications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    business_name VARCHAR(255) NOT NULL,
    owner_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    address TEXT NOT NULL,
    cuisine_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    business_license VARCHAR(255) NOT NULL,
    food_permit VARCHAR(255) NOT NULL,
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    admin_notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP NULL,
    reviewed_by INT NULL,
    INDEX idx_status (status),
    INDEX idx_email (email),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Step 6: Verify the migration
SELECT 'Users table count:' as info, COUNT(*) as count FROM users
UNION ALL
SELECT 'User tokens count:' as info, COUNT(*) as count FROM user_tokens
UNION ALL
SELECT 'Restaurant applications count:' as info, COUNT(*) as count FROM restaurant_applications;

-- Step 7: Show sample data to verify
SELECT u.id, u.email, u.name, u.is_verified, ut.otp, ut.otp_expires_at
FROM users u
LEFT JOIN user_tokens ut ON u.id = ut.user_id
ORDER BY u.created_at DESC
LIMIT 5;