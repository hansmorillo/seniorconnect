# booking_routes.py - FIXED VERSION
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from flask_wtf.csrf import generate_csrf, validate_csrf, ValidationError
from flask_limiter.util import get_remote_address
from datetime import datetime, date, timedelta
from extensions import db, limiter
from models.booking import Booking
from types import SimpleNamespace
import uuid

booking = Blueprint('booking', __name__, url_prefix='/booking')

def generate_booking_reference():
    """Generate a unique booking reference"""
    timestamp = datetime.now().strftime('%Y%m%d')
    unique_id = str(uuid.uuid4())[:8].upper()
    return f"SC-{timestamp}-{unique_id}"

def _parse_start_time_from_label(label: str):
    """Extract a time() object from a slot label like '8:00 AM – 10:00 AM' or '8:00 AM - 10:00 AM'."""
    if not label:
        return None
    # handle en dash or hyphen
    sep = '–' if '–' in label else '-'
    start_str = label.split(sep)[0].strip()
    try:
        return datetime.strptime(start_str, "%I:%M %p").time()
    except ValueError:
        return None

def _is_within_24h(booking_obj):
    """Return True if the booking starts within the next 24 hours (and is in the future)."""
    start_time = _parse_start_time_from_label(booking_obj.time_slot)
    if not start_time:
        return False  # if we can't parse, don't lock by accident
    start_dt = datetime.combine(booking_obj.booking_date, start_time)
    now = datetime.now()
    return now <= start_dt <= now + timedelta(hours=24)

@booking.route('/', methods=["GET", "POST"])
@login_required
def booking_main():
    token = generate_csrf()
    return render_template('booking.html', csrf_token=token)

