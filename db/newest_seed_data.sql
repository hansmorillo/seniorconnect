-- Seed data for SeniorConnect
-- Run after: CREATE DATABASE seniorconnect; USE seniorconnect;

USE seniorconnect;

START TRANSACTION;

-- ===== Seed: Events =====
INSERT INTO events
    (id, name, description, date_time, location, image_url, organizer_id, is_verified, created_at, updated_at)
VALUES
    ('11111111-1111-1111-1111-111111111111',
     'Community Health Talk',
     'A session on healthy aging tips and preventive care.',
     '2025-09-01 10:00:00',
     'Community Hall A',
     NULL,
     NULL,
     FALSE,
     NOW(), NOW()),

    ('22222222-2222-2222-2222-222222222222',
     'Senior Yoga Class',
     'Gentle yoga session tailored for seniors. Bring your own mat.',
     '2025-09-05 09:30:00',
     'Wellness Center Room 2',
     NULL,
     NULL,
     FALSE,
     NOW(), NOW()),

    ('33333333-3333-3333-3333-333333333333',
     'Digital Skills Workshop',
     'Learn how to use smartphones and apps to stay connected.',
     '2025-09-10 14:00:00',
     'Library Computer Lab',
     NULL,
     NULL,
     FALSE,
     NOW(), NOW());

COMMIT;
