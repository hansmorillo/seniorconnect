-- =========================================================
-- SeniorConnect — Clean Rebuild Schema + Email Verification + Bookings v2
-- Safe on a fresh DB. For existing DBs, this script:
--   • Temporarily disables FK checks
--   • Drops dependent tables first to avoid circular-FK issues
--   • Recreates tables in correct dependency order (users → others)
--   • Adds version-agnostic migration for users.is_verified
--   • Provides quick diagnostics at the end
-- =========================================================

-- ---------------------------------------------------------------------
-- Global safety toggles for targeted DROP/CREATE operations
-- ---------------------------------------------------------------------
SET SQL_SAFE_UPDATES = 0;
SET @OLD_FOREIGN_KEY_CHECKS = @@FOREIGN_KEY_CHECKS;
SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------------------------------------------------
-- Create DB (no-op if already exists) and USE it
-- ---------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS seniorconnect;
USE seniorconnect;

-- =====================================================================
-- 0) Clean drops (dependents first) to guarantee a clean rebuild
--    (No-ops if tables don’t exist)
-- =====================================================================
DROP TABLE IF EXISTS rsvps;
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS feedbacks;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS locations;
DROP TABLE IF EXISTS pending_users;
DROP TABLE IF EXISTS users;

-- =====================================================================
-- 1) Core tables
--    Order matters: create `users` FIRST, then tables that reference it.
-- =====================================================================

-- 1.1) Users (includes email verification flag)
CREATE TABLE users (
    id CHAR(36) PRIMARY KEY,                          -- UUID string (e.g., 8-4-4-4-12)
    display_name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    is_verified TINYINT(1) NOT NULL DEFAULT 1,        -- email verification status
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- 1.2) Events (references users.id via organizer_id)
CREATE TABLE events (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    date_time DATETIME NOT NULL,
    location VARCHAR(255) NOT NULL,
    image_url TEXT,
    organizer_id CHAR(36),                            -- FK to users.id (nullable)
    is_verified BOOLEAN DEFAULT FALSE,                -- event moderation flag (optional)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_events_organizer
      FOREIGN KEY (organizer_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- 1.3) RSVPs (composite uniqueness on user/event)
CREATE TABLE rsvps (
    id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    event_id CHAR(36) NOT NULL,
    status VARCHAR(50) DEFAULT 'confirmed',
    rsvp_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE (user_id, event_id),
    CONSTRAINT fk_rsvps_user  FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE CASCADE,
    CONSTRAINT fk_rsvps_event FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- 1.4) Locations (kept for other features even though bookings stores a text location)
CREATE TABLE locations (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL,
    description TEXT,
    category VARCHAR(100),
    capacity INT,
    image_url TEXT,
    is_bookable BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 2) Bookings — recreated to match the new structure
--    (Free-text location, organiser details, soft FK to users via booked_by_user_id)
-- =====================================================================
CREATE TABLE bookings (
    id CHAR(36) PRIMARY KEY,
    reference_number VARCHAR(50) UNIQUE NOT NULL,

    -- Location and timing
    location VARCHAR(255) NOT NULL,
    booking_date DATE NOT NULL,
    time_slot VARCHAR(100) NOT NULL,

    -- Event details
    event_title VARCHAR(255) NOT NULL,
    interest_group VARCHAR(100) NOT NULL,
    activity_type VARCHAR(100) NOT NULL,
    expected_attendees INT NOT NULL,
    equipment_required TEXT,
    event_description TEXT,

    -- Organiser details
    organiser_name VARCHAR(255) NOT NULL,
    organiser_email VARCHAR(255) NOT NULL,
    organiser_phone VARCHAR(20) NOT NULL,
    accessibility_help VARCHAR(10) NOT NULL,

    -- System fields
    booked_by_user_id CHAR(36),
    status VARCHAR(50) DEFAULT 'confirmed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_booked_by_user_id (booked_by_user_id), -- helps FK lookups/joins
    CONSTRAINT fk_bookings_user
      FOREIGN KEY (booked_by_user_id) REFERENCES users(id)
      ON DELETE SET NULL
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 3) Notifications and Feedbacks
-- =====================================================================

CREATE TABLE notifications (
    id CHAR(36) PRIMARY KEY,
    user_id CHAR(36),
    type VARCHAR(100) NOT NULL,
    event_name VARCHAR(255),
    date_time VARCHAR(100),
    location VARCHAR(255),
    comments TEXT,
    message TEXT NOT NULL,
    link TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_notifications_user_id (user_id),
    CONSTRAINT fk_notifications_user
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- Use CHAR(36) for id and user_id to stay consistent with users.id (UUID strings)
CREATE TABLE feedbacks (
    id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_feedbacks_user_id (user_id),
    CONSTRAINT fk_feedbacks_user
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 4) Pending users — supports email verification flow
-- =====================================================================
CREATE TABLE pending_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    display_name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(128) NOT NULL,
    verification_token VARCHAR(100) NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    INDEX idx_email (email),
    INDEX idx_verification_token (verification_token),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 5) Idempotent migration steps for existing DBs (version-agnostic)
--     Safely add users.is_verified if missing (pre-8.0.29 compatible),
--     then set all current users to verified.
-- =====================================================================
SET @col_exists := (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'users'
    AND COLUMN_NAME = 'is_verified'
);

SET @sql := IF(
  @col_exists = 0,
  'ALTER TABLE users ADD COLUMN is_verified TINYINT(1) NOT NULL DEFAULT 1',
  'SELECT ''users.is_verified already exists'' AS info'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

UPDATE users
SET is_verified = 1
WHERE id IS NOT NULL;

-- =====================================================================
-- 6) Quick Verification / Diagnostics
-- =====================================================================
SELECT 'users table structure:' AS info;
DESCRIBE users;

SELECT 'pending_users table structure:' AS info;
DESCRIBE pending_users;

SELECT 'Current users count:' AS info, COUNT(*) AS count FROM users;

SELECT 'Sample users (id, display_name, email, is_verified, created_at):' AS info;
SELECT id, display_name, email, is_verified, created_at
FROM users
LIMIT 5;

-- ---------------------------------------------------------------------
-- Restore FK checks
-- ---------------------------------------------------------------------
SET FOREIGN_KEY_CHECKS = @OLD_FOREIGN_KEY_CHECKS;
