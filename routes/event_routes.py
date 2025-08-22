from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app
from flask_login import login_required, current_user
from models.event import Event, RSVP
from models.notifications import Notification  # Add this import
from extensions import db, limiter
from uuid import UUID
import uuid  # Add this import
import os
from datetime import datetime

event = Blueprint('event', __name__, url_prefix='/events')

# Serve uploaded images from the /uploads folder
@event.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    upload_folder = os.path.join(current_app.root_path, 'uploads')
    return send_from_directory(upload_folder, filename)

@event.route('/')
@login_required
@limiter.limit("20 per minute")  # Throttle brute-force attempts
def events():
    events_list = Event.query.all() # Fetch all events from the database
    user_rsvps = {r.event_id for r in RSVP.query.filter_by(user_id=current_user.id).all()}
    return render_template('events.html', events=events_list, user_rsvps=user_rsvps)

@event.route('/rsvp/<uuid:event_id>', methods=['POST'])
@login_required
@limiter.limit("10 per minute")  # Rate limit RSVP attempts
def toggle_rsvp(event_id):
    try:
        event_uuid = str(UUID(str(event_id)))  # Validate UUID
    except ValueError:
        flash('Invalid event ID.', 'danger')
        return redirect(url_for('event.events'))

    event_obj = Event.query.get(event_uuid)
    if not event_obj:
        flash('Event not found.', 'danger')
        return redirect(url_for('event.events'))

    try:
        # Check if the RSVP already exists
        existing_rsvp = RSVP.query.filter_by(user_id=current_user.id, event_id=event_uuid).first()

        if existing_rsvp:
            # Cancel RSVP
            db.session.delete(existing_rsvp)
            
            # Create cancellation notification
            cancellation_notification = Notification(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                type='event_cancellation',
                message=f'You have cancelled your RSVP for "{event_obj.name}"',
                event_name=event_obj.name,
                date_time=event_obj.date_time.strftime('%Y-%m-%d %H:%M') if event_obj.date_time else None,
                location=event_obj.location,
                comments='RSVP cancelled successfully',
                is_read=False,
                created_at=datetime.utcnow()
            )
            
            db.session.add(cancellation_notification)
            db.session.commit()
            
            flash('You have canceled your RSVP for this event.', 'info')
            
        else:
            # Create new RSVP
            new_rsvp = RSVP(user_id=current_user.id, event_id=event_uuid)
            db.session.add(new_rsvp)
            
            # Create signup notification with event details
            signup_notification = Notification(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                type='event_signup',
                message=f'You have successfully signed up for "{event_obj.name}"',
                event_name=event_obj.name,
                date_time=event_obj.date_time.strftime('%Y-%m-%d %H:%M') if event_obj.date_time else None,
                location=event_obj.location,
                comments=f'Event Description: {event_obj.description[:200]}...' if len(event_obj.description) > 200 else event_obj.description,
                is_read=False,
                created_at=datetime.utcnow()
            )
            
            db.session.add(signup_notification)
            db.session.commit()
            
            flash('You have successfully RSVP\'d for this event!', 'success')

    except Exception as e:
        db.session.rollback()
        print(f"Error in toggle_rsvp: {str(e)}")
        flash('A database error occurred. Please try again.', 'danger')

    return redirect(url_for('event.events'))