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
import logging, json

ALLOWED_LOCATIONS = {"Indoor Sports Hall", "Function Room", "Multi-purpose Hall"}

VALID_INTEREST_GROUPS = {"Yoga", "Chess", "Taichi", "Mahjong", "Gardening", "Silver Fitness", "Karaoke", "Crafting & Knitting", "Chinese Calligraphy", "Cooking", "Technology Learners", "Local Explorers", "Photography"}

VALID_ACTIVITY_TYPES = {"Workshop", "Talk", "Performance", "Hands-on Session", "Meeting", "Event", "Others"}

ENFORCE_DROPDOWN_WHITELIST = False

# Mirror your actual labels; server must be source of truth
TIME_SLOTS_BY_LOCATION = {
    "Indoor Sports Hall": [
        {"label": "8:00 AM – 10:00 AM"},
        {"label": "10:30 AM – 12:30 PM"},
        {"label": "1:00 PM – 3:00 PM"},
        {"label": "3:30 PM – 5:30 PM"},
        {"label": "6:00 PM – 8:00 PM"},
        {"label": "8:30 PM – 10:30 PM"},
    ],
    "Function Room": [
        {"label": "8:00 AM – 9:00 AM"},
        {"label": "9:30 AM – 10:30 AM"},
        {"label": "11:00 AM – 12:00 PM"},
        {"label": "12:30 PM – 1:30 PM"},
        {"label": "2:00 PM – 3:00 PM"},
        {"label": "3:30 PM – 4:30 PM"},
        {"label": "5:00 PM – 6:00 PM"},
        {"label": "6:30 PM – 7:30 PM"},
        {"label": "8:00 PM – 9:00 PM"},
    ],
    "Multi-purpose Hall": [
        {"label": "8:00 AM – 9:30 AM"},
        {"label": "9:45 AM – 11:15 AM"},
        {"label": "11:30 AM – 1:00 PM"},
        {"label": "1:15 PM – 2:45 PM"},
        {"label": "3:00 PM – 4:30 PM"},
        {"label": "4:45 PM – 6:15 PM"},
        {"label": "6:30 PM – 8:00 PM"},
        {"label": "8:15 PM – 9:45 PM"},
    ],
}

def validate_input_sizes(form_data):
    limits = {
        'eventTitle': 100,
        'description': 1000,
        'equipment': 500,
        'organiserName': 100,
        'organiserEmail': 100,
        'organiserPhone': 20,
        'attendees': 10,  # length of string
    }
    for field, max_len in limits.items():
        val = form_data.get(field, '') or ''
        if len(str(val)) > max_len:
            return False, f"{field} exceeds maximum length of {max_len} characters"
    # numeric sanity for attendees
    try:
        att = int(form_data.get('attendees', '0'))
    except ValueError:
        return False, "Invalid attendees number"
    if not (1 <= att <= 1000):
        return False, "Maximum 1000 attendees allowed"
    return True, None

def _normalize_slot(label: str) -> str:
    """Normalise a slot label by unifying dash type and whitespace around it."""
    if not label:
        return ""
    # unify to en-dash
    norm = label.replace("—", "–").replace("-", "–")
    # ensure single spaces around dash
    parts = [p.strip() for p in norm.split("–")]
    return " – ".join(parts) if len(parts) == 2 else norm.strip()

def validate_booking_rules(location, date_str, time_slot):
    if location not in ALLOWED_LOCATIONS:
        return False, "Invalid location"
    try:
        booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return False, "Invalid date format"
    if booking_date < date.today():
        return False, "Cannot book past dates"
    
    # extra guard: if booking is today, disallow slots that have already started
    if booking_date == date.today():
        start_t = _parse_start_time_from_label(time_slot)
        if start_t and datetime.combine(booking_date, start_t) <= datetime.now():
            return False, "Cannot book a timeslot that has already started"

    valid_slots = TIME_SLOTS_BY_LOCATION.get(location, [])
    norm_time = _normalize_slot(time_slot)
    valid_norm = {_normalize_slot(s['label']) for s in valid_slots}
    if norm_time not in valid_norm:
        return False, "Invalid timeslot for this location"
    return True, None

