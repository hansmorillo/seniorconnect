-- =========================================================
-- SeniorConnect — Seed Data (matches live_schema.sql)
-- For demo/testing only — NOT for production
-- =========================================================

USE seniorconnect;

-- ---------------------------------------------------------
-- Users
-- (One normal user, one admin user)
-- ---------------------------------------------------------
INSERT INTO users (id, display_name, phone_number, email, password_hash, is_verified, is_admin)
VALUES
('11111111-1111-1111-1111-111111111111', 'Alice Tan', '91234567', 'alice@example.com', '$2b$12$abcdefghijk1234567890lmnopqrstuv', 1, 0),
('22222222-2222-2222-2222-222222222222', 'Admin Lee', '98765432', 'admin@example.com', '$2b$12$abcdefghijk1234567890lmnopqrstuv', 1, 1);

-- ---------------------------------------------------------
-- Pending Users (demo unverified account)
-- ---------------------------------------------------------
INSERT INTO pending_users (display_name, phone_number, email, password_hash, verification_token, expires_at)
VALUES
('Pending User', '90000000', 'pending@example.com', '$2b$12$abcdefghijk1234567890lmnopqrstuv', 'pendingtoken123', NOW() + INTERVAL 1 DAY);

-- ---------------------------------------------------------
-- Locations
-- ---------------------------------------------------------
INSERT INTO locations (id, name, address, description, category, capacity, is_bookable)
VALUES
('33333333-3333-3333-3333-333333333333', 'Function Room', '123 Main St', 'Air-conditioned multipurpose room', 'Community', 50, 1),
('44444444-4444-4444-4444-444444444444', 'Sports Hall', '456 Park Ave', 'Indoor sports hall with seating', 'Sports', 200, 1);

-- ---------------------------------------------------------
-- Events
-- ---------------------------------------------------------
INSERT INTO events (id, name, description, date_time, location, organizer_id, is_verified)
VALUES
('55555555-5555-5555-5555-555555555555', 'Yoga for Seniors', 'Gentle yoga session suitable for all levels', '2025-09-01 10:00:00', 'Function Room', '11111111-1111-1111-1111-111111111111', 1),
('66666666-6666-6666-6666-666666666666', 'Community Chess Meetup', 'Casual chess games for enthusiasts', '2025-09-02 14:00:00', 'Sports Hall', '11111111-1111-1111-1111-111111111111', 1);

-- ---------------------------------------------------------
-- RSVPs
-- ---------------------------------------------------------
INSERT INTO rsvps (id, user_id, event_id, status)
VALUES
('77777777-7777-7777-7777-777777777777', '11111111-1111-1111-1111-111111111111', '55555555-5555-5555-5555-555555555555', 'confirmed');

-- ---------------------------------------------------------
-- Bookings
-- ---------------------------------------------------------
INSERT INTO bookings (id, reference_number, location, booking_date, time_slot, event_title, interest_group, activity_type, expected_attendees, organiser_name, organiser_email, organiser_phone, accessibility_help, booked_by_user_id, status)
VALUES
('88888888-8888-8888-8888-888888888888', 'SC-20250823-ABCD1234', 'Function Room', '2025-09-05', '10:30 AM – 12:30 PM', 'Knitting Workshop', 'Crafting & Knitting', 'Workshop', 15, 'Alice Tan', 'alice@example.com', '91234567', 'No', '11111111-1111-1111-1111-111111111111', 'confirmed');

-- ---------------------------------------------------------
-- Notifications
-- ---------------------------------------------------------
INSERT INTO notifications (id, user_id, type, message, is_read)
VALUES
('99999999-9999-9999-9999-999999999999', '11111111-1111-1111-1111-111111111111', 'event_signup', 'You have successfully signed up for Yoga for Seniors', 0);

-- ---------------------------------------------------------
-- Feedbacks
-- ---------------------------------------------------------
INSERT INTO feedbacks (id, user_id, name, email, subject, content)
VALUES
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111', 'Alice Tan', 'alice@example.com', 'Love the app', 'Really enjoying the events and booking system!');


