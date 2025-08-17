# test_notifications.py
import pytest
import uuid
from flask import url_for
from models.notifications import Notification
from extensions import db

def test_access_other_users_notification(client, auth, test_user, test_user2):
    """Test that users cannot access other users' notifications."""
    
    # Create notification for user1
    with client.application.app_context():
        notification = Notification(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            type='test',
            message='Test notification for user1',
            event_name='Test Event',
            date_time='2023-01-01 12:00',
            location='Test Location',
            comments='Test comment'
        )
        db.session.add(notification)
        db.session.commit()
        notification_id = notification.id

    # Login as user2 and try to dismiss user1's notification
    auth.login(test_user2.email, 'password2')
    
    # This should return 403 Forbidden (not 404 to avoid information leakage)
    response = client.post(
        url_for('user.dismiss_notification', notification_id=notification_id),
        follow_redirects=False  # Don't follow redirects to see the actual status
    )
    
    # Should return 403 Forbidden
    assert response.status_code == 403
    
    # Verify the notification still exists (wasn't deleted)
    with client.application.app_context():
        notification = Notification.query.get(notification_id)
        assert notification is not None
        assert notification.user_id == test_user.id

def test_list_only_own_notifications(client, auth, test_user, test_user2):
    """Test that users only see their own notifications in the list."""
    
    # Create notifications for both users
    with client.application.app_context():
        # Notification for user1
        note1 = Notification(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            type='test',
            message='Note for user1',
            event_name='User1 Event',
            date_time='2023-01-01 12:00',
            location='User1 Location',
            comments='User1 comment'
        )
        db.session.add(note1)
        
        # Notification for user2
        note2 = Notification(
            id=str(uuid.uuid4()),
            user_id=test_user2.id,
            type='test',
            message='Note for user2',
            event_name='User2 Event',
            date_time='2023-01-02 12:00',
            location='User2 Location',
            comments='User2 comment'
        )
        db.session.add(note2)
        db.session.commit()
        
        # Store IDs for verification
        note1_id = note1.id
        note2_id = note2.id
    
    # Login as user1 and check they only see their notification
    login_response = auth.login(test_user.email, 'password')
    assert login_response.status_code in [200, 302]  # Allow both direct success and redirect
    
    response = client.get(url_for('user.notifications'))
    assert response.status_code == 200
    
    # Check that user1's notification is present
    assert b'User1 Event' in response.data
    assert b'User1 Location' in response.data
    assert b'User1 comment' in response.data
    
    # Check that user2's notification is NOT present
    assert b'User2 Event' not in response.data
    assert b'User2 Location' not in response.data
    assert b'User2 comment' not in response.data
    
    # Verify in database that both notifications still exist
    with client.application.app_context():
        assert Notification.query.get(note1_id) is not None
        assert Notification.query.get(note2_id) is not None

def test_mark_all_notifications_read_only_own(client, auth, test_user, test_user2):
    """Test that mark all as read only affects current user's notifications."""
    
    with client.application.app_context():
        # Create unread notifications for both users
        note1 = Notification(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            type='test',
            message='Unread note for user1',
            is_read=False
        )
        note2 = Notification(
            id=str(uuid.uuid4()),
            user_id=test_user2.id,
            type='test',
            message='Unread note for user2',
            is_read=False
        )
        db.session.add_all([note1, note2])
        db.session.commit()
        
        note1_id = note1.id
        note2_id = note2.id
    
    # Login as user1 and mark all as read
    auth.login(test_user.email, 'password')
    response = client.post(url_for('user.mark_all_notifications_read'))
    assert response.status_code == 302  # Redirect after POST
    
    # Verify only user1's notification was marked as read
    with client.application.app_context():
        note1 = Notification.query.get(note1_id)
        note2 = Notification.query.get(note2_id)
        
        assert note1.is_read == True   # User1's notification should be read
        assert note2.is_read == False  # User2's notification should still be unread

def test_clear_all_notifications_only_own(client, auth, test_user, test_user2):
    """Test that clear all only deletes current user's notifications."""
    
    with client.application.app_context():
        # Create notifications for both users
        note1 = Notification(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            type='test',
            message='Note for user1'
        )
        note2 = Notification(
            id=str(uuid.uuid4()),
            user_id=test_user2.id,
            type='test',
            message='Note for user2'
        )
        db.session.add_all([note1, note2])
        db.session.commit()
        
        note1_id = note1.id
        note2_id = note2.id
    
    # Login as user1 and clear all notifications
    auth.login(test_user.email, 'password')
    response = client.post(url_for('user.clear_all_notifications'))
    assert response.status_code == 302  # Redirect after POST
    
    # Verify only user1's notification was deleted
    with client.application.app_context():
        note1 = Notification.query.get(note1_id)
        note2 = Notification.query.get(note2_id)
        
        assert note1 is None          # User1's notification should be deleted
        assert note2 is not None      # User2's notification should still exist

def test_access_nonexistent_notification(client, auth, test_user):
    """Test accessing a notification that doesn't exist."""
    
    auth.login(test_user.email, 'password')
    
    # Try to dismiss a non-existent notification
    fake_id = str(uuid.uuid4())
    response = client.post(
        url_for('user.dismiss_notification', notification_id=fake_id),
        follow_redirects=False
    )
    
    # Should return 404 for non-existent notification
    assert response.status_code == 404