# simple audit logger
audit_logger = logging.getLogger("audit")
if not audit_logger.handlers:
    import os
    os.makedirs("logs", exist_ok=True)
    handler = logging.FileHandler("logs/audit.log")
    handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    audit_logger.addHandler(handler)
    audit_logger.setLevel(logging.INFO)

def log_booking_action(action, booking_id, user_id, details=None):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,  # CREATE / UPDATE / CANCEL / VIEW
        "booking_id": booking_id,
        "user_id": user_id,
        "ip_address": request.remote_addr,
        "user_agent": request.headers.get("User-Agent", ""),
        "details": details or {},
    }
    audit_logger.info(json.dumps(entry))

booking = Blueprint('booking', __name__, url_prefix='/booking')

def generate_booking_reference():
    """Generate a unique booking reference"""
    timestamp = datetime.now().strftime('%Y%m%d')
    unique_id = str(uuid.uuid4())[:8].upper()
    return f"SC-{timestamp}-{unique_id}"

def parse_booking_end_datetime(booking_date, time_slot):
    """
    Parse booking date and time slot to get the end datetime.
    Handles en-dash (–), em-dash (—), or hyphen (-).
    """
    try:
        sep = "–"
        if "—" in time_slot:
            sep = "—"
        elif "-" in time_slot:
            sep = "-"
        start_end = [p.strip() for p in time_slot.split(sep)]
        if len(start_end) != 2:
            # try fallback normalisation
            start_end = [p.strip() for p in _normalize_slot(time_slot).split(" – ")]
            if len(start_end) != 2:
                return None
        end_time = datetime.strptime(start_end[1], "%I:%M %p").time()
        return datetime.combine(booking_date, end_time)
    except (ValueError, IndexError, AttributeError):
        return None

