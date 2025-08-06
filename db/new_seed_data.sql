USE seniorconnect;

-- 1. Users
INSERT INTO users (id, display_name, phone_number, email, password_hash) VALUES
('11111111-1111-1111-1111-111111111111', 'Alice Tan', '91234567', 'alice@example.com', '$2b$12$abcdefghijklmnopqrstuv'),
('22222222-2222-2222-2222-222222222222', 'Bob Lee', '92345678', 'bob@example.com', '$2b$12$abcdefghijklmnopqrstuv');

-- 2. Events
INSERT INTO events (id, name, description, date_time, location, organizer_id) VALUES
('33333333-3333-3333-3333-333333333333', 'Community Walk', 'Morning walk at the park', '2025-08-15 07:00:00', 'Central Park', '11111111-1111-1111-1111-111111111111');

-- 3. Interest Groups
INSERT INTO interest_groups (id, name, description, creator_id) VALUES
('44444444-4444-4444-4444-444444444444', 'Healthy Living', 'Group promoting healthy lifestyles', '11111111-1111-1111-1111-111111111111');

-- 4. Locations
INSERT INTO locations (id, name, address, description, category, capacity) VALUES
('55555555-5555-5555-5555-555555555555', 'Community Hall', '123 Main Street', 'Large hall for events', 'Hall', 100);

-- 5. Group Memberships
INSERT INTO group_memberships (id, user_id, group_id, role) VALUES
('66666666-6666-6666-6666-666666666666', '11111111-1111-1111-1111-111111111111', '44444444-4444-4444-4444-444444444444', 'admin'),
('77777777-7777-7777-7777-777777777777', '22222222-2222-2222-2222-222222222222', '44444444-4444-4444-4444-444444444444', 'member');

-- 6. RSVPs
INSERT INTO rsvps (id, user_id, event_id, status) VALUES
('88888888-8888-8888-8888-888888888888', '22222222-2222-2222-2222-222222222222', '33333333-3333-3333-3333-333333333333', 'confirmed');

-- 7. Bookings
INSERT INTO bookings (id, location_id, booked_by_user_id, purpose_description, start_time, end_time, status) VALUES
('99999999-9999-9999-9999-999999999999', '55555555-5555-5555-5555-555555555555', '11111111-1111-1111-1111-111111111111', 'Yoga Class', '2025-08-20 09:00:00', '2025-08-20 11:00:00', 'approved');

-- 8. Notifications
INSERT INTO notifications (id, user_id, type, message) VALUES
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '22222222-2222-2222-2222-222222222222', 'event', 'You are confirmed for Community Walk');

-- 9. Chats
INSERT INTO chats (id, group_id, type) VALUES
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '44444444-4444-4444-4444-444444444444', 'group');

-- 10. Messages
INSERT INTO messages (id, chat_id, sender_id, content) VALUES
('cccccccc-cccc-cccc-cccc-cccccccccccc', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '11111111-1111-1111-1111-111111111111', 'Welcome to the group!');

-- 11. Private Chat Participants
INSERT INTO private_chat_participants (id, chat_id, user_id) VALUES
('dddddddd-dddd-dddd-dddd-dddddddddddd', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '22222222-2222-2222-2222-222222222222');