@booking.route('/check-availability', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def check_availability():
    """Check which timeslots are already booked for a given location and date"""
    try:
        # Get JSON data from request
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        location = data.get('location')
        date_str = data.get('date')
        
        if not location or not date_str:
            return jsonify({'success': False, 'error': 'Location and date are required'}), 400
        
        # Parse the date
        try:
            booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format'}), 400
        
        # Query the database for existing bookings on this date and location
        existing_bookings = Booking.query.filter_by(
            location=location,
            booking_date=booking_date,
            status='confirmed'  # Only consider confirmed bookings
        ).all()
        
        # Extract the booked timeslots
        booked_timeslots = [booking.time_slot for booking in existing_bookings]
        
        print(f"DEBUG: Availability check successful for {location} on {date_str}")  # Debug log
        
        return jsonify({
            'success': True,
            'booked_timeslots': booked_timeslots,
            'date': date_str,
            'location': location
        })
        
    except Exception as e:
        print(f"Error checking availability: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@booking.route('/success', methods=["GET", "POST"])
@login_required
@limiter.limit("5 per minute")
def booking_success():
    # Handle GET request (refresh/direct access)
    if request.method == 'GET':
        # Check if we have booking data in session
        if 'last_booking_data' in session:
            booking_data = session['last_booking_data'].copy()
            booking_reference = session.get('last_booking_reference')
            
            # Convert date string back to datetime object for template
            if isinstance(booking_data['date'], str):
                try:
                    booking_data['date'] = datetime.strptime(booking_data['date'], "%Y-%m-%d").date()
                except ValueError:
                    # If date parsing fails, redirect to booking main
                    flash('Invalid booking data found. Please make a new booking.', 'error')
                    return redirect(url_for('booking.booking_main'))
            
            # Create namespace object for template
            booking_ns = SimpleNamespace(**booking_data)
            
            return render_template(
                'booking_success.html',
                booking=booking_ns,
                booking_reference=booking_reference
            )
        else:
            # No booking data in session, redirect to main booking page
            flash('No booking information found. Please make a new booking.', 'info')
            return redirect(url_for('booking.booking_main'))
    
    # Handle POST request (new booking submission)
    if not request.form:
        return redirect(url_for('booking.booking_main'))

    try:
        # CSRF validation
        csrf_token = request.form.get('csrf_token')
        if not csrf_token:
            flash('CSRF token missing. Please try again.', 'error')
            return redirect(url_for('booking.booking_main'))

        # Pull fields exactly as named in booking.html
        location = request.form.get('location')
        date_str = request.form.get('date')
        time_label = request.form.get('time')
        
        # Event Details
        event_title = request.form.get('eventTitle')
        interest_group = request.form.get('interestGroup')
        attendees = request.form.get('attendees')
        activity_type = request.form.get('activityType')
        equipment = request.form.get('equipment', '').strip()
        description = request.form.get('description', '').strip()
        
        # Organiser
        organiser_name = request.form.get('organiserName')
        organiser_email = request.form.get('organiserEmail')
        organiser_phone = request.form.get('organiserPhone')
        accessibility_help = request.form.get('accessibilityHelp')
        
        # Validate required fields
        if not all([location, date_str, time_label, event_title, interest_group, 
                   attendees, activity_type, organiser_name, organiser_email, 
                   organiser_phone, accessibility_help]):
            flash('All required fields must be filled out.', 'error')
            return redirect(url_for('booking.booking_main'))
        
        # Parse date
        try:
            booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('booking.booking_main'))
        
        # Validate attendees
        try:
            attendees_count = int(attendees)
            if attendees_count <= 0:
                raise ValueError("Attendees must be positive")
        except ValueError:
            flash('Invalid number of attendees.', 'error')
            return redirect(url_for('booking.booking_main'))
        
        # Check if this exact booking already exists (prevent duplicate submissions)
        existing_booking = Booking.query.filter_by(
            location=location,
            booking_date=booking_date,
            time_slot=time_label,
            organiser_email=organiser_email,
            status='confirmed'
        ).first()
        
        if existing_booking:
            flash('A booking with these details already exists.', 'warning')
            # Still show the success page with existing booking data
            booking_ns = SimpleNamespace(
                location=location,
                date=booking_date,
                time=time_label,
                event_title=event_title,
                interest_group=interest_group,
                activity_type=activity_type,
                attendees=attendees_count,
                equipment=equipment,
                description=description,
                organiser_name=organiser_name,
                organiser_email=organiser_email,
                organiser_phone=organiser_phone,
                accessibility_help=accessibility_help
            )
            return render_template(
                'booking_success.html',
                booking=booking_ns,
                booking_reference=existing_booking.reference_number
            )
        
        # Generate unique reference
        reference_number = generate_booking_reference()
        
        # Create new booking record
        new_booking = Booking(
            reference_number=reference_number,
            location=location,
            booking_date=booking_date,
            time_slot=time_label,
            event_title=event_title,
            interest_group=interest_group,
            activity_type=activity_type,
            expected_attendees=attendees_count,
            equipment_required=equipment if equipment else None,
            event_description=description if description else None,
            organiser_name=organiser_name,
            organiser_email=organiser_email,
            organiser_phone=organiser_phone,
            accessibility_help=accessibility_help,
            booked_by_user_id=current_user.id if current_user.is_authenticated else None,
            status='confirmed'
        )
        
        # Save to database
        db.session.add(new_booking)
        db.session.commit()
        
        print(f"Booking saved successfully with reference: {reference_number}")  # Debug log
        
        # Store booking data in session for refresh protection
        booking_data = {
            'location': location,
            'date': booking_date.strftime('%Y-%m-%d'),  # Store as string for session compatibility
            'time': time_label,
            'event_title': event_title,
            'interest_group': interest_group,
            'activity_type': activity_type,
            'attendees': attendees_count,
            'equipment': equipment,
            'description': description,
            'organiser_name': organiser_name,
            'organiser_email': organiser_email,
            'organiser_phone': organiser_phone,
            'accessibility_help': accessibility_help
        }
        
        session['last_booking_data'] = booking_data
        session['last_booking_reference'] = reference_number
        
        # Create a namespace object for the template (with proper date object)
        booking_ns = SimpleNamespace(
            location=location,
            date=booking_date,  # Keep as date object for immediate template use
            time=time_label,
            event_title=event_title,
            interest_group=interest_group,
            activity_type=activity_type,
            attendees=attendees_count,
            equipment=equipment,
            description=description,
            organiser_name=organiser_name,
            organiser_email=organiser_email,
            organiser_phone=organiser_phone,
            accessibility_help=accessibility_help
        )
        
        return render_template(
            'booking_success.html',
            booking=booking_ns,
            booking_reference=reference_number
        )
        
    except ValidationError as e:
        # CSRF validation failed
        print(f"CSRF validation error: {str(e)}")
        flash('Security validation failed. Please try again.', 'error')
        return redirect(url_for('booking.booking_main'))
    except Exception as e:
        # Log the error and rollback
        print(f"Booking error: {str(e)}")
        db.session.rollback()
        flash('An error occurred while processing your booking. Please try again.', 'error')
        return redirect(url_for('booking.booking_main'))

@booking.route('/manage')
@login_required
def booking_manage():
    """Display user's bookings - both upcoming and past"""
    try:
        today = date.today()
        
        # Get upcoming bookings (only confirmed bookings with future dates)
        upcoming_bookings = Booking.query.filter(
            Booking.booked_by_user_id == current_user.id,
            Booking.booking_date >= today,
            Booking.status == 'confirmed'
        ).order_by(Booking.booking_date.asc(), Booking.time_slot.asc()).all()
        
        for b in upcoming_bookings:
            # attach a transient attribute used by the template
            b.is_edit_locked = _is_within_24h(b)

        # Get past bookings - includes:
        # 1. All bookings with past dates (regardless of status)
        # 2. All cancelled bookings (regardless of date)
        from sqlalchemy import or_
        
        past_bookings = Booking.query.filter(
            Booking.booked_by_user_id == current_user.id
        ).filter(
            or_(
                Booking.booking_date < today,  # Past date bookings
                Booking.status == 'cancelled'  # OR cancelled bookings
            )
        ).order_by(Booking.booking_date.desc()).all()
        
        # Generate CSRF token for the forms
        csrf_token = generate_csrf()
        
        return render_template(
            'booking_manage.html', 
            upcoming_bookings=upcoming_bookings,
            past_bookings=past_bookings,
            csrf_token=csrf_token
        )
        
    except Exception as e:
        print(f"Error loading bookings: {str(e)}")
        flash('Error loading your bookings. Please try again.', 'error')
        return redirect(url_for('booking.booking_main'))
    
@booking.route('/get-booking/<booking_id>')
@login_required
def get_booking(booking_id):
    """Get booking details for editing/viewing"""
    try:
        booking_obj = Booking.query.filter_by(
            id=booking_id,
            booked_by_user_id=current_user.id
        ).first()
        
        if not booking_obj:
            return jsonify({'success': False, 'error': 'Booking not found'}), 404
        
        booking_data = {
            'id': booking_obj.id,
            'reference_number': booking_obj.reference_number,
            'location': booking_obj.location,
            'booking_date': booking_obj.booking_date.strftime('%Y-%m-%d'),
            'time_slot': booking_obj.time_slot,
            'event_title': booking_obj.event_title,
            'interest_group': booking_obj.interest_group,
            'activity_type': booking_obj.activity_type,
            'expected_attendees': booking_obj.expected_attendees,
            'equipment_required': booking_obj.equipment_required,
            'event_description': booking_obj.event_description,
            'organiser_name': booking_obj.organiser_name,
            'organiser_email': booking_obj.organiser_email,
            'organiser_phone': booking_obj.organiser_phone,
            'accessibility_help': booking_obj.accessibility_help,
            'status': booking_obj.status
        }
        
        return jsonify({'success': True, 'booking': booking_data})
        
    except Exception as e:
        print(f"Error getting booking: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@booking.route('/update-booking/<booking_id>', methods=['PUT'])
@login_required
@limiter.limit("20 per hour")
def update_booking(booking_id):
    """Update booking details"""
    try:
        booking_obj = Booking.query.filter_by(
            id=booking_id,
            booked_by_user_id=current_user.id,
            status='confirmed'
        ).first()
        
        # Disallow edits for bookings starting within 24 hours
        if _is_within_24h(booking_obj):
            return jsonify({
                'success': False,
                'error': 'Bookings starting within the next 24 hours cannot be edited. You can only cancel.'
            }), 400

        if not booking_obj:
            return jsonify({'success': False, 'error': 'Booking not found or cannot be edited'}), 404
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['event_title', 'interest_group', 'activity_type', 
                         'expected_attendees', 'organiser_name', 'organiser_email', 
                         'organiser_phone', 'accessibility_help']
        
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
        # Parse and validate date if provided
        if data.get('booking_date'):
            try:
                new_date = datetime.strptime(data['booking_date'], '%Y-%m-%d').date()
                if new_date < date.today():
                    return jsonify({'success': False, 'error': 'Cannot change to a past date'}), 400
            except ValueError:
                return jsonify({'success': False, 'error': 'Invalid date format'}), 400
        else:
            new_date = booking_obj.booking_date
        
        # If date or time slot changed, check availability
        new_time_slot = data.get('time_slot', booking_obj.time_slot)
        if new_date != booking_obj.booking_date or new_time_slot != booking_obj.time_slot:
            existing_booking = Booking.query.filter_by(
                location=booking_obj.location,
                booking_date=new_date,
                time_slot=new_time_slot,
                status='confirmed'
            ).filter(Booking.id != booking_id).first()
            
            if existing_booking:
                return jsonify({'success': False, 'error': 'This time slot is already booked'}), 400
        
        # Update booking fields
        booking_obj.booking_date = new_date
        booking_obj.time_slot = new_time_slot
        booking_obj.event_title = data['event_title']
        booking_obj.interest_group = data['interest_group']
        booking_obj.activity_type = data['activity_type']
        booking_obj.expected_attendees = int(data['expected_attendees'])
        booking_obj.equipment_required = data.get('equipment_required', '').strip() or None
        booking_obj.event_description = data.get('event_description', '').strip() or None
        booking_obj.organiser_name = data['organiser_name']
        booking_obj.organiser_email = data['organiser_email']
        booking_obj.organiser_phone = data['organiser_phone']
        booking_obj.accessibility_help = data['accessibility_help']
        booking_obj.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Booking updated successfully'})
        
    except Exception as e:
        print(f"Error updating booking: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@booking.route('/cancel-booking/<booking_id>', methods=['PUT'])
@login_required
@limiter.limit("10 per hour")
def cancel_booking(booking_id):
    """Cancel a booking"""
    try:
        booking_obj = Booking.query.filter_by(
            id=booking_id,
            booked_by_user_id=current_user.id,
            status='confirmed'
        ).first()
        
        if not booking_obj:
            return jsonify({'success': False, 'error': 'Booking not found or already cancelled'}), 404
        
        # Check if booking is in the future
        if booking_obj.booking_date < date.today():
            return jsonify({'success': False, 'error': 'Cannot cancel past bookings'}), 400
        
        booking_obj.status = 'cancelled'
        booking_obj.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Booking cancelled successfully'})
        
    except Exception as e:
        print(f"Error cancelling booking: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Internal server error'}), 500