def _parse_start_time_from_label(label: str):
    """Extract start time from 'H:MM AM – H:MM AM' (accepts –, —, or -)."""
    if not label:
        return None
    if "–" in label:
        sep = "–"
    elif "—" in label:
        sep = "—"
    elif "-" in label:
        sep = "-"
    else:
        return None
    start_str = label.split(sep)[0].strip()
    try:
        return datetime.strptime(start_str, "%I:%M %p").time()
    except ValueError:
        try:
            # last-ditch: normalise then parse
            start_norm = _normalize_slot(label).split(" – ")[0].strip()
            return datetime.strptime(start_norm, "%I:%M %p").time()
        except Exception:
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
@limiter.limit("5 per minute")  # Throttle brute-force attempts
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
            # basic input guardrails
            if location not in ALLOWED_LOCATIONS:
                return jsonify({'success': False, 'error': 'Invalid location'}), 400
            if booking_date < date.today():
                return jsonify({'success': False, 'error': 'Past date'}), 400
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

        # size limits (maps to PDF)
        ok, err = validate_input_sizes(request.form)
        if not ok:
            flash(err, 'error')
            return redirect(url_for('booking.booking_main'))

        # NEW: booking rules (valid location/date/slot)
        ok, err = validate_booking_rules(location, date_str, time_label)
        if not ok:
            flash(err, 'error')
            return redirect(url_for('booking.booking_main'))
        
        interest_group = request.form.get('interestGroup')
        activity_type = request.form.get('activityType')
        accessibility_help = request.form.get('accessibilityHelp')

        # Required fields (catch missing values clearly)
        if not all([
            location, date_str, time_label,
            event_title := request.form.get('eventTitle'),
            interest_group, activity_type,
            attendees := request.form.get('attendees'),
            organiser_name := request.form.get('organiserName'),
            organiser_email := request.form.get('organiserEmail'),
            organiser_phone := request.form.get('organiserPhone'),
            accessibility_help
        ]):
            flash('All required fields must be filled out.', 'error')
            return redirect(url_for('booking.booking_main'))

        # Optional: enforce strict dropdown/radio whitelists
        if ENFORCE_DROPDOWN_WHITELIST:
            if interest_group not in VALID_INTEREST_GROUPS:
                flash('Invalid interest group', 'error')
                return redirect(url_for('booking.booking_main'))
            if activity_type not in VALID_ACTIVITY_TYPES:
                flash('Invalid activity type', 'error')
                return redirect(url_for('booking.booking_main'))
            if accessibility_help not in {'Yes', 'No'}:
                flash('Invalid accessibility selection', 'error')
                return redirect(url_for('booking.booking_main'))

        
        # Event Details
        event_title = request.form.get('eventTitle')
        attendees = request.form.get('attendees')
        equipment = request.form.get('equipment', '').strip()
        description = request.form.get('description', '').strip()
        
        # Organiser
        organiser_name = request.form.get('organiserName')
        organiser_email = request.form.get('organiserEmail')
        organiser_phone = request.form.get('organiserPhone')
        
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
        log_booking_action('CREATE', new_booking.id, current_user.id, {
            "location": location,
            "date": date_str,
            "reference": reference_number
        })
        
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
@limiter.limit("10 per minute")  # Throttle brute-force attempts
def booking_manage():
    """Display user's bookings - both upcoming and past"""
    try:
        # CLEANUP: Update past bookings status first
        cleanup_past_bookings()
        
        now = datetime.now()
        today = date.today()
        
        # Get all user's bookings
        all_bookings = Booking.query.filter(
            Booking.booked_by_user_id == current_user.id
        ).all()
        
        upcoming_bookings = []
        past_bookings = []
        
        for booking_obj in all_bookings:
            # Parse the booking's end time to determine if it's truly past
            booking_end_datetime = parse_booking_end_datetime(booking_obj.booking_date, booking_obj.time_slot)
            
            if booking_obj.status == 'cancelled':
                # All cancelled bookings go to past regardless of date
                past_bookings.append(booking_obj)
            elif booking_end_datetime and booking_end_datetime < now:
                # Booking has ended - should already be marked as completed by cleanup
                past_bookings.append(booking_obj)
            elif booking_obj.booking_date >= today and booking_obj.status == 'confirmed':
                # Future booking that hasn't ended yet
                booking_obj.is_edit_locked = _is_within_24h(booking_obj)
                upcoming_bookings.append(booking_obj)
            else:
                # Fallback: if we can't parse the time, use date only
                if booking_obj.booking_date < today:
                    past_bookings.append(booking_obj)
                else:
                    booking_obj.is_edit_locked = _is_within_24h(booking_obj)
                    upcoming_bookings.append(booking_obj)
        
        # Sort bookings
        upcoming_bookings.sort(key=lambda b: (b.booking_date, b.time_slot))
        past_bookings.sort(key=lambda b: b.booking_date, reverse=True)
        
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

def cleanup_past_bookings():
    """Update status of bookings that have already ended"""
    try:
        now = datetime.now()
        
        # Get all confirmed bookings
        confirmed_bookings = Booking.query.filter_by(status='confirmed').all()
        
        updated_count = 0
        for booking in confirmed_bookings:
            booking_end_datetime = parse_booking_end_datetime(booking.booking_date, booking.time_slot)
            
            # If we can parse the datetime and it's in the past, mark as completed
            if booking_end_datetime and booking_end_datetime < now:
                booking.status = 'completed'
                updated_count += 1
                print(f"Updated booking {booking.reference_number} to completed")
            # Fallback: if we can't parse time, use date only
            elif not booking_end_datetime and booking.booking_date < now.date():
                booking.status = 'completed'
                updated_count += 1
                print(f"Updated booking {booking.reference_number} to completed (date only)")
        
        # Commit the changes
        if updated_count > 0:
            db.session.commit()
            print(f"Cleanup completed: {updated_count} bookings updated to completed status")
        
    except Exception as e:
        print(f"Error in cleanup_past_bookings: {str(e)}")
        db.session.rollback()
        # Don't raise the error - just log it so the main function continues
        pass

