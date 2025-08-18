from extensions import db
import uuid

class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date_time = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(255), nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    organizer_id = db.Column(db.String(36), db.ForeignKey('user.id'))
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)

class RSVP(db.Model):
    __tablename__ = 'rsvps'  # <- plural to match DB schema

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    event_id = db.Column(db.String(36), db.ForeignKey('events.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='confirmed')
    rsvp_date = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'event_id', name='uq_rsvps_user_event'),
    )