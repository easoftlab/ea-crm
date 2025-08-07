from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response, current_app, session
from flask_login import login_required, current_user
from .forms import LeadForm
from .auth import permission_required
from .models import db, Lead, Contact, ContactPhone, ContactEmail, SocialProfile, ScrapedLead, User, UserActivity, UserDailyStats, UserWeeklyStats, UserMonthlyStats, UserTask, Projection, ConvertedClient, ConvertedClientProjection, LeadProjection, ProductionTask, TaskAttachment, DropboxUpload, LANServerFile, Role, ApplicationUsage, DetailedApplicationUsage, MouseKeyboardActivity, ProductivityReport, WebsiteVisit, BrowserActivity, ProductionActivity, DesktopActivity
from .ai.lead_scoring import score_lead, extract_lead_features
from .ai.intent_detection import detect_intent

from sqlalchemy import func, or_, extract, case
from datetime import datetime, date, timedelta
from collections import defaultdict
import re
from flask_wtf.csrf import validate_csrf, CSRFError
from flask_wtf import csrf
import io
from flask import send_file
from statistics import mean, median
import threading
from .scraper import LinkedInScraper
import pandas as pd
import os
from werkzeug.utils import secure_filename
import dateutil.parser

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

scraper_thread = None
scraper_instance = None
scraper_lock = threading.Lock()

def safe_date(val):
    if val is None:
        return ''
    if isinstance(val, str):
        return val
    if isinstance(val, datetime):
        return val.strftime('%Y-%m-%d')
    try:
        return str(val)
    except Exception:
        return ''

bp = Blueprint('main', __name__)

def sentence_case(text):
    if not text:
        return ''
    # Split into sentences, capitalize first letter of each, lower the rest
    sentences = re.split(r'([.!?]\s+)', text.strip())
    result = ''
    for i in range(0, len(sentences), 2):
        sentence = sentences[i].strip()
        sep = sentences[i+1] if i+1 < len(sentences) else ''
        if sentence:
            sentence = sentence[0].upper() + sentence[1:].lower() if len(sentence) > 1 else sentence.upper()
            result += sentence + sep
    return result.strip()

def get_states_by_timezone(timezone):
    """Return list of states that belong to the specified timezone."""
    timezone_states = {
        'EST': [
            'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Indiana', 'Kentucky', 
            'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'New Hampshire', 
            'New Jersey', 'New York', 'North Carolina', 'Ohio', 'Pennsylvania', 
            'Rhode Island', 'South Carolina', 'Tennessee', 'Vermont', 'Virginia', 
            'West Virginia', 'District of Columbia'
        ],
        'CST': [
            'Alabama', 'Arkansas', 'Illinois', 'Iowa', 'Kansas', 'Louisiana', 
            'Minnesota', 'Mississippi', 'Missouri', 'Nebraska', 'North Dakota', 
            'Oklahoma', 'South Dakota', 'Texas', 'Wisconsin'
        ],
        'MST': [
            'Arizona', 'Colorado', 'Idaho', 'Montana', 'New Mexico', 'Utah', 'Wyoming'
        ],
        'PST': [
            'California', 'Nevada', 'Oregon', 'Washington'
        ],
        'AKST': [
            'Alaska'
        ],
        'HST': [
            'Hawaii'
        ]
    }
    return timezone_states.get(timezone, [])

def apply_lead_filters(query):
    """Apply filters from request.args to a Lead query."""
    from_date = request.args.get('from')
    to_date = request.args.get('to')
    status = request.args.get('status')
    industry = request.args.get('industry')
    country = request.args.get('country')
    if from_date:
        query = query.filter(Lead.created_at >= from_date)
    if to_date:
        query = query.filter(Lead.created_at <= to_date + ' 23:59:59')
    if status:
        query = query.filter(Lead.status == status)
    if industry:
        query = query.filter(Lead.industry.ilike(f'%{industry}%'))
    if country:
        query = query.filter(Lead.country.ilike(f'%{country}%'))
    return query

@bp.route('/add', methods=['GET', 'POST'])
@login_required
@permission_required('add_leads')
def add_lead():
    form = LeadForm()
    # Static lists
    us_states = [
        'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut', 'Delaware',
        'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky',
        'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota', 'Mississippi',
        'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey', 'New Mexico',
        'New York', 'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania',
        'Rhode Island', 'South Carolina', 'South Dakota', 'Tennessee', 'Texas', 'Utah', 'Vermont',
        'Virginia', 'Washington', 'West Virginia', 'Wisconsin', 'Wyoming'
    ]
    industries_full = [
        'E-commerce / Online Retail',
        'Fashion & Apparel',
        'Jewelry & Luxury Goods',
        'Real Estate',
        'Photography Studios',
        'Wedding & Event Photographers',
        'Advertising & Creative Agencies',
        'Marketing Firms',
        'Magazine & Publishing Houses',
        'Automotive Dealerships',
        'Furniture & Home Decor Brands',
        'Cosmetics & Skincare Brands',
        'Modeling Agencies',
        'Printing & Packaging Companies',
        'Product Manufacturers',
        'Auction Houses',
        'Food & Beverage Brands',
        'Eyewear & Accessories Brands',
        'Stock Photography Agencies',
        'Electronics & Gadgets Retailers'
    ]
    sources_full = [
        'Website', 'Referral', 'Social Media', 'Email Campaign', 'Phone Call', 'Walk-in', 'Event', 'Other'
    ]
    top_countries = ['UK', 'USA', 'Australia']
    europe_countries = [
        'Albania', 'Andorra', 'Armenia', 'Austria', 'Azerbaijan', 'Belarus', 'Belgium', 'Bosnia and Herzegovina', 'Bulgaria',
        'Croatia', 'Cyprus', 'Czech Republic', 'Denmark', 'Estonia', 'Finland', 'France', 'Georgia', 'Germany', 'Greece',
        'Hungary', 'Iceland', 'Ireland', 'Italy', 'Kazakhstan', 'Kosovo', 'Latvia', 'Liechtenstein', 'Lithuania', 'Luxembourg',
        'Malta', 'Moldova', 'Monaco', 'Montenegro', 'Netherlands', 'North Macedonia', 'Norway', 'Poland', 'Portugal',
        'Romania', 'Russia', 'San Marino', 'Serbia', 'Slovakia', 'Slovenia', 'Spain', 'Sweden', 'Switzerland', 'Turkey',
        'Ukraine', 'Vatican City'
    ]
    # Remove top_countries from europe_countries if present
    europe_countries = [c for c in europe_countries if c not in top_countries]
    country_full = top_countries + sorted(europe_countries)
    # Dynamic lists from DB
    industries = sorted(set(industries_full + [row[0] for row in db.session.query(Lead.industry).distinct().filter(Lead.industry != None).all() if row[0]]), key=lambda x: industries_full.index(x) if x in industries_full else (len(industries_full) + 1))
    countries = country_full
    states = sorted(set(us_states + [row[0] for row in db.session.query(Lead.state).distinct().filter(Lead.state != None).all() if row[0]]))
    sources = sorted(set(sources_full + [row[0] for row in db.session.query(Lead.source).distinct().filter(Lead.source != None).all() if row[0]]))
    # Static US timezones
    timezones = ['EST', 'CST', 'MST', 'PST', 'AKST', 'HST']
    if form.validate_on_submit():
        # Standardize company name to proper case
        company_name = form.company_name.data.title() if form.company_name.data else ''
        # Standardize notes to sentence case
        notes = sentence_case(form.notes.data) if form.notes.data else ''
        lead = Lead(
            company_name=company_name,
            company_website=form.company_website.data,
            country=form.country.data,
            state=form.state.data,
            industry=form.industry.data,
            source=form.source.data,
            notes=notes,
            timezone=form.timezone.data,
        )
        db.session.add(lead)
        db.session.flush()  # Get lead.id before commit
        # Parse contacts_json
        import json
        contacts_json = request.form.get('contacts_json')
        if contacts_json:
            try:
                contacts = json.loads(contacts_json)
                for c in contacts:
                    name = c.get('name', '').title()
                    position = c.get('position', '')
                    contact = Contact(name=name, position=position, lead_id=lead.id)
                    db.session.add(contact)
                    # Phones
                    for phone in c.get('phones', []):
                        if phone:
                            db.session.add(ContactPhone(phone=phone, contact=contact))
                    # Emails
                    for email in c.get('emails', []):
                        if email:
                            db.session.add(ContactEmail(email=email.lower(), contact=contact))
                    # Socials
                    for social in c.get('socials', []):
                        url = social.get('url', '')
                        stype = social.get('type', '')
                        if url:
                            db.session.add(SocialProfile(url=url, type=stype, contact=contact))
            except Exception as e:
                print('Error parsing contacts_json:', e)
        db.session.commit()
        flash('Lead saved!', 'success')
        return redirect(url_for('main.add_lead'))
    return render_template('add_lead.html', form=form, industries=industries, countries=countries, states=states, sources=sources, timezones=timezones)

@bp.route('/')
@login_required
def dashboard():
    # Admin users have access to everything
    if current_user.has_permission('admin'):
        return dashboard_content()
    
    # Check if user is Production role (has view_tasks permission)
    if current_user.has_permission('view_tasks'):
        # Production users should be redirected to their dashboard
        return redirect(url_for('production.dashboard'))
    
    # Check if user is Lead Generator (only has add_leads permission)
    if current_user.has_permission('add_leads') and not current_user.has_permission('manage_leads'):
        # Lead Generator should see the add-only dashboard
        return render_template('add_only_dashboard.html')
    
    # For other users, require manage_leads permission
    if not current_user.has_permission('manage_leads'):
        flash('You need manage_leads permissions to access this page.', 'error')
        return redirect(url_for('auth.login'))
    
    return dashboard_content()

def dashboard_content():
    # Get filter parameters from query string
    status = request.args.get('status', '').strip()
    country = request.args.get('country', '').strip()
    industry = request.args.get('industry', '').strip()
    timezone = request.args.get('timezone', '').strip()
    search = request.args.get('search', '').strip()
    followup_range = request.args.get('followup_range', '').strip()
    updated_today = request.args.get('updated_today', '').strip()
    created_today = request.args.get('created_today', '').strip()
    today = date.today()  # <-- Ensure this is before any use of 'today'
    # Build query
    query = Lead.query
    if updated_today:
        # Show leads that were updated today (today's calls) - no status restriction
        query = query.filter(func.date(Lead.updated_at) == today)
    elif created_today:
        # Show leads that were created today
        query = query.filter(func.date(Lead.created_at) == created_today)
    elif status:
        query = query.filter(Lead.status == status)
    else:
        # Only show 'New' leads by default if no specific status filter is set
        query = query.filter(Lead.status == 'New')
    if country:
        query = query.filter(Lead.country.ilike(f'%{country}%'))
    if industry:
        query = query.filter(Lead.industry.ilike(f'%{industry}%'))
    if timezone:
        # Filter by states that belong to the selected timezone
        states_in_timezone = get_states_by_timezone(timezone)
        if states_in_timezone:
            query = query.filter(Lead.state.in_(states_in_timezone))
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            Lead.company_name.ilike(search_pattern) |
            Lead.notes.ilike(search_pattern) |
            Lead.state.ilike(search_pattern) |
            Lead.country.ilike(search_pattern) |
            Lead.status.ilike(search_pattern)
        )
    if followup_range:
        # Only show leads with a real followup_date and status 'Follow Up'
        query = query.filter(
            Lead.followup_date != None,
            Lead.followup_date != '',
            Lead.followup_date != '-',
            Lead.status == 'Follow Up'
        )
        # If followup_range is 'pending' or empty, show only today's follow-ups
        if followup_range == "pending" or followup_range == "":
            # Only show leads with followup_date == today
            query = query.filter(Lead.followup_date == today)
            # Set followup_range to today for template logic
            followup_range = f"{today.strftime('%Y-%m-%d')},{today.strftime('%Y-%m-%d')}"
        else:
            # Parse followup_range (format: "YYYY-MM-DD,YYYY-MM-DD")
            try:
                start_date_str, end_date_str = followup_range.split(',')
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                query = query.filter(
                    Lead.followup_date >= start_date,
                    Lead.followup_date <= end_date
                )
            except (ValueError, AttributeError):
                # If parsing fails, ignore the filter
                pass
    leads = query.order_by(Lead.created_at.desc()).all()
    new_leads_today = Lead.query.filter(func.date(Lead.created_at) == today).count()
    # Calculate follow_ups_due for current week + any untouched follow-ups from previous weeks
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    # Get current week follow-ups
    current_week_followups = Lead.query.filter(
        Lead.followup_date != None,
        Lead.followup_date >= week_start,
        Lead.followup_date <= week_end
    ).count()
    
    # Get untouched follow-ups from previous weeks (leads that haven't been updated recently)
    # Consider a lead "untouched" if it hasn't been updated in the last 7 days
    untouched_cutoff = today - timedelta(days=7)
    untouched_previous_followups = Lead.query.filter(
        Lead.followup_date != None,
        Lead.followup_date < week_start,  # Previous weeks
        Lead.updated_at <= untouched_cutoff  # Not recently updated
    ).count()
    
    follow_ups_due = current_week_followups + untouched_previous_followups
    if not follow_ups_due:
        follow_ups_due = 0
    converted = Lead.query.filter(Lead.status == 'Converted').count() if hasattr(Lead, 'status') else 0
    interested = Lead.query.filter(Lead.status == 'Interested').count() if hasattr(Lead, 'status') else 0
    
    # Count today's calls (leads that had status changes today)
    today_calls = Lead.query.filter(
        func.date(Lead.updated_at) == today,
        Lead.status != 'New'  # Exclude leads that are still 'New'
    ).count()
    # Total Remain Leads: All leads with status 'New'
    total_remain_leads = Lead.query.filter(Lead.status == 'New').count()
    print(f"DEBUG: Dashboard counts - Converted: {converted}, Today Calls: {today_calls}, Interested: {interested}")
    # Datalists for filters
    industries = [row[0] for row in db.session.query(Lead.industry).distinct().filter(Lead.industry != None).order_by(Lead.industry).all() if row[0]]
    countries = [row[0] for row in db.session.query(Lead.country).distinct().filter(Lead.country != None).order_by(Lead.country).all() if row[0]]
    states = [row[0] for row in db.session.query(Lead.state).distinct().filter(Lead.state != None).order_by(Lead.state).all() if row[0]]
    # Remove any query for Lead.timezone and use static list
    timezones = ['EST', 'CST', 'MST', 'PST', 'AKST', 'HST']
    statuses = [row[0] for row in db.session.query(Lead.status).distinct().filter(Lead.status != None).order_by(Lead.status).all() if row[0]] if hasattr(Lead, 'status') else []
    # Check if user's profile is complete
    profile_complete = current_user.is_profile_complete()
    missing_profile_fields = current_user.get_missing_profile_fields()
    
    response = make_response(render_template('dashboard.html', 
        leads=leads, 
        new_leads_today=new_leads_today, 
        follow_ups_due=follow_ups_due, 
        converted=converted, 
        today_calls=today_calls, 
        interested=interested, 
        status=status, 
        country=country, 
        industry=industry, 
        timezone=timezone, 
        search=search, 
        followup_range=followup_range, 
        industries=industries, 
        countries=countries, 
        states=states, 
        timezones=timezones, 
        statuses=statuses, 
        today=today,
        total_remain_leads=total_remain_leads,
        profile_complete=profile_complete,
        missing_profile_fields=missing_profile_fields
    ))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@bp.route('/ajax_search_leads', methods=['GET'])
