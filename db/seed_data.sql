-- seed_data.sql

USE seniorconnect;

INSERT INTO interest_groups (id, name, description, creator_id)
VALUES ('uuid-group-1', 'Gardening Club', 'A group for plant lovers.', 'uuid-user-1');

INSERT INTO group_memberships (id, user_id, group_id)
VALUES ('uuid-membership-1', 'uuid-user-1', 'uuid-group-1');

INSERT INTO events (id, name, description, date_time, location, organizer_id)
VALUES ('uuid-event-1', 'Picnic at Botanic Gardens', 'Join us for a fun picnic!', '2025-08-15 10:00:00', 'Singapore Botanic Gardens', 'uuid-user-1');

INSERT INTO rsvps (id, user_id, event_id)
VALUES ('uuid-rsvp-1', 'uuid-user-1', 'uuid-event-1');

INSERT INTO locations (id, name, address, category, capacity)
VALUES ('uuid-loc-1', 'Community Hall A', '123 Sunshine Rd, SG', 'Hall', 50);

INSERT INTO bookings (id, location_id, booked_by_user_id, purpose_description, start_time, end_time)
VALUES ('uuid-booking-1', 'uuid-loc-1', 'uuid-user-1', 'Yoga Class', '2025-08-20 09:00:00', '2025-08-20 11:00:00');

INSERT INTO chats (id, group_id, type)
VALUES ('uuid-chat-1', 'uuid-group-1', 'group');

INSERT INTO messages (id, chat_id, sender_id, content)
VALUES ('uuid-msg-1', 'uuid-chat-1', 'uuid-user-1', 'Hello and welcome!');

INSERT INTO private_chat_participants (id, chat_id, user_id)
VALUES ('uuid-pc-1', 'uuid-chat-1', 'uuid-user-1');

INSERT INTO notifications (id, user_id, type, message)
VALUES ('uuid-note-1', 'uuid-user-1', 'reminder', 'Your booking is tomorrow!');
