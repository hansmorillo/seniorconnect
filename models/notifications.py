# notifications.py - Enhanced with Output Sanitization
from extensions import db
from datetime import datetime
from utils.security_utils import sanitize_input

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Additional fields
    event_name = db.Column(db.String(255))
    date_time = db.Column(db.String(100))
    location = db.Column(db.String(255))
    comments = db.Column(db.Text)

    # Relationship
    user = db.relationship('User', backref='notifications')

    def __init__(self, **kwargs):
        """
        Input sanitization - sanitize data going INTO the database
        This prevents malicious content from being stored
        """
        # Check if this is a NEW object (not loaded from database)
        # Only sanitize if we're not loading from database (SQLAlchemy sets _sa_instance_state)
        # basically a filter on the way into the database
        if not hasattr(self, '_sa_instance_state'):
            for field in ['message', 'event_name', 'location', 'comments']:
                if field in kwargs and kwargs[field]:
                    kwargs[field] = sanitize_input(kwargs[field])
        
        # Special handling for date_time to ensure proper format
        if 'date_time' in kwargs:
            try:
                datetime.strptime(kwargs['date_time'], '%Y-%m-%d %H:%M')
            except (ValueError, TypeError):
                kwargs['date_time'] = None
                
        super().__init__(**kwargs)

    # OUTPUT SANITIZATION PROPERTIES
    # These properties sanitize data when it's accessed/displayed
    # basically sanitise on the way out
    @property
    def safe_message(self):
        """Get sanitized message for display"""
        return sanitize_input(self.message) if self.message else ''
    
    @property
    def safe_event_name(self):
        """Get sanitized event name for display"""
        return sanitize_input(self.event_name) if self.event_name else ''
    
    @property
    def safe_location(self):
        """Get sanitized location for display"""
        return sanitize_input(self.location) if self.location else ''
    
    @property
    def safe_comments(self):
        """Get sanitized comments for display"""
        return sanitize_input(self.comments) if self.comments else ''

    # DISPLAY METHODS - These provide formatted, safe output
    
    def get_display_title(self):
        """Get the primary display title (event_name or message)"""
        return self.safe_event_name or self.safe_message
    
    def get_formatted_datetime(self):
        """Get formatted date/time or fallback"""
        if not self.date_time:
            return None
        try:
            # If stored as string, try to parse and format nicely
            dt = datetime.strptime(self.date_time, '%Y-%m-%d %H:%M')
            return dt.strftime('%A, %B %d, %Y at %I:%M %p')
        except:
            return self.date_time  # Return as-is if parsing fails

    def to_dict(self):
        """Dictionary representation with sanitized output"""
        return {
            'id': self.id,
            'event_name': self.safe_event_name,
            'date_time': self.get_formatted_datetime(),
            'location': self.safe_location,
            'comments': self.safe_comments,
            'message': self.safe_message,
            'is_read': self.is_read,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

    def to_safe_dict(self):
        """Alias for to_dict() to emphasize safety"""
        return self.to_dict()

    def __repr__(self):
        return f'<Notification {self.id}: {self.get_display_title()[:50]}>'