@booking.route('/get-booking/<booking_id>')
@login_required
@limiter.limit("5 per minute")  # Throttle brute-force attempts
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
        
        if not booking_obj:
            return jsonify({'success': False, 'error': 'Booking not found or cannot be edited'}), 404
        
        # Check if booking has already ended
        booking_end_datetime = parse_booking_end_datetime(booking_obj.booking_date, booking_obj.time_slot)
        if booking_end_datetime and booking_end_datetime < datetime.now():
            return jsonify({'success': False, 'error': 'Cannot edit a booking that has already ended'}), 400
        
        # Disallow edits for bookings starting within 24 hours
        if _is_within_24h(booking_obj):
            return jsonify({
                'success': False,
                'error': 'Bookings starting within the next 24 hours cannot be edited. You can only cancel.'
            }), 400
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['event_title', 'interest_group', 'activity_type', 
                         'expected_attendees', 'organiser_name', 'organiser_email', 
                         'organiser_phone', 'accessibility_help']
        
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
            
        # NEW: size limits (reusing names from create by adapting keys)
        fake_form = {
            'eventTitle': data.get('event_title',''),
            'description': data.get('event_description',''),
            'equipment': data.get('equipment_required',''),
            'organiserName': data.get('organiser_name',''),
            'organiserEmail': data.get('organiser_email',''),
            'organiserPhone': data.get('organiser_phone',''),
            'attendees': str(data.get('expected_attendees','')),
        }
        ok, err = validate_input_sizes(fake_form)
        if not ok:
            return jsonify({'success': False, 'error': err}), 400

        # Still require values:
        if not all([data.get('interest_group'), data.get('activity_type'), data.get('accessibility_help')]):
            return jsonify({'success': False, 'error': 'interest_group, activity_type, and accessibility_help are required'}), 400

        # Optional strict enforcement
        if ENFORCE_DROPDOWN_WHITELIST:
            if data.get('interest_group') not in VALID_INTEREST_GROUPS:
                return jsonify({'success': False, 'error': 'Invalid interest group'}), 400
            if data.get('activity_type') not in VALID_ACTIVITY_TYPES:
                return jsonify({'success': False, 'error': 'Invalid activity type'}), 400
            if data.get('accessibility_help') not in {'Yes','No'}:
                return jsonify({'success': False, 'error': 'Invalid accessibility selection'}), 400
        
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

        valid_slots = TIME_SLOTS_BY_LOCATION.get(booking_obj.location, [])
        if not any(s['label'] == new_time_slot for s in valid_slots):
            return jsonify({'success': False, 'error': 'Invalid timeslot for this location'}), 400

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
        log_booking_action('UPDATE', booking_obj.id, current_user.id, {"changes": data})

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
        
        # Check if booking has already ended
        booking_end_datetime = parse_booking_end_datetime(booking_obj.booking_date, booking_obj.time_slot)
        if booking_end_datetime and booking_end_datetime < datetime.now():
            return jsonify({'success': False, 'error': 'Cannot cancel a booking that has already ended'}), 400
        
        # Check if booking is in the future (fallback check using date only)
        if booking_obj.booking_date < date.today():
            return jsonify({'success': False, 'error': 'Cannot cancel past bookings'}), 400
        
        booking_obj.status = 'cancelled'
        booking_obj.updated_at = datetime.utcnow()
        
        db.session.commit()
        log_booking_action('CANCEL', booking_obj.id, current_user.id)
        
        return jsonify({'success': True, 'message': 'Booking cancelled successfully'})
        
    except Exception as e:
        print(f"Error cancelling booking: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Internal server error'}), 500