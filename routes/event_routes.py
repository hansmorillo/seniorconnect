from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app
from flask_login import login_required, current_user
from models.event import Event, RSVP
from extensions import db, limiter
from uuid import UUID
from sqlalchemy.exc import IntegrityError
import os

event = Blueprint('event', __name__, url_prefix='/events')

# Serve uploaded images from the /uploads folder
@event.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    upload_folder = os.path.join(current_app.root_path, 'uploads')
    return send_from_directory(upload_folder, filename)

@event.route('/')
@login_required
def events():
    events_list = Event.query.all() # Fetch all events from the database
    user_rsvps = {r.event_id for r in RSVP.query.filter_by(user_id=current_user.id).all()}
    return render_template('events.html', events=events_list, user_rsvps=user_rsvps)

@event.route('/rsvp/<uuid:event_id>', methods=['POST'])
@login_required
@limiter.limit("5 per minute")  # Rate limit login attempts
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
            db.session.commit()
            flash('You have canceled your RSVP for this event.', 'info')
        else:
            # Insert new RSVP
            new_rsvp = RSVP(user_id=current_user.id, event_id=event_uuid)
            db.session.add(new_rsvp)
            db.session.commit()
            flash('You have successfully RSVP’d for this event!', 'success')

    except IntegrityError:
        db.session.rollback()
        flash('A database error occurred. Please try again.', 'danger')

    return redirect(url_for('event.events'))