@login_required
@permission_required('manage_leads')
def ajax_search_leads():
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '')
    country = request.args.get('country', '')
    industry = request.args.get('industry', '')
    timezone = request.args.get('timezone', '')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    followup_range = request.args.get('followup_range', '').strip()
    updated_today = request.args.get('updated_today', '').strip()
    created_today = request.args.get('created_today', '').strip()
    today = date.today()
    query = Lead.query
    # Apply filters
    if updated_today:
        # Show leads that were updated today (today's calls) - no status restriction
        query = query.filter(func.date(Lead.updated_at) == today)
    elif created_today:
        # Show leads that were created today
        query = query.filter(func.date(Lead.created_at) == created_today)
    elif status:
        query = query.filter(Lead.status == status)
    elif not followup_range:
        # Only show 'New' leads by default if no specific status filter is set AND no followup_range
        query = query.filter(Lead.status == 'New')
    if country:
        query = query.filter(Lead.country == country)
    if industry:
        query = query.filter(Lead.industry == industry)
    if timezone:
        # Filter by states that belong to the selected timezone
        states_in_timezone = get_states_by_timezone(timezone)
        if states_in_timezone:
            query = query.filter(Lead.state.in_(states_in_timezone))
    if search:
        query = query.filter(
            Lead.company_name.ilike(f'%{search}%') |
            Lead.notes.ilike(f'%{search}%') |
            Lead.state.ilike(f'%{search}%') |
            Lead.country.ilike(f'%{search}%') |
            Lead.status.ilike(f'%{search}%')
        )
    # Add followup_range filter logic
    if followup_range:
        query = query.filter(
            Lead.followup_date != None,
            Lead.followup_date != '',
            Lead.followup_date != '-'
        )
        if followup_range == 'pending' or followup_range == '':
            query = query.filter(Lead.followup_date == today)
        else:
            try:
                start_date_str, end_date_str = followup_range.split(',')
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                query = query.filter(
                    Lead.followup_date >= start_date,
                    Lead.followup_date <= end_date
                )
            except (ValueError, AttributeError):
                pass
    total = query.count()
    leads = query.order_by(Lead.created_at.desc()).offset((page-1)*per_page).limit(per_page).all()
    def contact_dict(contact):
        return {
            'name': contact.name,
            'position': contact.position,
            'phones': [p.phone for p in contact.phones],
            'emails': [e.email for e in contact.emails],
            'socials': [{'url': s.url, 'type': s.type} for s in contact.socials]
        }
    leads_json = [
        {
            'id': lead.id,
            'company_name': lead.company_name,
            'company_website': lead.company_website,
            'country': lead.country,
            'state': lead.state,
            'industry': lead.industry,
            'source': lead.source,
            'notes': lead.notes,
            'status': lead.status,
            'followup_date': safe_date(lead.followup_date),
            'contacts': [contact_dict(c) for c in lead.contacts],
            'created_at': safe_date(lead.created_at),
            'updated_at': safe_date(lead.updated_at),
            'followup_history': [
                {
                    'number': history.followup_number,
                    'date': safe_date(history.followup_date),
                    'status': history.status_at_followup or 'Unknown',
                    'created_at': safe_date(history.created_at)
                }
                for history in lead.followup_history
            ] if lead.followup_history and len(lead.followup_history) > 0 else None
        }
        for lead in leads
    ]
    return jsonify({'leads': leads_json, 'total': total, 'page': page, 'per_page': per_page})

@bp.route('/ajax_search_converted', methods=['GET'])
@login_required
@permission_required('manage_leads')
def ajax_search_converted():
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '')
    country = request.args.get('country', '')
    industry = request.args.get('industry', '')
    timezone = request.args.get('timezone', '')
    converted_statuses = ['Converted', 'On Board Clients']
    query = Lead.query.filter(Lead.status.in_(converted_statuses))
    if status:
        query = query.filter(Lead.status == status)
    if country:
        query = query.filter(Lead.country == country)
    if industry:
        query = query.filter(Lead.industry == industry)
    if timezone:
        query = query.filter(Lead.timezone == timezone)
    if search:
        query = query.filter(
            Lead.company_name.ilike(f'%{search}%') |
            Lead.notes.ilike(f'%{search}%')
        )
    leads = query.order_by(Lead.created_at.desc()).all()
    def contact_dict(contact):
        return {
            'name': contact.name,
            'position': contact.position,
            'phones': [p.phone for p in contact.phones],
            'emails': [e.email for e in contact.emails],
            'socials': [{'url': s.url, 'type': s.type} for s in contact.socials]
        }
    leads_json = [
        {
            'id': lead.id,
            'company_name': lead.company_name,
            'company_website': lead.company_website,
            'country': lead.country,
            'state': lead.state,
            'industry': lead.industry,
            'source': lead.source,
            'notes': lead.notes,
            'status': lead.status,
            'followup_date': safe_date(lead.followup_date),
            'timezone': lead.timezone,
            'created_at': safe_date(lead.created_at),
            'updated_at': safe_date(lead.updated_at),
            'contacts': [contact_dict(c) for c in lead.contacts]
        }
        for lead in leads
    ]
    return jsonify({'leads': leads_json})

@bp.route('/lead/<int:lead_id>', methods=['GET'])
@login_required
@permission_required('manage_leads')
def get_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    return jsonify({
        'id': lead.id,
        'company_name': lead.company_name,
        'status': lead.status or '',
        'notes': lead.notes or ''
    })

@bp.route('/lead/<int:lead_id>/edit', methods=['POST'])
@login_required
@permission_required('manage_leads')
def edit_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    status = request.form.get('status', '').strip()
    notes = request.form.get('notes', '').strip()
    lead.status = status
    lead.notes = notes
    db.session.commit()
    flash('Lead updated!', 'success')
    return redirect(url_for('main.dashboard'))

