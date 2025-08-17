# models/booking.py
from extensions import db  # Import db from your extensions
from datetime import datetime
from sqlalchemy import UniqueConstraint, CheckConstraint
import uuid

class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reference_number = db.Column(db.String(50), unique=True, nullable=False)
    
    # Location and timing
    location = db.Column(db.String(255), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(100), nullable=False)
    
    # Event details
    event_title = db.Column(db.String(255), nullable=False)
    interest_group = db.Column(db.String(100), nullable=False)
    activity_type = db.Column(db.String(100), nullable=False)
    expected_attendees = db.Column(db.Integer, nullable=False)
    equipment_required = db.Column(db.Text)
    event_description = db.Column(db.Text)
    
    # Organiser details
    organiser_name = db.Column(db.String(255), nullable=False)
    organiser_email = db.Column(db.String(255), nullable=False)
    organiser_phone = db.Column(db.String(20), nullable=False)
    accessibility_help = db.Column(db.String(10), nullable=False)
    
    # System fields
    booked_by_user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='SET NULL'))
    status = db.Column(db.String(50), default='confirmed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('location', 'booking_date', 'time_slot', 'status', name='uq_booking_slot_status'),
        CheckConstraint('expected_attendees > 0 AND expected_attendees <= 1000', name='chk_expected_attendees_range'),
    )
    
    def __repr__(self):
        return f'<Booking {self.reference_number}: {self.event_title}>'