@bp.route('/update_lead', methods=['POST'])
@login_required
@permission_required('manage_leads')
def update_lead():
    try:
        csrf_token = request.form.get('csrf_token')
        validate_csrf(csrf_token)
    except CSRFError:
        response = jsonify({'success': False, 'error': 'CSRF token missing or invalid.'})
        response.headers['Content-Type'] = 'application/json'
        return response, 400
    lead_id = request.form.get('lead_id')
    status = request.form.get('status')
    followup_date = request.form.get('followup_date')
    notes = request.form.get('notes')
    if not lead_id:
        response = jsonify({'success': False, 'error': 'Missing lead_id.'})
        response.headers['Content-Type'] = 'application/json'
        return response, 400
    from .models import Lead, FollowUpHistory
    lead = Lead.query.get(lead_id)
    if not lead:
        response = jsonify({'success': False, 'error': 'Lead not found.'})
        response.headers['Content-Type'] = 'application/json'
        return response, 404
    
    # Handle follow-up history
    if followup_date and followup_date.strip():
        try:
            new_followup_date = datetime.strptime(followup_date, '%Y-%m-%d').date()
            
            # Check if this is a new follow-up (different from current)
            if not lead.followup_date or new_followup_date != lead.followup_date:
                # If there was a previous follow-up date, save it to history first
                if lead.followup_date:
                    # Get the next follow-up number
                    existing_followups = FollowUpHistory.query.filter_by(lead_id=lead_id).count()
                    next_followup_number = existing_followups + 1
                    
                    # Save the OLD follow-up date to history with current status
                    old_followup = FollowUpHistory(
                        lead_id=lead_id,
                        followup_number=next_followup_number,
                        followup_date=lead.followup_date,
                        status_at_followup=lead.status  # Save the status at this follow-up
                    )
                    db.session.add(old_followup)
                
                # Update the lead's current follow-up date to the new one
                lead.followup_date = new_followup_date
        except Exception as e:
            # If date parsing fails, set to None
            lead.followup_date = None
    else:
        lead.followup_date = None
    
    if status:
        lead.status = status
    if notes is not None:
        lead.notes = notes
    
    db.session.commit()
    
    # Get follow-up history for response
    followup_history = []
    for history in lead.followup_history:
        followup_history.append({
            'number': history.followup_number,
            'date': history.followup_date.strftime('%Y-%m-%d'),
            'status': history.status_at_followup or 'Unknown',
            'created_at': history.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    response_data = {
        'success': True, 
        'status': lead.status, 
        'followup_date': lead.followup_date.strftime('%Y-%m-%d') if lead.followup_date else None, 
        'notes': lead.notes
    }
    
    # Only include followup_history if there's actual history
    if followup_history:
        response_data['followup_history'] = followup_history
    
    response = jsonify(response_data)
    response.headers['Content-Type'] = 'application/json'
    return response

@bp.route('/delete_lead', methods=['POST'])
@login_required
@permission_required('admin')
def delete_lead():
    from flask import request
    try:
        # Handle CSRF validation for both form data and JSON
        if request.is_json:
            data = request.get_json()
            csrf_token = data.get('csrf_token')
        else:
            csrf_token = request.form.get('csrf_token')
        validate_csrf(csrf_token)
    except CSRFError:
        response = jsonify({'success': False, 'error': 'CSRF token missing or invalid.'})
        response.headers['Content-Type'] = 'application/json'
        return response, 400
    
    if request.is_json:
        data = request.get_json()
        if data.get('delete_all'):
            Lead.query.delete()
            db.session.commit()
            return jsonify({'success': True, 'deleted': 'all'})
        lead_ids = data.get('lead_ids')
        if lead_ids:
            Lead.query.filter(Lead.id.in_(lead_ids)).delete(synchronize_session=False)
            db.session.commit()
            return jsonify({'success': True, 'deleted': lead_ids})
    # Fallback: single-lead deletion (legacy)
    lead_id = request.form.get('lead_id') or request.args.get('lead_id')
    if not lead_id:
        return jsonify({'success': False, 'error': 'No lead_id provided.'}), 400
    lead = Lead.query.get(lead_id)
    if not lead:
        return jsonify({'success': False, 'error': 'Lead not found.'}), 404
    db.session.delete(lead)
    db.session.commit()
    return jsonify({'success': True, 'deleted': [lead_id]})

@bp.route('/reports')
@login_required
@permission_required('view_reports')
def reports():
    # Callers should not access reports
    if current_user.role.name == 'Caller':
        flash('Callers cannot access reports. Please use your dashboard.', 'error')
        return redirect(url_for('main.personal_dashboard'))
    # Daily, weekly, monthly stats by status
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    # Helper to count by status
    def count_by_status(query):
        stats = defaultdict(int)
        for lead in query:
            stats[lead.status or 'Unknown'] += 1
        return stats
    # Daily
    daily_leads = Lead.query.filter(func.date(Lead.created_at) == today).all()
    daily_stats = count_by_status(daily_leads)
    # Weekly
    weekly_leads = Lead.query.filter(Lead.created_at >= week_start).all()
    weekly_stats = count_by_status(weekly_leads)
    # Monthly
    monthly_leads = Lead.query.filter(Lead.created_at >= month_start).all()
    monthly_stats = count_by_status(monthly_leads)
    return render_template('reports.html', daily_stats=daily_stats, weekly_stats=weekly_stats, monthly_stats=monthly_stats)

@bp.route('/converted')
@login_required
@permission_required('manage_leads')
def converted_clients():
    # Filtering parameters
    search = request.args.get('search', '').strip()
    industry = request.args.get('industry', '').strip()
    country = request.args.get('country', '').strip()

    # Build base query for converted statuses
    converted_statuses = ['Converted', 'On Board Clients']
    query = Lead.query.filter(Lead.status.in_(converted_statuses))

    # Apply search filter (name, company, email, phone)
    if search:
        search_like = f"%{search}%"
        query = query.filter(
            or_(
                Lead.company_name.ilike(search_like)
            )
        )
    # Apply industry filter
    if industry:
        query = query.filter(Lead.industry == industry)
    # Apply country filter
    if country:
        query = query.filter(Lead.country == country)

    leads = query.order_by(Lead.created_at.desc()).all()

    # Eager load contacts, phones, emails, socials for each lead
    leads_with_contacts = []
    for lead in leads:
        contacts = []
        for contact in lead.contacts:
            contacts.append({
                'name': contact.name,
                'position': contact.position,
                'phones': [p.phone for p in contact.phones],
                'emails': [e.email for e in contact.emails],
                'socials': [{'url': s.url, 'type': s.type} for s in contact.socials]
            })
        leads_with_contacts.append({
            'id': lead.id,
            'company_name': lead.company_name,
            'company_website': lead.company_website,
            'country': lead.country,
            'state': lead.state,
            'industry': lead.industry,
            'source': lead.source,
            'notes': lead.notes,
            'status': lead.status,
            'followup_date': safe_date(lead.followup_date),
            'timezone': lead.timezone,
            'created_at': safe_date(lead.created_at),
            'updated_at': safe_date(lead.updated_at),
            'contacts': contacts
        })

    # Total converted (all time, not filtered)
    total_converted = Lead.query.filter(Lead.status.in_(converted_statuses)).count()
    # Total leads (for conversion rate)
    total_leads = Lead.query.count()
    conversion_rate = round((total_converted / total_leads * 100), 1) if total_leads else 0
    # Recent conversions (this week, not filtered)
    from datetime import date, timedelta
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    recent_conversions = Lead.query.filter(
        Lead.status.in_(converted_statuses),
        Lead.created_at >= week_start
    ).count()

    # Get industries and countries for dropdowns
    industries = [row[0] for row in db.session.query(Lead.industry).distinct().filter(Lead.industry != None).order_by(Lead.industry).all() if row[0]]
    countries = [row[0] for row in db.session.query(Lead.country).distinct().filter(Lead.country != None).order_by(Lead.country).all() if row[0]]

    return render_template(
        'converted_clients.html',
        leads=leads_with_contacts,
        total_converted=total_converted,
        conversion_rate=conversion_rate,
        recent_conversions=recent_conversions,
        industries=industries,
        countries=countries
    )

@bp.route('/converted_personal')
@login_required
@permission_required('manage_leads')
def personal_converted_clients():
    """Personal converted clients dashboard for individual users"""
    # Filtering parameters
    search = request.args.get('search', '').strip()
    industry = request.args.get('industry', '').strip()
    country = request.args.get('country', '').strip()

    # Build base query for converted statuses - ONLY user's own leads
    converted_statuses = ['Converted', 'On Board Clients']
    query = Lead.query.filter(
        Lead.status.in_(converted_statuses),
        Lead.created_by == current_user.id  # Only user's own leads
    )

    # Apply search filter (name, company, email, phone)
    if search:
        search_like = f"%{search}%"
        query = query.filter(
            or_(
                Lead.company_name.ilike(search_like)
            )
        )
    # Apply industry filter
    if industry:
        query = query.filter(Lead.industry == industry)
    # Apply country filter
    if country:
        query = query.filter(Lead.country == country)

    leads = query.order_by(Lead.created_at.desc()).all()

    # Eager load contacts, phones, emails, socials for each lead
    leads_with_contacts = []
    for lead in leads:
        contacts = []
        for contact in lead.contacts:
            contacts.append({
                'name': contact.name,
                'position': contact.position,
                'phones': [p.phone for p in contact.phones],
                'emails': [e.email for e in contact.emails],
                'socials': [{'url': s.url, 'type': s.type} for s in contact.socials]
            })
        leads_with_contacts.append({
            'id': lead.id,
            'company_name': lead.company_name,
            'company_website': lead.company_website,
            'country': lead.country,
            'state': lead.state,
            'industry': lead.industry,
            'source': lead.source,
            'notes': lead.notes,
            'status': lead.status,
            'followup_date': safe_date(lead.followup_date),
            'timezone': lead.timezone,
            'created_at': safe_date(lead.created_at),
            'updated_at': safe_date(lead.updated_at),
            'contacts': contacts
        })

    # Personal converted stats (only user's own leads)
    total_converted = Lead.query.filter(
        Lead.status.in_(converted_statuses),
        Lead.created_by == current_user.id
    ).count()
    
    # Total user's leads (for personal conversion rate)
    total_user_leads = Lead.query.filter(Lead.created_by == current_user.id).count()
    conversion_rate = round((total_converted / total_user_leads * 100), 1) if total_user_leads else 0
    
    # Recent conversions (this week, only user's own)
    from datetime import date, timedelta
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    recent_conversions = Lead.query.filter(
        Lead.status.in_(converted_statuses),
        Lead.created_by == current_user.id,
        Lead.created_at >= week_start
    ).count()

    # Get industries and countries for dropdowns (only from user's leads)
    industries = [row[0] for row in db.session.query(Lead.industry).filter(
        Lead.created_by == current_user.id,
        Lead.industry != None
    ).distinct().order_by(Lead.industry).all() if row[0]]
    
    countries = [row[0] for row in db.session.query(Lead.country).filter(
        Lead.created_by == current_user.id,
        Lead.country != None
    ).distinct().order_by(Lead.country).all() if row[0]]

    return render_template(
        'converted_clients_personal.html',
        leads=leads_with_contacts,
        total_converted=total_converted,
        conversion_rate=conversion_rate,
        recent_conversions=recent_conversions,
        industries=industries,
        countries=countries,
        user=current_user
    )

@bp.route('/scraper', methods=['GET'])
@login_required
@permission_required('manage_scraper')
def scraper():
    scraped_leads = ScrapedLead.query.all()
    for lead in scraped_leads:
        lead_dict = {
            'company_name': lead.company_name,
            'key_person': getattr(lead, 'key_person', ''),
            'about': getattr(lead, 'about', ''),
            'recent_post': getattr(lead, 'recent_post', ''),
            'seniority': getattr(lead, 'seniority', 'Unknown'),
            'department': getattr(lead, 'department', 'Unknown'),
            'company_size': getattr(lead, 'company_size', 0),
            'industry': getattr(lead, 'industry', 'Unknown'),
            'activity_level': getattr(lead, 'activity_level', 0),
            'intent_score': 0
        }
        intent_score, intent_tags = detect_intent(lead_dict['about'])
        lead.intent_score = intent_score
        lead.intent_tags = intent_tags
        try:
            lead.lead_score = score_lead(lead_dict)
        except Exception:
            lead.lead_score = 0
    return render_template('scraper.html', scraped_leads=scraped_leads)

@bp.route('/scraper/log_reply', methods=['POST'])
@login_required
@permission_required('manage_scraper')
def log_scraper_reply():
    lead_id = request.form.get('lead_id')
    reply = request.form.get('reply')
    lead = ScrapedLead.query.get(lead_id)
    if lead:
        lead.message_reply = reply
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Lead not found'})

# --- REPORTING API ENDPOINTS ---
@bp.route('/api/reports/test')
@login_required
def api_reports_test():
    print("API test endpoint called!")
    print(f"Current user: {current_user.username if current_user.is_authenticated else 'Not authenticated'}")
    print(f"User role: {current_user.role.name if current_user.is_authenticated and current_user.role else 'No role'}")
    print(f"User permissions: {current_user.role.permissions if current_user.is_authenticated and current_user.role else 'No permissions'}")
    return jsonify({
        'message': 'Reports API is working', 
        'timestamp': datetime.now().isoformat(),
        'user': current_user.username if current_user.is_authenticated else 'Not authenticated',
        'role': current_user.role.name if current_user.is_authenticated and current_user.role else 'No role',
        'permissions': current_user.role.permissions if current_user.is_authenticated and current_user.role else 'No permissions'
    })

@bp.route('/api/reports/summary')
@login_required
def api_reports_summary():
    print(f"=== API SUMMARY DEBUG ===")
    print(f"Request method: {request.method}")
    print(f"Request headers: {dict(request.headers)}")
    print(f"Request cookies: {dict(request.cookies)}")
    # print(f"Session data: {dict(session)}")  # Commented out to avoid session import conflict
    print(f"Current user: {current_user.username if current_user.is_authenticated else 'Not authenticated'}")
    print(f"User ID: {current_user.id if current_user.is_authenticated else 'None'}")
    print(f"========================")
    try:
        # Check if there are any leads in the database
        all_leads_count = Lead.query.count()
        print(f"Total leads in database: {all_leads_count}")
        
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # Don't use apply_lead_filters for summary - show all data
        total_leads = Lead.query.count()
        new_leads_today = Lead.query.filter(func.date(Lead.created_at) == today).count()
        follow_ups_due = Lead.query.filter(
            Lead.status == 'Follow Up',
            Lead.followup_date != None,
            Lead.followup_date >= week_start,
            Lead.followup_date <= week_start + timedelta(days=6)
        ).count()
        converted = Lead.query.filter(Lead.status == 'Converted').count()
        not_interested = Lead.query.filter(Lead.status == 'Not Interested').count()
        
        print(f"Summary counts - Total: {total_leads}, New Today: {new_leads_today}, Follow-ups: {follow_ups_due}, Converted: {converted}, Not Interested: {not_interested}")
        
        response_data = {
            'total_leads': total_leads,
            'new_leads_today': new_leads_today,
            'follow_ups_due': follow_ups_due,
            'converted': converted,
            'not_interested': not_interested
        }
        
        return jsonify(response_data)
    except Exception as e:
        print(f"Error in api_reports_summary: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/reports/by_status')
@login_required
def api_reports_by_status():
    try:
        # Don't use apply_lead_filters for status counts - show all data
        status_counts = Lead.query.with_entities(Lead.status, func.count(Lead.id)).group_by(Lead.status).all()
        response_data = {s or 'Unknown': c for s, c in status_counts}
        print(f"API Status Response: {response_data}")
        return jsonify(response_data)
    except Exception as e:
        print(f"Error in api_reports_by_status: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/reports/by_date')
@login_required
def api_reports_by_date():
    today = date.today()
    start_date = today - timedelta(days=29)
    # Don't use apply_lead_filters for date counts - show all data
    results = Lead.query.filter(Lead.created_at >= start_date).with_entities(func.date(Lead.created_at), func.count(Lead.id)).group_by(func.date(Lead.created_at)).order_by(func.date(Lead.created_at)).all()
    data = [{'date': str(d), 'count': c} for d, c in results]
    return jsonify(data)

@bp.route('/api/reports/by_industry')
@login_required
def api_reports_by_industry():
    # Don't use apply_lead_filters for industry counts - show all data
    results = Lead.query.with_entities(Lead.industry, func.count(Lead.id)).group_by(Lead.industry).all()
    return jsonify({i or 'Unknown': c for i, c in results})

@bp.route('/api/reports/by_country')
@login_required
def api_reports_by_country():
    # Don't use apply_lead_filters for country counts - show all data
    results = Lead.query.with_entities(Lead.country, func.count(Lead.id)).group_by(Lead.country).all()
    return jsonify({c or 'Unknown': n for c, n in results})

@bp.route('/api/reports/by_source')
@login_required
def api_reports_by_source():
    # Don't use apply_lead_filters for source counts - show all data
    results = Lead.query.with_entities(Lead.source, func.count(Lead.id)).group_by(Lead.source).all()
    return jsonify({s or 'Unknown': c for s, c in results})

@bp.route('/api/reports/export')
@login_required
@permission_required('admin')
def api_reports_export():
    format = request.args.get('format', 'csv')
    query = apply_lead_filters(Lead.query)
    leads = query.all()
    # Prepare data
    rows = []
    for lead in leads:
        rows.append({
            'ID': lead.id,
            'Company Name': lead.company_name,
            'Website': lead.company_website,
            'Country': lead.country,
            'State': lead.state,
            'Industry': lead.industry,
            'Source': lead.source,
            'Status': lead.status,
            'Followup Date': lead.followup_date.strftime('%Y-%m-%d') if lead.followup_date else '',
            'Timezone': lead.timezone,
            'Created At': lead.created_at.strftime('%Y-%m-%d %H:%M'),
            'Updated At': lead.updated_at.strftime('%Y-%m-%d %H:%M'),
            'Notes': lead.notes,
        })
    if format == 'excel':
        try:
            import pandas as pd
            df = pd.DataFrame(rows)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            output.seek(0)
            return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='leads_report.xlsx')
        except ImportError:
            # Fallback to CSV if pandas is not available
            import csv
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=rows[0].keys() if rows else ['ID'])
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
            output.seek(0)
            return send_file(io.BytesIO(output.read().encode()), mimetype='text/csv', as_attachment=True, download_name='leads_report.csv')
    # Default: CSV
    import csv
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys() if rows else ['ID'])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    output.seek(0)
    return send_file(io.BytesIO(output.read().encode()), mimetype='text/csv', as_attachment=True, download_name='leads_report.csv')

@bp.route('/api/reports/missing_data')
@login_required
def api_reports_missing_data():
    # Leads with no contacts
    leads_no_contacts = Lead.query.filter(~Lead.contacts.any()).all()
    # Leads with at least one contact but no emails
    leads_no_email = Lead.query.filter(Lead.contacts.any()).filter(~Lead.contacts.any(Contact.emails.any())).all()
    # Leads with at least one contact but no phones
    leads_no_phone = Lead.query.filter(Lead.contacts.any()).filter(~Lead.contacts.any(Contact.phones.any())).all()
    return jsonify({
        'no_contacts': {'count': len(leads_no_contacts), 'leads': [l.id for l in leads_no_contacts]},
        'no_email': {'count': len(leads_no_email), 'leads': [l.id for l in leads_no_email]},
        'no_phone': {'count': len(leads_no_phone), 'leads': [l.id for l in leads_no_phone]},
    })

@bp.route('/api/reports/duplicates')
@login_required
def api_reports_duplicates():
    # Duplicate company names
    dup_companies = db.session.query(Lead.company_name, func.count(Lead.id)).group_by(Lead.company_name).having(func.count(Lead.id) > 1).all()
    company_dups = {}
    for name, _ in dup_companies:
        ids = [l.id for l in Lead.query.filter(Lead.company_name == name).all()]
        if len(ids) > 1:
            company_dups[name] = ids
    # Duplicate emails
    dup_emails = db.session.query(ContactEmail.email, func.count(ContactEmail.id)).group_by(ContactEmail.email).having(func.count(ContactEmail.id) > 1).all()
    email_dups = {}
    for email, _ in dup_emails:
        leads = db.session.query(Lead.id).join(Contact).join(ContactEmail).filter(ContactEmail.email == email).distinct().all()
        ids = [l.id for l in leads]
        if len(ids) > 1:
            email_dups[email] = ids
    # Duplicate phones
    dup_phones = db.session.query(ContactPhone.phone, func.count(ContactPhone.id)).group_by(ContactPhone.phone).having(func.count(ContactPhone.id) > 1).all()
    phone_dups = {}
    for phone, _ in dup_phones:
        leads = db.session.query(Lead.id).join(Contact).join(ContactPhone).filter(ContactPhone.phone == phone).distinct().all()
        ids = [l.id for l in leads]
        if len(ids) > 1:
            phone_dups[phone] = ids
    return jsonify({
        'company': company_dups,
        'email': email_dups,
        'phone': phone_dups
    })

@bp.route('/api/reports/contact_engagement')
@login_required
def api_reports_contact_engagement():
    # Number of contacts per lead
    contact_counts = db.session.query(Lead.id, func.count(Contact.id)).outerjoin(Contact).group_by(Lead.id).all()
    # Contact method usage
    phone_count = db.session.query(ContactPhone).count()
    email_count = db.session.query(ContactEmail).count()
    social_count = db.session.query(SocialProfile).count()
    return jsonify({
        'contacts_per_lead': [{'lead_id': lid, 'count': cnt} for lid, cnt in contact_counts],
        'method_usage': {
            'phone': phone_count,
            'email': email_count,
            'social': social_count
        }
    })

@bp.route('/api/reports/pipeline_insights')
@login_required
def api_reports_pipeline_insights():
    today = date.today()
    # Follow-up aging: days from created_at to followup_date for leads with followup_date
    followup_leads = Lead.query.filter(Lead.followup_date != None, Lead.created_at != None).all()
    followup_ages = [(l.followup_date - l.created_at.date()).days for l in followup_leads if l.followup_date and l.created_at]
    avg_followup = mean(followup_ages) if followup_ages else 0
    median_followup = median(followup_ages) if followup_ages else 0
    # Overdue follow-ups: leads with followup_date < today and status == 'Follow Up'
    overdue = Lead.query.filter(Lead.status == 'Follow Up', Lead.followup_date != None, Lead.followup_date < today).count()
    # Pipeline velocity: days from created_at to status change (Converted/Not Interested)
    converted_leads = Lead.query.filter(Lead.status == 'Converted', Lead.created_at != None, Lead.updated_at != None).all()
    notint_leads = Lead.query.filter(Lead.status == 'Not Interested', Lead.created_at != None, Lead.updated_at != None).all()
    conv_ages = [(l.updated_at.date() - l.created_at.date()).days for l in converted_leads if l.updated_at and l.created_at]
    notint_ages = [(l.updated_at.date() - l.created_at.date()).days for l in notint_leads if l.updated_at and l.created_at]
    avg_conv = mean(conv_ages) if conv_ages else 0
    avg_notint = mean(notint_ages) if notint_ages else 0
    return jsonify({
        'followup_aging': {'average_days': avg_followup, 'median_days': median_followup},
        'overdue_followups': overdue,
        'pipeline_velocity': {
            'converted_avg_days': avg_conv,
            'not_interested_avg_days': avg_notint
        }
    })

@bp.route('/api/reports/conversion_funnel')
@login_required
def api_reports_conversion_funnel():
    def get_funnel(group_field):
        total = db.session.query(getattr(Lead, group_field), func.count(Lead.id)).group_by(getattr(Lead, group_field)).all()
        converted = db.session.query(getattr(Lead, group_field), func.count(Lead.id)).filter(Lead.status == 'Converted').group_by(getattr(Lead, group_field)).all()
        total_dict = {k or 'Unknown': v for k, v in total}
        conv_dict = {k or 'Unknown': v for k, v in converted}
        result = {}
        for k in total_dict:
            conv = conv_dict.get(k, 0)
            result[k] = {
                'total': total_dict[k],
                'converted': conv,
                'conversion_rate': round(100 * conv / total_dict[k], 1) if total_dict[k] else 0
            }
        return result
    return jsonify({
        'source': get_funnel('source'),
        'industry': get_funnel('industry'),
        'country': get_funnel('country')
    })

@bp.route('/api/reports/geo_heatmap')
@login_required
def api_reports_geo_heatmap():
    # By country
    country_totals = db.session.query(Lead.country, func.count(Lead.id)).group_by(Lead.country).all()
    country_converted = db.session.query(Lead.country, func.count(Lead.id)).filter(Lead.status == 'Converted').group_by(Lead.country).all()
    country_data = {}
    for c, total in country_totals:
        c = c or 'Unknown'
        conv = dict(country_converted).get(c, 0)
        country_data[c] = {
            'total': total,
            'converted': conv,
            'conversion_rate': round(100 * conv / total, 1) if total else 0
        }
    # By state (for USA only)
    state_totals = db.session.query(Lead.state, func.count(Lead.id)).filter(Lead.country == 'USA').group_by(Lead.state).all()
    state_converted = db.session.query(Lead.state, func.count(Lead.id)).filter(Lead.country == 'USA', Lead.status == 'Converted').group_by(Lead.state).all()
    state_data = {}
    for s, total in state_totals:
        s = s or 'Unknown'
        conv = dict(state_converted).get(s, 0)
        state_data[s] = {
            'total': total,
            'converted': conv,
            'conversion_rate': round(100 * conv / total, 1) if total else 0
        }
    return jsonify({'country': country_data, 'usa_states': state_data})

@bp.route('/api/scraper/start', methods=['POST'])
def api_scraper_start():
    global scraper_thread, scraper_instance
    with scraper_lock:
        if scraper_thread and scraper_thread.is_alive():
            return jsonify({'success': False, 'message': 'Scraper already running.'})
        scraper_instance = LinkedInScraper(current_app._get_current_object())
        def run_scraper():
            try:
                scraper_instance.scrape()
            except Exception as e:
                print(f'Scraper error: {e}')
        scraper_thread = threading.Thread(target=run_scraper, daemon=True)
        scraper_thread.start()
    return jsonify({'success': True, 'message': 'Scraper started.'})

@bp.route('/api/scraper/stop', methods=['POST'])
def api_scraper_stop():
    global scraper_instance
    with scraper_lock:
        if scraper_instance:
            scraper_instance.stop()
            scraper_instance = None
            return jsonify({'success': True, 'message': 'Scraper stopped.'})
        else:
            return jsonify({'success': False, 'message': 'Scraper not running.'})

@bp.route('/api/check_duplicates', methods=['POST'])
def api_check_duplicates():
    """Check for potential duplicates before adding a new lead"""
    # Skip CSRF validation for this API endpoint
    try:
        data = request.get_json()
        company_name = data.get('company_name', '').strip().title()
        company_website = data.get('company_website', '').strip().lower()
        contacts = data.get('contacts', [])
        
        duplicates = {
            'company_name': [],
            'company_website': [],
            'email': [],
            'phone': []
        }
        
        # Check for duplicate company names (exact match)
        if company_name:
            company_duplicates = Lead.query.filter(
                func.lower(Lead.company_name) == company_name.lower()
            ).all()
            if company_duplicates:
                duplicates['company_name'] = [
                    {
                        'id': lead.id,
                        'company_name': lead.company_name,
                        'company_website': lead.company_website,
                        'country': lead.country,
                        'state': lead.state,
                        'industry': lead.industry,
                        'status': lead.status,
                        'created_at': safe_date(lead.created_at),
                        'contacts': [
                            {
                                'name': contact.name,
                                'position': contact.position,
                                'phones': [p.phone for p in contact.phones],
                                'emails': [e.email for e in contact.emails]
                            }
                            for contact in lead.contacts
                        ]
                    }
                    for lead in company_duplicates
                ]
        
        # Check for duplicate company websites
        if company_website:
            website_duplicates = Lead.query.filter(
                func.lower(Lead.company_website) == company_website
            ).all()
            if website_duplicates:
                duplicates['company_website'] = [
                    {
                        'id': lead.id,
                        'company_name': lead.company_name,
                        'company_website': lead.company_website,
                        'country': lead.country,
                        'state': lead.state,
                        'industry': lead.industry,
                        'status': lead.status,
                        'created_at': safe_date(lead.created_at),
                        'contacts': [
                            {
                                'name': contact.name,
                                'position': contact.position,
                                'phones': [p.phone for p in contact.phones],
                                'emails': [e.email for e in contact.emails]
                            }
                            for contact in lead.contacts
                        ]
                    }
                    for lead in website_duplicates
                ]
        
        # Check for duplicate emails and phones from contacts
        for contact in contacts:
            emails = contact.get('emails', [])
            phones = contact.get('phones', [])
            
            for email in emails:
                if email:
                    email_duplicates = db.session.query(Lead).join(Contact).join(ContactEmail).filter(
                        func.lower(ContactEmail.email) == email.lower()
                    ).all()
                    if email_duplicates:
                        duplicates['email'].extend([
                            {
                                'id': lead.id,
                                'company_name': lead.company_name,
                                'company_website': lead.company_website,
                                'country': lead.country,
                                'state': lead.state,
                                'industry': lead.industry,
                                'status': lead.status,
                                'created_at': safe_date(lead.created_at),
                                'matching_email': email,
                                'contacts': [
                                    {
                                        'name': contact.name,
                                        'position': contact.position,
                                        'phones': [p.phone for p in contact.phones],
                                        'emails': [e.email for e in contact.emails]
                                    }
                                    for contact in lead.contacts
                                ]
                            }
                            for lead in email_duplicates
                        ])
            
            for phone in phones:
                if phone:
                    phone_duplicates = db.session.query(Lead).join(Contact).join(ContactPhone).filter(
                        ContactPhone.phone == phone
                    ).all()
                    if phone_duplicates:
                        duplicates['phone'].extend([
                            {
                                'id': lead.id,
                                'company_name': lead.company_name,
                                'company_website': lead.company_website,
                                'country': lead.country,
                                'state': lead.state,
                                'industry': lead.industry,
                                'status': lead.status,
                                'created_at': safe_date(lead.created_at),
                                'matching_phone': phone,
                                'contacts': [
                                    {
                                        'name': contact.name,
                                        'position': contact.position,
                                        'phones': [p.phone for p in contact.phones],
                                        'emails': [e.email for e in contact.emails]
                                    }
                                    for contact in lead.contacts
                                ]
                            }
                            for lead in phone_duplicates
                        ])
        
        # Remove duplicates from email and phone lists
        duplicates['email'] = list({dupe['id']: dupe for dupe in duplicates['email']}.values())
        duplicates['phone'] = list({dupe['id']: dupe for dupe in duplicates['phone']}.values())
        
        has_duplicates = any(len(duplicates[key]) > 0 for key in duplicates)
        
        return jsonify({
            'success': True,
            'has_duplicates': has_duplicates,
            'duplicates': duplicates
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 

@bp.route('/import_leads', methods=['GET', 'POST'])
@login_required
@permission_required('admin')
def import_leads():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        if not allowed_file(file.filename):
            flash('Invalid file type. Only CSV and Excel files are allowed.', 'danger')
            return redirect(request.url)
        filename = secure_filename(file.filename)
        filepath = os.path.join('instance', filename)
        file.save(filepath)
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)
            # Accept both user-friendly and snake_case headers
            header_map = {
                'company_name': 'Company Name',
                'company_website': 'Company Website',
                'country': 'Country',
                'state': 'State',
                'industry': 'Industry',
                'contact_name': 'Contact Name',
                'contact_position': 'Contact Position',
                'contact_phone': 'Contact Phone',
                'contact_email': 'Contact Email',
                'timezone': 'Time Zone',  # Add support for Time Zone column
            }
            # Accept both 'Time Zone' and 'timezone' as valid headers
            if 'Time Zone' not in df.columns and 'timezone' in df.columns:
                df['Time Zone'] = df['timezone']
            required = [header_map['company_name'], header_map['company_website'], header_map['country'], header_map['industry'], header_map['contact_phone']]
            for col in required:
                if col not in df.columns:
                    flash(f'Missing required column: {col}', 'danger')
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    return redirect(request.url)
            count = 0
            for _, row in df.iterrows():
                company_name = row.get('Company Name')
                company_website = row.get('Company Website')
                country = row.get('Country')
                industry = row.get('Industry')
                contact_phone = row.get('Contact Phone')
                # Skip if any required field is missing or NaN
                if (not company_name or pd.isna(company_name) or
                    not company_website or pd.isna(company_website) or
                    not country or pd.isna(country) or
                    not industry or pd.isna(industry) or
                    not contact_phone or pd.isna(contact_phone)):
                    continue
                state = row.get('State')
                timezone = row.get('Time Zone') if 'Time Zone' in row else None
                lead = Lead(
                    company_name=company_name,
                    company_website=company_website,
                    country=country,
                    state=state,
                    industry=industry,
                    status='New',
                    timezone=timezone
                )
                db.session.add(lead)
                db.session.flush()
                contact_name = row.get('Contact Name')
                if not contact_name or pd.isna(contact_name):
                    contact_name = company_name
                contact_position = row.get('Contact Position')
                contact_email = row.get('Contact Email')
                contact = Contact(
                    lead_id=lead.id,
                    name=contact_name or '',
                    position=contact_position or ''
                )
                db.session.add(contact)
                db.session.flush()
                db.session.add(ContactPhone(contact_id=contact.id, phone=str(contact_phone)))
                if contact_email and not pd.isna(contact_email):
                    db.session.add(ContactEmail(contact_id=contact.id, email=str(contact_email)))
                count += 1
            db.session.commit()
            flash(f'Successfully imported {count} leads.', 'success')
        except Exception as e:
            flash(f'Import failed: {e}', 'danger')
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
        return redirect(url_for('main.dashboard'))
    return render_template('import_leads.html') 

@bp.route('/dashboard/personal')
@login_required
def personal_dashboard():
    """Personal dashboard for individual users showing their own stats and tasks, or production dashboard for Production users."""
    # Admin users should be redirected to main dashboard
    if current_user.has_permission('admin'):
        return redirect(url_for('main.dashboard'))

    # If user is Production, show the production dashboard logic and template
    if current_user.role and current_user.role.name == 'Production':
        today = date.today()
        assigned_tasks = ProductionTask.query.filter_by(assigned_to=current_user.id).order_by(ProductionTask.created_at.desc()).all()
        today_app_usage = ApplicationUsage.query.filter_by(user_id=current_user.id, usage_date=today).all()
        today_detailed_apps = DetailedApplicationUsage.query.filter_by(user_id=current_user.id, usage_date=today).all()
        today_activity = MouseKeyboardActivity.query.filter_by(user_id=current_user.id, activity_date=today).first()
        today_report = ProductivityReport.query.filter_by(user_id=current_user.id, report_date=today).first()
        today_website_visits = WebsiteVisit.query.filter_by(user_id=current_user.id, visit_date=today).all()
        today_browser_activity = BrowserActivity.query.filter_by(user_id=current_user.id, activity_date=today).all()
        recent_activities = ProductionActivity.query.filter_by(user_id=current_user.id).order_by(ProductionActivity.created_at.desc()).limit(10).all()
        total_active_time = sum(app.active_time_seconds for app in today_app_usage) if today_app_usage else 0
        total_break_time = sum(app.idle_time_seconds for app in today_app_usage) if today_app_usage else 0
        productivity_score = min(100, (total_active_time / (total_active_time + total_break_time)) * 100) if total_active_time > 0 else 0
        adobe_apps = ['Adobe Photoshop', 'Adobe Illustrator', 'Adobe InDesign', 'Adobe XD']
        adobe_usage = {}
        total_adobe_time = 0
        for app in today_app_usage:
            if app.application_name in adobe_apps:
                total_adobe_time += app.total_time_seconds
        for app in today_app_usage:
            if app.application_name in adobe_apps:
                if total_adobe_time > 0:
                    percentage = (app.total_time_seconds / total_adobe_time) * 100
                    adobe_usage[app.application_name] = round(percentage, 1)
                else:
                    adobe_usage[app.application_name] = 0
        creative_tools = {}
        communication_tools = {}
        browsers = {}
        productivity_tools = {}
        for app in today_detailed_apps:
            if app.application_category == 'creative':
                creative_tools[app.application_name] = {
                    'time': app.total_time_seconds,
                    'percentage': round((app.total_time_seconds / (total_active_time + total_break_time)) * 100, 1) if (total_active_time + total_break_time) > 0 else 0
                }
            elif app.application_category == 'communication':
                communication_tools[app.application_name] = {
                    'time': app.total_time_seconds,
                    'percentage': round((app.total_time_seconds / (total_active_time + total_break_time)) * 100, 1) if (total_active_time + total_break_time) > 0 else 0
                }
            elif app.application_category == 'browser':
                browsers[app.application_name] = {
                    'time': app.total_time_seconds,
                    'percentage': round((app.total_time_seconds / (total_active_time + total_break_time)) * 100, 1) if (total_active_time + total_break_time) > 0 else 0
                }
            elif app.application_category == 'productivity':
                productivity_tools[app.application_name] = {
                    'time': app.total_time_seconds,
                    'percentage': round((app.total_time_seconds / (total_active_time + total_break_time)) * 100, 1) if (total_active_time + total_break_time) > 0 else 0
                }
        reference_sites = {}
        social_media = {}
        client_portals = {}
        other_websites = {}
        for visit in today_website_visits:
            if visit.website_category == 'reference':
                reference_sites[visit.website_name] = {
                    'visits': visit.visit_count,
                    'time': visit.total_time_seconds
                }
            elif visit.website_category == 'social':
                social_media[visit.website_name] = {
                    'visits': visit.visit_count,
                    'time': visit.total_time_seconds
                }
            elif visit.website_category == 'client':
                client_portals[visit.website_name] = {
                    'visits': visit.visit_count,
                    'time': visit.total_time_seconds
                }
            elif visit.website_category == 'other':
                other_websites[visit.website_name] = {
                    'visits': visit.visit_count,
                    'time': visit.total_time_seconds
                }
        browser_usage = {}
        for browser in today_browser_activity:
            browser_usage[browser.browser_name] = {
                'time': browser.total_time_seconds,
                'websites': browser.websites_visited,
                'tabs': browser.tabs_opened,
                'percentage': round((browser.total_time_seconds / (total_active_time + total_break_time)) * 100, 1) if (total_active_time + total_break_time) > 0 else 0
            }
        work_apps_time = sum(app.total_time_seconds for app in today_detailed_apps if app.application_category in ['creative', 'productivity'])
        web_activity_time = sum(visit.total_time_seconds for visit in today_website_visits)
        communication_time = sum(app.total_time_seconds for app in today_detailed_apps if app.application_category == 'communication')
        file_management_time = sum(app.total_time_seconds for app in today_detailed_apps if app.application_name in ['File Explorer', 'Finder', 'Dropbox', 'Google Drive'])
        total_work_time = work_apps_time + communication_time + file_management_time
        total_distraction_time = sum(visit.total_time_seconds for visit in today_website_visits if visit.website_category == 'social')
        if total_work_time > 0:
            focus_score = min(100, (total_work_time / (total_work_time + total_distraction_time)) * 100)
        else:
            focus_score = 0
        task_stats = {
            'total': len(assigned_tasks),
            'pending': len([t for t in assigned_tasks if t.status == 'pending']),
            'in_progress': len([t for t in assigned_tasks if t.status == 'in_progress']),
            'completed': len([t for t in assigned_tasks if t.status == 'completed'])
        }
        week_start = today - timedelta(days=today.weekday())
        week_tasks = ProductionTask.query.filter(ProductionTask.assigned_to == current_user.id, ProductionTask.created_at >= week_start).all()
        weekly_completed = len([t for t in week_tasks if t.status == 'completed'])
        weekly_target = 40
        weekly_progress = min(100, (weekly_completed / weekly_target) * 100) if weekly_target > 0 else 0
        today_desktop_activities = DesktopActivity.query.filter(
            DesktopActivity.user_id == current_user.id,
            db.func.date(DesktopActivity.timestamp) == today
        ).order_by(DesktopActivity.timestamp.desc()).all()
        return render_template('production/dashboard.html',
            assigned_tasks=assigned_tasks,
            task_stats=task_stats,
            today_app_usage=today_app_usage,
            today_activity=today_activity,
            today_report=today_report,
            recent_activities=recent_activities,
            total_active_time=total_active_time,
            total_break_time=total_break_time,
            productivity_score=productivity_score,
            adobe_usage=adobe_usage,
            creative_tools=creative_tools,
            communication_tools=communication_tools,
            browsers=browsers,
            productivity_tools=productivity_tools,
            reference_sites=reference_sites,
            social_media=social_media,
            client_portals=client_portals,
            other_websites=other_websites,
            browser_usage=browser_usage,
            work_apps_time=work_apps_time,
            web_activity_time=web_activity_time,
            communication_time=communication_time,
            file_management_time=file_management_time,
            total_work_time=total_work_time,
            total_distraction_time=total_distraction_time,
            focus_score=focus_score,
            weekly_completed=weekly_completed,
            weekly_target=weekly_target,
            weekly_progress=weekly_progress,
            today_desktop_activities=today_desktop_activities
        )

    # Otherwise, show the current personal dashboard for Callers
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = date(today.year, today.month, 1)
    daily_stats = UserDailyStats.query.filter_by(user_id=current_user.id, date=today).first()
    weekly_stats = UserWeeklyStats.query.filter_by(user_id=current_user.id, week_start=week_start).first()
    monthly_stats = UserMonthlyStats.query.filter_by(user_id=current_user.id, month_year=month_start).first()
    pending_tasks = UserTask.query.filter_by(user_id=current_user.id, status='pending').order_by(UserTask.due_date.asc()).limit(5).all()
    in_progress_tasks = UserTask.query.filter_by(user_id=current_user.id, status='in_progress').order_by(UserTask.due_date.asc()).limit(5).all()
    recent_activities = UserActivity.query.filter_by(user_id=current_user.id).order_by(UserActivity.created_at.desc()).limit(10).all()
    user_leads = Lead.query.filter_by(created_by=current_user.id).order_by(Lead.created_at.desc()).limit(10).all()
    personal_metrics = {
        'today_leads': daily_stats.leads_created if daily_stats else 0,
        'today_followups': daily_stats.followups_added if daily_stats else 0,
        'today_conversions': daily_stats.conversions if daily_stats else 0,
        'week_leads': weekly_stats.leads_created if weekly_stats else 0,
        'week_followups': weekly_stats.followups_added if weekly_stats else 0,
        'week_conversions': weekly_stats.conversions if weekly_stats else 0,
        'month_leads': monthly_stats.leads_created if monthly_stats else 0,
        'month_followups': monthly_stats.followups_added if monthly_stats else 0,
        'month_conversions': monthly_stats.conversions if monthly_stats else 0,
        'pending_tasks': len(pending_tasks),
        'in_progress_tasks': len(in_progress_tasks)
    }
    total_user_leads = Lead.query.filter_by(created_by=current_user.id).count()
    converted_statuses = ['Converted', 'On Board Clients']
    total_user_converted = Lead.query.filter(Lead.status.in_(converted_statuses), Lead.created_by == current_user.id).count()
    personal_conversion_rate = round((total_user_converted / total_user_leads * 100), 1) if total_user_leads else 0
    recent_conversions = Lead.query.filter(Lead.status.in_(converted_statuses), Lead.created_by == current_user.id, Lead.created_at >= week_start).count()
    user_leads_by_status = db.session.query(Lead.status, func.count(Lead.id).label('count')).filter(Lead.created_by == current_user.id).group_by(Lead.status).all()
    today_calls = Lead.query.filter(func.date(Lead.updated_at) == today, Lead.status != 'New', Lead.created_by == current_user.id).count()
    week_calls = Lead.query.filter(Lead.updated_at >= week_start, Lead.status != 'New', Lead.created_by == current_user.id).count()
    month_calls = Lead.query.filter(Lead.updated_at >= month_start, Lead.status != 'New', Lead.created_by == current_user.id).count()
    total_calls = Lead.query.filter(Lead.status != 'New', Lead.created_by == current_user.id).count()
    personal_metrics.update({
        'total_leads': total_user_leads,
        'total_converted': total_user_converted,
        'conversion_rate': personal_conversion_rate,
        'recent_conversions': recent_conversions,
        'leads_by_status': user_leads_by_status,
        'today_calls': today_calls,
        'week_calls': week_calls,
        'month_calls': month_calls,
        'total_calls': total_calls
    })
    return render_template('personal_dashboard.html', 
        personal_metrics=personal_metrics,
        pending_tasks=pending_tasks,
        in_progress_tasks=in_progress_tasks,
        recent_activities=recent_activities,
        user_leads=user_leads,
        today=today
    )

@bp.route('/dashboard/personal/stats')
@login_required
def personal_stats():
    """API endpoint for personal statistics"""
    # Admin users should not access personal stats
    if current_user.has_permission('admin'):
        return jsonify({'error': 'Admin users should use main dashboard'}), 403
    
    period = request.args.get('period', 'week')  # week, month, year
    today = date.today()
    
    if period == 'week':
        start_date = today - timedelta(days=today.weekday())
        stats = UserWeeklyStats.query.filter_by(user_id=current_user.id, week_start=start_date).first()
    elif period == 'month':
        start_date = date(today.year, today.month, 1)
        stats = UserMonthlyStats.query.filter_by(user_id=current_user.id, month_year=start_date).first()
    else:  # year
        start_date = date(today.year, 1, 1)
        stats = UserMonthlyStats.query.filter(
            UserMonthlyStats.user_id == current_user.id,
            UserMonthlyStats.month_year >= start_date
        ).all()
    
    if period in ['week', 'month']:
        if stats:
            return jsonify({
                'leads_created': stats.leads_created,
                'leads_updated': stats.leads_updated,
                'followups_added': stats.followups_added,
                'conversions': stats.conversions,
                'total_time_spent': stats.total_time_spent
            })
        else:
            return jsonify({
                'leads_created': 0,
                'leads_updated': 0,
                'followups_added': 0,
                'conversions': 0,
                'total_time_spent': 0
            })
    else:  # year - aggregate monthly stats
        total_leads = sum(s.leads_created for s in stats)
        total_conversions = sum(s.conversions for s in stats)
        total_time = sum(s.total_time_spent for s in stats)
        return jsonify({
            'leads_created': total_leads,
            'conversions': total_conversions,
            'total_time_spent': total_time
        })

@bp.route('/tasks')
@login_required
def my_tasks():
    """User's task management page"""
    # Admin users should use admin task management
    if current_user.has_permission('admin'):
        return redirect(url_for('main.admin_manage_tasks'))
    
    status_filter = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'all')
    
    query = UserTask.query.filter_by(user_id=current_user.id)
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    if priority_filter != 'all':
        query = query.filter_by(priority=priority_filter)
    
    tasks = query.order_by(UserTask.due_date.asc(), UserTask.priority.desc()).all()
    
    return render_template('my_tasks.html', tasks=tasks, 
                         status_filter=status_filter, 
                         priority_filter=priority_filter)

@bp.route('/tasks/<int:task_id>/update', methods=['POST'])
@login_required
def update_task_status(task_id):
    """Update task status"""
    task = UserTask.query.get_or_404(task_id)
    
    # Ensure user can only update their own tasks
    if task.user_id != current_user.id:
        flash('You can only update your own tasks.', 'error')
        return redirect(url_for('main.my_tasks'))
    
    new_status = request.form.get('status')
    if new_status in ['pending', 'in_progress', 'completed', 'cancelled']:
        task.status = new_status
        if new_status == 'completed':
            task.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        flash('Task status updated successfully!', 'success')
    
    return redirect(url_for('main.my_tasks'))

# Admin Activity Dashboard Routes
@bp.route('/admin/activity')
@login_required
@permission_required('admin')
def admin_activity_dashboard():
    """Admin dashboard showing all users' activity and progress"""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = date(today.year, today.month, 1)
    
    # Get all users with their stats
    users = User.query.filter_by(is_approved=True).all()
    user_stats = {}
    
    for user in users:
        daily_stats = UserDailyStats.query.filter_by(user_id=user.id, date=today).first()
        weekly_stats = UserWeeklyStats.query.filter_by(user_id=user.id, week_start=week_start).first()
        monthly_stats = UserMonthlyStats.query.filter_by(user_id=user.id, month_year=month_start).first()
        
        # Calculate call analytics for each user
        today_calls = Lead.query.filter(
            func.date(Lead.updated_at) == today,
            Lead.status != 'New',
            Lead.created_by == user.id
        ).count()
        
        week_calls = Lead.query.filter(
            Lead.updated_at >= week_start,
            Lead.status != 'New',
            Lead.created_by == user.id
        ).count()
        
        month_calls = Lead.query.filter(
            Lead.updated_at >= month_start,
            Lead.status != 'New',
            Lead.created_by == user.id
        ).count()
        
        total_calls = Lead.query.filter(
            Lead.status != 'New',
            Lead.created_by == user.id
        ).count()
        
        user_stats[user.id] = {
            'user': user,
            'daily': daily_stats,
            'weekly': weekly_stats,
            'monthly': monthly_stats,
            'today_calls': today_calls,
            'week_calls': week_calls,
            'month_calls': month_calls,
            'total_calls': total_calls,
            'recent_activities': UserActivity.query.filter_by(user_id=user.id)
                .order_by(UserActivity.created_at.desc()).limit(5).all()
        }
    
    # Get team-wide metrics
    team_daily_stats = db.session.query(
        func.sum(UserDailyStats.leads_created).label('total_leads'),
        func.sum(UserDailyStats.followups_added).label('total_followups'),
        func.sum(UserDailyStats.conversions).label('total_conversions')
    ).filter(UserDailyStats.date == today).first()
    
    team_weekly_stats = db.session.query(
        func.sum(UserWeeklyStats.leads_created).label('total_leads'),
        func.sum(UserWeeklyStats.followups_added).label('total_followups'),
        func.sum(UserWeeklyStats.conversions).label('total_conversions')
    ).filter(UserWeeklyStats.week_start == week_start).first()
    
    # Fetch today's DesktopActivity for all Production users
    production_role = Role.query.filter_by(name='Production').first()
    production_users = User.query.filter_by(role_id=production_role.id).all() if production_role else []
    production_desktop_activities = {}
    for user in production_users:
        activities = DesktopActivity.query.filter(
            DesktopActivity.user_id == user.id,
            db.func.date(DesktopActivity.timestamp) == today
        ).order_by(DesktopActivity.timestamp.desc()).all()
        production_desktop_activities[user.id] = activities
    return render_template('admin_activity_dashboard.html',
                         user_stats=user_stats,
                         team_daily_stats=team_daily_stats,
                         team_weekly_stats=team_weekly_stats,
                         today=today,
                         production_desktop_activities=production_desktop_activities,
                         production_users=production_users)

@bp.route('/admin/activity/user/<int:user_id>')
@login_required
@permission_required('admin')
def admin_user_activity(user_id):
    """Detailed view of a specific user's activity with projections"""
    user = User.query.get_or_404(user_id)
    
    # Get user's detailed stats
    period = request.args.get('period', 'week')
    today = date.today()
    
    if period == 'week':
        start_date = today - timedelta(days=today.weekday())
        stats = UserWeeklyStats.query.filter_by(user_id=user.id, week_start=start_date).first()
    elif period == 'month':
        start_date = date(today.year, today.month, 1)
        stats = UserMonthlyStats.query.filter_by(user_id=user.id, month_year=start_date).first()
    else:  # year
        start_date = date(today.year, 1, 1)
        stats = UserMonthlyStats.query.filter(
            UserMonthlyStats.user_id == user.id,
            UserMonthlyStats.month_year >= start_date
        ).all()
    
    # Get user's activities
    activities = UserActivity.query.filter_by(user_id=user.id).order_by(UserActivity.created_at.desc()).limit(50).all()
    
    # Get user's tasks
    tasks = UserTask.query.filter_by(user_id=user.id).order_by(UserTask.created_at.desc()).all()
    
    # Get user's leads
    leads = Lead.query.filter_by(created_by=user.id).order_by(Lead.created_at.desc()).limit(20).all()
    
    # Get user's projections for current month
    current_month = date(today.year, today.month, 1)
    user_projections = Projection.query.filter_by(
        user_id=user.id,
        month_year=current_month
    ).all()
    
    # Calculate actual values for projections
    actual_leads = Lead.query.filter(
        Lead.created_by == user.id,
        func.date(Lead.created_at) >= current_month
    ).count()
    
    actual_calls = Lead.query.filter(
        Lead.updated_at >= current_month,
        Lead.status != 'New',
        Lead.created_by == user.id
    ).count()
    
    actual_conversions = Lead.query.filter(
        Lead.status.in_(['Converted', 'On Board Clients']),
        Lead.created_by == user.id,
        func.date(Lead.created_at) >= current_month
    ).count()
    
    # Calculate actual revenue for this user
    actual_revenue = Lead.query.filter(
        Lead.created_by == user.id,
        func.date(Lead.created_at) >= current_month,
        Lead.revenue > 0
    ).with_entities(func.sum(Lead.revenue)).scalar() or 0
    
    # Update actual values in projections
    for projection in user_projections:
        if projection.projection_type == 'leads':
            projection.actual_value = actual_leads
        elif projection.projection_type == 'calls':
            projection.actual_value = actual_calls
        elif projection.projection_type == 'conversions':
            projection.actual_value = actual_conversions
        elif projection.projection_type == 'revenue':
            projection.actual_value = int(actual_revenue)
        projection.calculate_completion()
    
    # Get user's converted clients and their projections
    user_converted_clients = ConvertedClient.query.filter_by(converted_by=user.id).all()
    client_projections_data = []
    
    for client in user_converted_clients:
        client_projections = ConvertedClientProjection.query.filter_by(
            client_id=client.id,
            month_year=current_month
        ).all()
        
        if client_projections:
            client_projections_data.append({
                'client': client,
                'projections': client_projections
            })
    
    # Get user's converted leads and their projections
    user_converted_leads = Lead.query.filter(
        Lead.created_by == user.id,
        Lead.status.in_(['Converted', 'On Board Clients'])
    ).all()
    lead_projections_data = []
    
    for lead in user_converted_leads:
        lead_projections = LeadProjection.query.filter_by(
            lead_id=lead.id,
            month_year=current_month
        ).all()
        
        if lead_projections:
            lead_projections_data.append({
                'lead': lead,
                'projections': lead_projections
            })
    
    db.session.commit()
    
    return render_template('admin_user_activity.html',
                         user=user,
                         stats=stats,
                         activities=activities,
                         tasks=tasks,
                         leads=leads,
                         period=period,
                         user_projections=user_projections,
                         client_projections_data=client_projections_data,
                         lead_projections_data=lead_projections_data,
                         current_month=current_month)

@bp.route('/admin/tasks')
@login_required
@permission_required('admin')
def admin_manage_tasks():
    """Admin task management - assign and monitor tasks"""
    users = User.query.filter_by(is_approved=True).all()
    tasks = UserTask.query.order_by(UserTask.created_at.desc()).all()
    
    return render_template('admin_manage_tasks.html', users=users, tasks=tasks)

@bp.route('/admin/tasks/assign', methods=['POST'])
@login_required
@permission_required('admin')
def admin_assign_task():
    """Assign a new task to a user"""
    user_id = request.form.get('user_id')
    title = request.form.get('title')
    description = request.form.get('description')
    task_type = request.form.get('task_type')
    priority = request.form.get('priority')
    due_date_str = request.form.get('due_date')
    
    if not all([user_id, title, task_type]):
        flash('Please fill in all required fields.', 'error')
        return redirect(url_for('main.admin_manage_tasks'))
    
    try:
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
    except ValueError:
        due_date = None
    
    task = UserTask(
        user_id=user_id,
        assigned_by=current_user.id,
        title=title,
        description=description,
        task_type=task_type,
        priority=priority,
        due_date=due_date
    )
    
    db.session.add(task)
    db.session.commit()
    
    flash('Task assigned successfully!', 'success')
    return redirect(url_for('main.admin_manage_tasks'))

# Projection Routes
@bp.route('/projections')
@login_required
def projections():
    """Projection dashboard for Caller users and management view for Admin/Manager"""
    today = date.today()
    current_month = date(today.year, today.month, 1)
    
    # Get current user's projections
    user_projections = Projection.query.filter_by(
        user_id=current_user.id,
        month_year=current_month
    ).all()
    
    # Get actual values for current month
    actual_leads = Lead.query.filter(
        Lead.created_by == current_user.id,
        func.date(Lead.created_at) >= current_month
    ).count()
    
    actual_calls = Lead.query.filter(
        Lead.updated_at >= current_month,
        Lead.status != 'New',
        Lead.created_by == current_user.id
    ).count()
    
    actual_conversions = Lead.query.filter(
        Lead.status.in_(['Converted', 'On Board Clients']),
        Lead.created_by == current_user.id,
        func.date(Lead.created_at) >= current_month
    ).count()
    
    # Update actual values in projections
    for projection in user_projections:
        if projection.projection_type == 'leads':
            projection.actual_value = actual_leads
        elif projection.projection_type == 'calls':
            projection.actual_value = actual_calls
        elif projection.projection_type == 'conversions':
            projection.actual_value = actual_conversions
        projection.calculate_completion()
    
    db.session.commit()
    
    return render_template('projections.html', 
                         projections=user_projections,
                         current_month=current_month,
                         actual_leads=actual_leads,
                         actual_calls=actual_calls,
                         actual_conversions=actual_conversions)

@bp.route('/projections/create', methods=['GET', 'POST'])
@login_required
def create_projection():
    """Create new projection"""
    if request.method == 'POST':
        projection_type = request.form.get('projection_type')
        target_value = int(request.form.get('target_value'))
        month_year_str = request.form.get('month_year')
        notes = request.form.get('notes', '')
        
        # Parse month_year (format: YYYY-MM)
        month_year = datetime.strptime(month_year_str + '-01', '%Y-%m-%d').date()
        
        # Check if projection already exists
        existing_projection = Projection.query.filter_by(
            user_id=current_user.id,
            month_year=month_year,
            projection_type=projection_type
        ).first()
        
        if existing_projection:
            flash('Projection for this type and month already exists!', 'error')
            return redirect(url_for('main.projections'))
        
        projection = Projection(
            user_id=current_user.id,
            month_year=month_year,
            projection_type=projection_type,
            target_value=target_value,
            notes=notes
        )
        
        db.session.add(projection)
        db.session.commit()
        
        flash('Projection created successfully!', 'success')
        return redirect(url_for('main.projections'))
    
    today = date.today()
    current_month = date(today.year, today.month, 1)
    return render_template('create_projection.html', current_month=current_month)

@bp.route('/projections/<int:projection_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_projection(projection_id):
    """Edit existing projection"""
    projection = Projection.query.get_or_404(projection_id)
    
    # Ensure user can only edit their own projections
    if projection.user_id != current_user.id and not current_user.has_permission('admin'):
        flash('You can only edit your own projections!', 'error')
        return redirect(url_for('main.projections'))
    
    if request.method == 'POST':
        projection.target_value = int(request.form.get('target_value'))
        projection.notes = request.form.get('notes', '')
        projection.calculate_completion()
        
        db.session.commit()
        flash('Projection updated successfully!', 'success')
        return redirect(url_for('main.projections'))
    
    return render_template('edit_projection.html', projection=projection)

@bp.route('/projections/<int:projection_id>/delete', methods=['POST'])
@login_required
def delete_projection(projection_id):
    """Delete projection"""
    projection = Projection.query.get_or_404(projection_id)
    
    # Ensure user can only delete their own projections
    if projection.user_id != current_user.id and not current_user.has_permission('admin'):
        flash('You can only delete your own projections!', 'error')
        return redirect(url_for('main.projections'))
    
    db.session.delete(projection)
    db.session.commit()
    
    flash('Projection deleted successfully!', 'success')
    return redirect(url_for('main.projections'))

@bp.route('/admin/projections')
@login_required
@permission_required('admin')
def admin_projections():
    """Admin view of all user projections with global overview"""
    today = date.today()
    current_month = date(today.year, today.month, 1)
    selected_month = request.args.get('month', current_month.strftime('%Y-%m'))
    
    # Parse selected month
    month_year = datetime.strptime(selected_month + '-01', '%Y-%m-%d').date()
    
    # Get all projections for the selected month
    all_projections = Projection.query.filter_by(month_year=month_year).all()
    
    # Group projections by user
    user_projections = {}
    for projection in all_projections:
        user_id = projection.user_id
        if user_id not in user_projections:
            user_projections[user_id] = {
                'user': projection.user,
                'projections': []
            }
        user_projections[user_id]['projections'].append(projection)
    
    # Calculate GLOBAL PROJECTIONS (sum of all user projections)
    global_projections = {
        'leads': {'target': 0, 'actual': 0, 'completion': 0},
        'calls': {'target': 0, 'actual': 0, 'completion': 0},
        'conversions': {'target': 0, 'actual': 0, 'completion': 0},
        'revenue': {'target': 0, 'actual': 0, 'completion': 0}
    }
    
    # Calculate GLOBAL CLIENT PROJECTIONS
    global_client_projections = {
        'revenue': {'target': 0, 'actual': 0, 'completion': 0},
        'work_volume': {'target': 0, 'actual': 0, 'completion': 0},
        'tasks': {'target': 0, 'actual': 0, 'completion': 0}
    }
    
    # Calculate GLOBAL LEAD PROJECTIONS
    global_lead_projections = {
        'revenue': {'target': 0, 'actual': 0, 'completion': 0},
        'work_volume': {'target': 0, 'actual': 0, 'completion': 0},
        'tasks': {'target': 0, 'actual': 0, 'completion': 0}
    }
    
    # Get actual values for each user and calculate global totals
    for user_id, data in user_projections.items():
        user = data['user']
        
        # Calculate actual values for this user
        actual_leads = Lead.query.filter(
            Lead.created_by == user_id,
            func.date(Lead.created_at) >= month_year
        ).count()
        
        actual_calls = Lead.query.filter(
            Lead.updated_at >= month_year,
            Lead.status != 'New',
            Lead.created_by == user_id
        ).count()
        
        actual_conversions = Lead.query.filter(
            Lead.status.in_(['Converted', 'On Board Clients']),
            Lead.created_by == user_id,
            func.date(Lead.created_at) >= month_year
        ).count()
        
        # Calculate actual revenue for this user
        actual_revenue = Lead.query.filter(
            Lead.created_by == user_id,
            func.date(Lead.created_at) >= month_year,
            Lead.revenue > 0
        ).with_entities(func.sum(Lead.revenue)).scalar() or 0
        
        # Update actual values in projections and accumulate global totals
        for projection in data['projections']:
            if projection.projection_type == 'leads':
                projection.actual_value = actual_leads
                global_projections['leads']['target'] += projection.target_value
                global_projections['leads']['actual'] += actual_leads
            elif projection.projection_type == 'calls':
                projection.actual_value = actual_calls
                global_projections['calls']['target'] += projection.target_value
                global_projections['calls']['actual'] += actual_calls
            elif projection.projection_type == 'conversions':
                projection.actual_value = actual_conversions
                global_projections['conversions']['target'] += projection.target_value
                global_projections['conversions']['actual'] += actual_conversions
            elif projection.projection_type == 'revenue':
                projection.actual_value = int(actual_revenue)
                global_projections['revenue']['target'] += projection.target_value
                global_projections['revenue']['actual'] += int(actual_revenue)
            projection.calculate_completion()
    
    # Calculate global completion percentages
    for projection_type in global_projections:
        if global_projections[projection_type]['target'] > 0:
            global_projections[projection_type]['completion'] = (
                global_projections[projection_type]['actual'] / global_projections[projection_type]['target']
            ) * 100
        else:
            global_projections[projection_type]['completion'] = 0
    
    # Calculate global client projections
    all_client_projections = ConvertedClientProjection.query.filter_by(month_year=month_year).all()
    for projection in all_client_projections:
        if projection.projection_type in global_client_projections:
            global_client_projections[projection.projection_type]['target'] += projection.target_value
            global_client_projections[projection.projection_type]['actual'] += projection.actual_value
    
    # Calculate global lead projections
    all_lead_projections = LeadProjection.query.filter_by(month_year=month_year).all()
    for projection in all_lead_projections:
        if projection.projection_type in global_lead_projections:
            global_lead_projections[projection.projection_type]['target'] += projection.target_value
            global_lead_projections[projection.projection_type]['actual'] += projection.actual_value
    
    # Calculate completion percentages for client and lead projections
    for projection_type in global_client_projections:
        if global_client_projections[projection_type]['target'] > 0:
            global_client_projections[projection_type]['completion'] = (
                global_client_projections[projection_type]['actual'] / global_client_projections[projection_type]['target']
            ) * 100
        else:
            global_client_projections[projection_type]['completion'] = 0
    
    for projection_type in global_lead_projections:
        if global_lead_projections[projection_type]['target'] > 0:
            global_lead_projections[projection_type]['completion'] = (
                global_lead_projections[projection_type]['actual'] / global_lead_projections[projection_type]['target']
            ) * 100
        else:
            global_lead_projections[projection_type]['completion'] = 0
    
    # Calculate GLOBAL ACTUAL VALUES (from all leads, not just projected users)
    global_actual_leads = Lead.query.filter(
        func.date(Lead.created_at) >= month_year
    ).count()
    
    global_actual_calls = Lead.query.filter(
        Lead.updated_at >= month_year,
        Lead.status != 'New'
    ).count()
    
    global_actual_conversions = Lead.query.filter(
        Lead.status.in_(['Converted', 'On Board Clients']),
        func.date(Lead.created_at) >= month_year
    ).count()
    
    global_actual_revenue = Lead.query.filter(
        func.date(Lead.created_at) >= month_year,
        Lead.revenue > 0
    ).with_entities(func.sum(Lead.revenue)).scalar() or 0
    
    # Add global actual values to global projections
    global_projections['leads']['actual'] = global_actual_leads
    global_projections['calls']['actual'] = global_actual_calls
    global_projections['conversions']['actual'] = global_actual_conversions
    global_projections['revenue']['actual'] = int(global_actual_revenue)
    
    # Recalculate global completion with actual global values
    for projection_type in global_projections:
        if global_projections[projection_type]['target'] > 0:
            global_projections[projection_type]['completion'] = (
                global_projections[projection_type]['actual'] / global_projections[projection_type]['target']
            ) * 100
        else:
            global_projections[projection_type]['completion'] = 0
    
    db.session.commit()
    
    return render_template('admin_projections.html',
                         user_projections=user_projections,
                         global_projections=global_projections,
                         global_client_projections=global_client_projections,
                         global_lead_projections=global_lead_projections,
                         selected_month=month_year,
                         current_month=current_month)

# Converted Client Management Routes
@bp.route('/converted-clients')
@login_required
@permission_required('manage_leads')
def converted_clients_management():
    """Manage converted clients"""
    clients = ConvertedClient.query.filter_by(converted_by=current_user.id).order_by(ConvertedClient.created_at.desc()).all()
    return render_template('converted_clients_management.html', clients=clients)

@bp.route('/converted-clients/create', methods=['GET', 'POST'])
@login_required
@permission_required('manage_leads')
def create_converted_client():
    """Create a new converted client"""
    if request.method == 'POST':
        client = ConvertedClient(
            company_name=request.form['company_name'],
            client_name=request.form['client_name'],
            converted_by=current_user.id,
            industry=request.form.get('industry'),
            country=request.form.get('country'),
            notes=request.form.get('notes')
        )
        db.session.add(client)
        db.session.commit()
        flash(f'Converted client "{client.client_name}" created successfully!', 'success')
        return redirect(url_for('main.converted_clients_management'))
    
    return render_template('create_converted_client.html')

@bp.route('/converted-clients/<int:client_id>')
@login_required
@permission_required('manage_leads')
def view_converted_client(client_id):
    """View converted client details and projections"""
    client = ConvertedClient.query.get_or_404(client_id)
    
    # Get current month projections
    today = date.today()
    current_month = date(today.year, today.month, 1)
    
    projections = ConvertedClientProjection.query.filter_by(
        client_id=client.id,
        month_year=current_month
    ).all()
    
    return render_template('view_converted_client.html', 
                         client=client, 
                         projections=projections,
                         current_month=current_month)

@bp.route('/converted-clients/<int:client_id>/projections/create', methods=['GET', 'POST'])
@login_required
def create_client_projection(client_id):
    """Create projection for a converted client - Only Managers can set projections"""
    client = ConvertedClient.query.get_or_404(client_id)
    
    # Only Managers can set projections for clients (not Callers)
    if not current_user.has_permission('manage_leads') or current_user.role.name == 'Caller':
        flash('Only Managers can set projections for clients.', 'error')
        return redirect(url_for('main.converted_clients_management'))
    
    if request.method == 'POST':
        projection = ConvertedClientProjection(
            client_id=client.id,
            month_year=datetime.strptime(request.form['month_year'] + '-01', '%Y-%m-%d').date(),
            projection_type=request.form['projection_type'],
            target_value=int(request.form['target_value']),
            notes=request.form.get('notes')
        )
        db.session.add(projection)
        db.session.commit()
        flash(f'Projection created for {client.client_name}!', 'success')
        return redirect(url_for('main.view_converted_client', client_id=client.id))
    
    today = date.today()
    current_month = date(today.year, today.month, 1)
    
    return render_template('create_client_projection.html', 
                         client=client,
                         current_month=current_month)

@bp.route('/admin/converted-clients')
@login_required
@permission_required('admin')
def admin_converted_clients():
    """Admin view of all converted clients"""
    clients = ConvertedClient.query.order_by(ConvertedClient.created_at.desc()).all()
    
    # Group by converter
    clients_by_user = {}
    for client in clients:
        user_id = client.converted_by
        if user_id not in clients_by_user:
            clients_by_user[user_id] = {
                'user': client.converter,
                'clients': []
            }
        clients_by_user[user_id]['clients'].append(client)
    
    return render_template('admin_converted_clients.html', clients_by_user=clients_by_user)

@bp.route('/admin/converted-clients/global-projections')
@login_required
@permission_required('admin')
def admin_converted_clients_projections():
    """Admin view of all converted client projections"""
    today = date.today()
    current_month = date(today.year, today.month, 1)
    selected_month = request.args.get('month', current_month.strftime('%Y-%m'))
    
    month_year = datetime.strptime(selected_month + '-01', '%Y-%m-%d').date()
    
    # Get all client projections for the month
    projections = ConvertedClientProjection.query.filter_by(month_year=month_year).all()
    
    # Group by client
    projections_by_client = {}
    for projection in projections:
        client_id = projection.client_id
        if client_id not in projections_by_client:
            projections_by_client[client_id] = {
                'client': projection.client,
                'projections': []
            }
        projections_by_client[client_id]['projections'].append(projection)
    
    # Calculate global totals
    global_projections = {
        'revenue': {'target': 0, 'actual': 0, 'completion': 0},
        'work_volume': {'target': 0, 'actual': 0, 'completion': 0},
        'tasks': {'target': 0, 'actual': 0, 'completion': 0}
    }
    
    for client_id, data in projections_by_client.items():
        for projection in data['projections']:
            if projection.projection_type == 'revenue':
                global_projections['revenue']['target'] += projection.target_value
                global_projections['revenue']['actual'] += projection.actual_value
            elif projection.projection_type == 'work_volume':
                global_projections['work_volume']['target'] += projection.target_value
                global_projections['work_volume']['actual'] += projection.actual_value
            elif projection.projection_type == 'tasks':
                global_projections['tasks']['target'] += projection.target_value
                global_projections['tasks']['actual'] += projection.actual_value
    
    # Calculate completion percentages
    for projection_type in global_projections:
        if global_projections[projection_type]['target'] > 0:
            global_projections[projection_type]['completion'] = (
                global_projections[projection_type]['actual'] / global_projections[projection_type]['target']
            ) * 100
        else:
            global_projections[projection_type]['completion'] = 0
    
    return render_template('admin_converted_clients_projections.html',
                         projections_by_client=projections_by_client,
                         global_projections=global_projections,
                         selected_month=month_year,
                         current_month=current_month)

# Existing Converted Lead Projections Routes
@bp.route('/converted-leads')
@login_required
@permission_required('manage_leads')
def converted_leads_management():
    """Manage existing converted leads with projections"""
    # Get all converted leads
    converted_statuses = ['Converted', 'On Board Clients']
    leads = Lead.query.filter(Lead.status.in_(converted_statuses)).order_by(Lead.created_at.desc()).all()
    
    # Get current month projections for each lead
    today = date.today()
    current_month = date(today.year, today.month, 1)
    
    leads_with_projections = []
    for lead in leads:
        projections = LeadProjection.query.filter_by(
            lead_id=lead.id,
            month_year=current_month
        ).all()
        
        leads_with_projections.append({
            'lead': lead,
            'projections': projections
        })
    
    return render_template('converted_leads_management.html', 
                         leads_with_projections=leads_with_projections,
                         current_month=current_month)

@bp.route('/converted-leads/<int:lead_id>')
@login_required
@permission_required('manage_leads')
def view_converted_lead(lead_id):
    """View converted lead details and projections"""
    lead = Lead.query.get_or_404(lead_id)
    
    # Get current month projections
    today = date.today()
    current_month = date(today.year, today.month, 1)
    
    projections = LeadProjection.query.filter_by(
        lead_id=lead.id,
        month_year=current_month
    ).all()
    
    return render_template('view_converted_lead.html', 
                         lead=lead, 
                         projections=projections,
                         current_month=current_month)

@bp.route('/converted-leads/<int:lead_id>/projections/create', methods=['GET', 'POST'])
@login_required
def create_lead_projection(lead_id):
    """Create projection for a converted lead - Only Managers can set projections"""
    lead = Lead.query.get_or_404(lead_id)
    
    # Only Managers can set projections for existing leads (not Callers)
    if not current_user.has_permission('manage_leads') or current_user.role.name == 'Caller':
        flash('Only Managers can set projections for existing converted leads.', 'error')
        return redirect(url_for('main.converted_leads_management'))
    
    if request.method == 'POST':
        projection = LeadProjection(
            lead_id=lead.id,
            month_year=datetime.strptime(request.form['month_year'] + '-01', '%Y-%m-%d').date(),
            projection_type=request.form['projection_type'],
            target_value=int(request.form['target_value']),
            notes=request.form.get('notes')
        )
        db.session.add(projection)
        db.session.commit()
        flash(f'Projection created for {lead.company_name}!', 'success')
        return redirect(url_for('main.view_converted_lead', lead_id=lead.id))
    
    today = date.today()
    current_month = date(today.year, today.month, 1)
    
    return render_template('create_lead_projection.html', 
                         lead=lead,
                         current_month=current_month)

@bp.route('/admin/converted-leads-projections')
@login_required
@permission_required('admin')
def admin_converted_leads_projections():
    """Admin view of all converted lead projections"""
    today = date.today()
    current_month = date(today.year, today.month, 1)
    selected_month = request.args.get('month', current_month.strftime('%Y-%m'))
    
    month_year = datetime.strptime(selected_month + '-01', '%Y-%m-%d').date()
    
    # Get all lead projections for the month
    projections = LeadProjection.query.filter_by(month_year=month_year).all()
    
    # Group by lead
    projections_by_lead = {}
    for projection in projections:
        lead_id = projection.lead_id
        if lead_id not in projections_by_lead:
            projections_by_lead[lead_id] = {
                'lead': projection.lead,
                'projections': []
            }
        projections_by_lead[lead_id]['projections'].append(projection)
    
    # Calculate global totals
    global_projections = {
        'revenue': {'target': 0, 'actual': 0, 'completion': 0},
        'work_volume': {'target': 0, 'actual': 0, 'completion': 0},
        'tasks': {'target': 0, 'actual': 0, 'completion': 0}
    }
    
    for lead_id, data in projections_by_lead.items():
        for projection in data['projections']:
            if projection.projection_type == 'revenue':
                global_projections['revenue']['target'] += projection.target_value
                global_projections['revenue']['actual'] += projection.actual_value
            elif projection.projection_type == 'work_volume':
                global_projections['work_volume']['target'] += projection.target_value
                global_projections['work_volume']['actual'] += projection.actual_value
            elif projection.projection_type == 'tasks':
                global_projections['tasks']['target'] += projection.target_value
                global_projections['tasks']['actual'] += projection.actual_value
    
    # Calculate completion percentages
    for projection_type in global_projections:
        if global_projections[projection_type]['target'] > 0:
            global_projections[projection_type]['completion'] = (
                global_projections[projection_type]['actual'] / global_projections[projection_type]['target']
            ) * 100
        else:
            global_projections[projection_type]['completion'] = 0
    
    return render_template('admin_converted_leads_projections.html',
                         projections_by_lead=projections_by_lead,
                         global_projections=global_projections,
                         selected_month=month_year,
                         current_month=current_month) 

@bp.route('/admin/production')
@login_required
@permission_required('admin')
def admin_production_dashboard():
    """Admin dashboard for global Production data."""
    
    # Get Production team members
    production_users = User.query.join(Role).filter(Role.name == 'Production').all()
    
    # Get all Production tasks
    all_tasks = ProductionTask.query.all()
    
    # Get task statistics
    total_tasks = len(all_tasks)
    pending_tasks = len([t for t in all_tasks if t.status == 'pending'])
    in_progress_tasks = len([t for t in all_tasks if t.status == 'in_progress'])
    completed_tasks = len([t for t in all_tasks if t.status == 'completed'])
    
    # Get file upload statistics
    total_uploads = TaskAttachment.query.count()
    dropbox_uploads = DropboxUpload.query.count()
    lan_accesses = LANServerFile.query.count()
    
    # Get recent activities
    recent_tasks = ProductionTask.query.order_by(ProductionTask.created_at.desc()).limit(10).all()
    recent_uploads = TaskAttachment.query.order_by(TaskAttachment.uploaded_at.desc()).limit(10).all()
    recent_lan_access = LANServerFile.query.order_by(LANServerFile.last_accessed.desc()).limit(10).all()
    
    # Get task distribution by user
    task_by_user = {}
    for user in production_users:
        user_tasks = ProductionTask.query.filter_by(assigned_to=user.id).all()
        task_by_user[user.get_full_name()] = {
            'total': len(user_tasks),
            'pending': len([t for t in user_tasks if t.status == 'pending']),
            'in_progress': len([t for t in user_tasks if t.status == 'in_progress']),
            'completed': len([t for t in user_tasks if t.status == 'completed'])
        }
    
    # Get task distribution by priority
    priority_stats = {
        'low': len([t for t in all_tasks if t.priority == 'low']),
        'medium': len([t for t in all_tasks if t.priority == 'medium']),
        'high': len([t for t in all_tasks if t.priority == 'high']),
        'urgent': len([t for t in all_tasks if t.priority == 'urgent'])
    }
    
    # Get task distribution by type
    task_type_stats = {}
    for task in all_tasks:
        task_type_stats[task.task_type] = task_type_stats.get(task.task_type, 0) + 1
    
    # Get completion rate
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    # Get average task completion time
    completed_tasks_with_time = [t for t in all_tasks if t.completed_at and t.created_at]
    avg_completion_time = None
    if completed_tasks_with_time:
        total_time = sum((t.completed_at - t.created_at).total_seconds() for t in completed_tasks_with_time)
        avg_completion_time = total_time / len(completed_tasks_with_time) / 3600  # Convert to hours
    
    return render_template('admin/production_dashboard.html',
                         production_users=production_users,
                         total_tasks=total_tasks,
                         pending_tasks=pending_tasks,
                         in_progress_tasks=in_progress_tasks,
                         completed_tasks=completed_tasks,
                         total_uploads=total_uploads,
                         dropbox_uploads=dropbox_uploads,
                         lan_accesses=lan_accesses,
                         recent_tasks=recent_tasks,
                         recent_uploads=recent_uploads,
                         recent_lan_access=recent_lan_access,
                         task_by_user=task_by_user,
                         priority_stats=priority_stats,
                         task_type_stats=task_type_stats,
                         completion_rate=completion_rate,
                         avg_completion_time=avg_completion_time)

@bp.route('/api/desktop-activity', methods=['POST'])
def api_desktop_activity():
    data = request.get_json()
    user_id = data.get('user_id')
    events = data.get('events', [])
    if not user_id or not events:
        return jsonify({'error': 'Missing user_id or events'}), 400

    from .models import DesktopActivity, db
    from datetime import datetime

    for event in events:
        # ActivityWatch event: {"timestamp": ..., "data": {"app": ..., "title": ..., ...}, ...}
        activity = DesktopActivity(
            user_id=user_id,
            timestamp=datetime.fromisoformat(event['timestamp']) if 'timestamp' in event else datetime.now(timezone.utc),
            app=event['data'].get('app', ''),
            title=event['data'].get('title', ''),
            duration=event['data'].get('duration', 0),
            activity_type=event.get('activity_type', 'window')
        )
        db.session.add(activity)
    db.session.commit()
    return jsonify({"status": "success"})