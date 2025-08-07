# app/routes.py

import os
import calendar
from flask import render_template, request, redirect, url_for, flash, Blueprint, current_app, session
from flask_login import login_required, current_user
from .models import (db, User, LogbookEntry, Facility, FacilityApp, FacilityStatus, OperationalLog, ATCPosition, 
                     ATCPositionHeader, CNSDLogbook, CNSDPersonnel, 
                     CNSDFacility, CNSDFacilityStatus, CNSDUraianKegiatan, ATCPersonnel, FacilityCondition)
from datetime import datetime, timedelta
from collections import OrderedDict, defaultdict
from flask_weasyprint import HTML, render_pdf
from werkzeug.utils import secure_filename
import sqlalchemy as sa

main_bp = Blueprint('main', __name__)

def allowed_file(filename):
    """Memeriksa apakah ekstensi file diizinkan."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def get_ordered_facilities(logbook_type='TWR'):
    """Mengambil dan mengurutkan fasilitas berdasarkan tipe logbook."""
    if logbook_type == 'APP':
        all_facilities = FacilityApp.query.all()
        category_order = ['COM. & NAV.', 'FACILITIES']
    else: # Default ke TWR
        all_facilities = Facility.query.all()
        category_order = [
            'Internal Facilities - COM. & NAV.', 'Internal Support Facility',
            'External Support Facilities', 'Airfield Lighting Control System (ALS Cat.1)'
        ]

    grouped = OrderedDict([(cat, []) for cat in category_order])
    for f in all_facilities:
        if f.category in grouped:
            grouped[f.category].append(f)
    
    return grouped

def parse_duration(time_str: str) -> timedelta:
    """Menghitung durasi dari string format 'HH:MM-HH:MM'."""
    if not time_str or '-' not in time_str:
        return timedelta(0)
    try:
        start_str, end_str = time_str.split('-')
        start_time = datetime.strptime(start_str.strip(), '%H:%M').time()
        end_time = datetime.strptime(end_str.strip(), '%H:%M').time()
        
        start_dt = datetime.combine(datetime.today(), start_time)
        end_dt = datetime.combine(datetime.today(), end_time)

        if end_dt < start_dt:
            end_dt += timedelta(days=1)
            
        return end_dt - start_dt
    except (ValueError, IndexError):
        return timedelta(0)

def get_cnsd_facilities_ordered(airport_code):
    """Mengambil dan mengurutkan fasilitas CNSD berdasarkan bandara dan kategori."""
    all_facilities = CNSDFacility.query.filter_by(airport_code=airport_code).all()
    
    # Tentukan urutan kategori yang diinginkan
    category_order = ['COMMUNICATION', 'NAVIGATION', 'SURVEILLANCE', 'DATA PROCESSING']
    
    # Gunakan OrderedDict untuk menjaga urutan kategori
    grouped = OrderedDict([(cat, []) for cat in category_order])
    
    # Kelompokkan fasilitas ke dalam kategori yang sesuai
    for f in all_facilities:
        if f.category in grouped:
            grouped[f.category].append(f)
            
    return grouped


# --- RUTE UTAMA & OPERASI ---

@main_bp.route('/')
@login_required
def index():
    if current_user.division == 'operasi':
        return redirect(url_for('main.dashboard_operasi'))
    elif current_user.division == 'teknik':
        return redirect(url_for('main.dashboard_teknik'))
    return "Unknown division", 403

@main_bp.route('/dashboard/operasi')
@login_required
def dashboard_operasi():
    logbook_type = request.args.get('type', 'TWR')
    active_tab = request.args.get('tab', 'history')
    
    # --- LOGIKA UNTUK TAB LOGBOOK HISTORY ---
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    log_entries = []
    if active_tab == 'history':
        query = LogbookEntry.query.filter_by(logbook_type=logbook_type)
        if start_date_str:
            query = query.filter(LogbookEntry.log_date >= datetime.strptime(start_date_str, '%Y-%m-%d').date())
        if end_date_str:
            query = query.filter(LogbookEntry.log_date <= datetime.strptime(end_date_str, '%Y-%m-%d').date())
        log_entries = query.order_by(LogbookEntry.log_date.desc()).all()

    # --- LOGIKA UNTUK TAB PERSONNEL RECAP ---
    recap_data = []
    current_time = datetime.now()
    recap_month_str = request.args.get('recap_month', str(current_time.month))
    recap_year_str = request.args.get('recap_year', str(current_time.year))
    if active_tab == 'recap':
        recap_month = int(recap_month_str)
        recap_year = int(recap_year_str)
        logs_in_month = LogbookEntry.query.filter(
            sa.extract('month', LogbookEntry.log_date) == recap_month,
            sa.extract('year', LogbookEntry.log_date) == recap_year
        ).all()
        
        personnel_days = defaultdict(set)
        for log in logs_in_month:
            for person in log.atc_on_duty_personnel:
                personnel_days[person.name].add(log.log_date)

        personnel_hours = defaultdict(timedelta)
        log_ids_in_month = [log.id for log in logs_in_month]
        positions_in_month = ATCPosition.query.filter(ATCPosition.logbook_id.in_(log_ids_in_month)).all()
        
        for pos in positions_in_month:
            header = pos.logbook_entry.atc_position_header
            if not header: continue
            for i in range(1, 7):
                person_name = getattr(pos, f'time_slot_{i}', None)
                time_header = getattr(header, f'header_{i}', None)
                if person_name and time_header:
                    personnel_hours[person_name] += parse_duration(time_header)

        all_personnel = ATCPersonnel.query.order_by(ATCPersonnel.name).all()
        for person in all_personnel:
            total_days = len(personnel_days.get(person.name, set()))
            total_hours = personnel_hours.get(person.name, timedelta(0)).total_seconds() / 3600
            recap_data.append({'name': person.name, 'days': total_days, 'hours': round(total_hours, 2)})

    # --- LOGIKA UNTUK TAB PERSONAL ATC LOGBOOK ---
    personal_log_data = {}
    personal_log_summary = {}
    all_atc_personnel = ATCPersonnel.query.order_by(ATCPersonnel.name).all()
    
    selected_personnel_id = request.args.get('personnel_id', type=int)
    personal_month_str = request.args.get('personal_month', str(current_time.month))
    personal_year_str = request.args.get('personal_year', str(current_time.year))

    if active_tab == 'personal' and selected_personnel_id:
        selected_personnel = ATCPersonnel.query.get(selected_personnel_id)
        if selected_personnel:
            personal_month = int(personal_month_str)
            personal_year = int(personal_year_str)
            
            logs_in_month = LogbookEntry.query.filter(
                sa.extract('month', LogbookEntry.log_date) == personal_month,
                sa.extract('year', LogbookEntry.log_date) == personal_year
            ).all()
            
            log_ids = [log.id for log in logs_in_month]
            
            duty_records = []
            positions_in_month = ATCPosition.query.filter(ATCPosition.logbook_id.in_(log_ids)).all()

            for pos in positions_in_month:
                for i in range(1, 7):
                    person_name_in_slot = getattr(pos, f'time_slot_{i}')
                    if person_name_in_slot == selected_personnel.name:
                        log_entry = pos.logbook_entry
                        header = log_entry.atc_position_header
                        duration_str = getattr(header, f'header_{i}') if header else None
                        
                        if duration_str:
                            duty_records.append({
                                'date': log_entry.log_date,
                                'shift': log_entry.shift, # <-- Baris ini ditambahkan
                                'unit': log_entry.logbook_type,
                                'position': pos.position_name,
                                'duration': parse_duration(duration_str)
                            })
            
            grouped_duties = defaultdict(list)
            for record in duty_records:
                grouped_duties[record['date'].day].append(record)
            
            total_ctr_duration = timedelta(0)
            total_ass_duration = timedelta(0)
            ctr_positions = ['Controller', 'CONTROLLER RADAR 123.4 Mhz', 'CONTROLLER RADAR 120.2 Mhz']
            ass_positions = ['Supervisor', 'ASSISTANCE RADAR 123.4 Mhz', 'ASSISTANCE RADAR 120.2 Mhz']

            for record in duty_records:
                if record['position'] in ctr_positions:
                    total_ctr_duration += record['duration']
                elif record['position'] in ass_positions:
                    total_ass_duration += record['duration']
            
            personal_log_data = dict(sorted(grouped_duties.items()))
            personal_log_summary = {
                'selected_personnel_name': selected_personnel.name,
                'total_ctr_hours': round(total_ctr_duration.total_seconds() / 3600, 2),
                'total_ass_hours': round(total_ass_duration.total_seconds() / 3600, 2),
                'grand_total_hours': round((total_ctr_duration + total_ass_duration).total_seconds() / 3600, 2),
                'num_days': calendar.monthrange(personal_year, personal_month)[1]
            }

    return render_template(
        'dashboard.html', 
        log_entries=log_entries, 
        title=f"{'Approach Control Unit' if logbook_type == 'APP' else 'Aerodrome Control Tower'} Dashboard", 
        start_date=start_date_str, 
        end_date=end_date_str, 
        active_tab=active_tab, 
        recap_data=recap_data, 
        recap_month=int(recap_month_str), 
        recap_year=int(recap_year_str), 
        logbook_type=logbook_type,
        all_atc_personnel=all_atc_personnel,
        selected_personnel_id=selected_personnel_id,
        personal_month=int(personal_month_str),
        personal_year=int(personal_year_str),
        personal_log_data=personal_log_data,
        personal_log_summary=personal_log_summary
    )

@main_bp.route('/log/new/<string:logbook_type>', methods=['GET', 'POST'])
@login_required
def create_log_entry(logbook_type):
    if logbook_type not in ['TWR', 'APP']:
        return redirect(url_for('main.dashboard_operasi'))

    if request.method == 'POST':
        try:
            new_log = LogbookEntry(logbook_type=logbook_type, log_date=datetime.strptime(request.form['log_date'], '%Y-%m-%d').date(), shift=request.form['shift'], notam=request.form.get('notam'), user_id=current_user.id)
            for p_id in request.form.getlist('atc_on_duty_personnel[]'):
                if p_id and (personnel := ATCPersonnel.query.get(p_id)):
                    new_log.atc_on_duty_personnel.append(personnel)
            db.session.add(new_log)
            db.session.flush()

            header = ATCPositionHeader(logbook_entry=new_log)
            for i in range(1, 7):
                setattr(header, f'header_{i}', request.form.get(f'time_header_{i}'))
            db.session.add(header)
            
            positions = [
                "SUPERVISOR", "CONTROLLER RADAR 123.4 Mhz", "ASSISTANCE RADAR 123.4 Mhz",
                "CONTROLLER RADAR 120.2 Mhz", "ASSISTANCE RADAR 120.2 Mhz", "REST"
            ] if logbook_type == 'APP' else ['Controller', 'Supervisor', 'Rest']
            
            for position_name in positions:
                pos_key = position_name.replace(" ", "_").replace(".", "").lower()
                pos_entry = ATCPosition(logbook_entry=new_log, position_name=position_name)
                for i in range(1, 7):
                    setattr(pos_entry, f'time_slot_{i}', request.form.get(f'position_{pos_key}_{i}'))
                db.session.add(pos_entry)
            
            FacilityModel = FacilityApp if logbook_type == 'APP' else Facility
            for facility in FacilityModel.query.all():
                if condition_val := request.form.get(f'facility_{facility.id}_condition'):
                    db.session.add(FacilityStatus(logbook_entry=new_log, facility_id=facility.id, facility_type=logbook_type, condition=condition_val, notes=request.form.get(f'facility_{facility.id}_notes')))

            for key in [k for k in request.form.keys() if k.startswith('op_log_time_')]:
                index = key.replace('op_log_time_', '')
                if (time_val := request.form.get(f'op_log_time_{index}')) and (desc_val := request.form.get(f'op_log_desc_{index}')):
                    db.session.add(OperationalLog(logbook_entry=new_log, event_time=datetime.strptime(time_val, '%H:%M').time(), description=desc_val, remarks=request.form.get(f'op_log_remarks_{index}')))

            for field_name in ['controller_signature_1', 'controller_signature_2', 'manager_signature']:
                if (file := request.files.get(field_name)) and allowed_file(file.filename):
                    filename = f"ops_{field_name}_{new_log.id}_{secure_filename(file.filename)}"
                    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                    setattr(new_log, field_name, filename)

            db.session.commit()
            flash('Log entry created successfully!', 'success')
            return redirect(url_for('main.dashboard_operasi', type=logbook_type))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {e}', 'danger')

    template_name = 'create_log_app.html' if logbook_type == 'APP' else 'create_log.html'
    title = "Create New Approach Control Unit Log" if logbook_type == 'APP' else "Create New Aerodrome Control Tower Log"
    
    return render_template(
        template_name, 
        grouped_facilities=get_ordered_facilities(logbook_type), 
        atc_personnel_list=ATCPersonnel.query.order_by(ATCPersonnel.name).all(), 
        title=title, 
        logbook_type=logbook_type,
        FacilityCondition=FacilityCondition
    )

@main_bp.route('/log/edit/<int:log_id>', methods=['GET', 'POST'])
@login_required
def edit_log(log_id):
    log_entry = LogbookEntry.query.get_or_404(log_id)
    logbook_type = log_entry.logbook_type
    
    if current_user.id != log_entry.creator.id:
        flash('You are not authorized to edit this log entry.', 'danger')
        return redirect(url_for('main.dashboard_operasi', type=logbook_type))
        
    if request.method == 'POST':
        try:
            log_entry.log_date = datetime.strptime(request.form['log_date'], '%Y-%m-%d').date()
            log_entry.shift = request.form['shift']
            log_entry.notam = request.form.get('notam')
            
            log_entry.atc_on_duty_personnel.clear()
            for p_id in request.form.getlist('atc_on_duty_personnel[]'):
                if p_id and (personnel := ATCPersonnel.query.get(p_id)):
                    log_entry.atc_on_duty_personnel.append(personnel)
            
            header = log_entry.atc_position_header or ATCPositionHeader(logbook_entry=log_entry)
            for i in range(1, 7): setattr(header, f'header_{i}', request.form.get(f'time_header_{i}'))
            db.session.add(header)
            
            atc_positions_map = {pos.position_name: pos for pos in log_entry.atc_positions}
            positions = [
                "SUPERVISOR", "CONTROLLER RADAR 123.4 Mhz", "ASSISTANCE RADAR 123.4 Mhz",
                "CONTROLLER RADAR 120.2 Mhz", "ASSISTANCE RADAR 120.2 Mhz", "REST"
            ] if logbook_type == 'APP' else ['Controller', 'Supervisor', 'Rest']
            for position_name in positions:
                pos_key = position_name.replace(" ", "_").replace(".", "").lower()
                pos_entry = atc_positions_map.get(position_name) or ATCPosition(logbook_entry=log_entry, position_name=position_name)
                for i in range(1, 7): setattr(pos_entry, f'time_slot_{i}', request.form.get(f'position_{pos_key}_{i}'))
                db.session.add(pos_entry)

            statuses_map = {(status.facility_id, status.facility_type): status for status in log_entry.facility_statuses}
            FacilityModel = FacilityApp if logbook_type == 'APP' else Facility
            for facility in FacilityModel.query.all():
                if condition_val := request.form.get(f'facility_{facility.id}_condition'):
                    status_key = (facility.id, logbook_type)
                    if status := statuses_map.get(status_key):
                        status.condition = condition_val
                        status.notes = request.form.get(f'facility_{facility.id}_notes')
                    else:
                        db.session.add(FacilityStatus(logbook_id=log_id, facility_id=facility.id, facility_type=logbook_type, condition=condition_val, notes=request.form.get(f'facility_{facility.id}_notes')))

            OperationalLog.query.filter_by(logbook_id=log_id).delete()
            for key in [k for k in request.form.keys() if k.startswith('op_log_time_')]:
                index = key.replace('op_log_time_', '')
                if (time_val := request.form.get(f'op_log_time_{index}')) and (desc_val := request.form.get(f'op_log_desc_{index}')):
                    db.session.add(OperationalLog(logbook_id=log_id, event_time=datetime.strptime(time_val, '%H:%M').time(), description=desc_val, remarks=request.form.get(f'op_log_remarks_{index}')))

            for field_name in ['controller_signature_1', 'controller_signature_2', 'manager_signature']:
                if (file := request.files.get(field_name)) and allowed_file(file.filename):
                    if old_filename := getattr(log_entry, field_name):
                        try: os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], old_filename))
                        except OSError: pass
                    filename = f"ops_{field_name}_{log_entry.id}_{secure_filename(file.filename)}"
                    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                    setattr(log_entry, field_name, filename)

            db.session.commit()
            flash('Log entry updated successfully!', 'success')
            return redirect(url_for('main.view_log', log_id=log_id))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred during update: {e}', 'danger')

    template_name = 'edit_log_app.html' if logbook_type == 'APP' else 'edit_log.html'
    title = "Edit Approach Control Unit Log" if logbook_type == 'APP' else "Edit Aerodrome Control Tower Log"
    
    return render_template(
        template_name,
        log=log_entry,
        grouped_facilities=get_ordered_facilities(logbook_type),
        atc_positions={pos.position_name: pos for pos in log_entry.atc_positions},
        FacilityCondition=FacilityCondition,
        atc_personnel_list=ATCPersonnel.query.order_by(ATCPersonnel.name).all(),
        title=title
    )

@main_bp.route('/log/view/<int:log_id>')
@login_required
def view_log(log_id):
    log_entry = LogbookEntry.query.get_or_404(log_id)
    logbook_type = log_entry.logbook_type
    
    template_name = 'view_log_app.html' if logbook_type == 'APP' else 'view_log.html'
    title = "View Approach Control Unit Log" if logbook_type == 'APP' else "View Aerodrome Control Tower Log"

    return render_template(
        template_name,
        log=log_entry,
        grouped_facilities=get_ordered_facilities(logbook_type),
        atc_positions={pos.position_name: pos for pos in log_entry.atc_positions},
        FacilityCondition=FacilityCondition,
        title=title
    )

@main_bp.route('/log/download/<int:log_id>')
@login_required
def download_log_pdf(log_id):
    log_entry = LogbookEntry.query.get_or_404(log_id)
    logbook_type = log_entry.logbook_type

    logo_path = os.path.join(current_app.static_folder, 'img', 'airnav.png')
    
    signature_paths = {
        'controller_1': os.path.join(current_app.config['UPLOAD_FOLDER'], log_entry.controller_signature_1) if log_entry.controller_signature_1 else None,
        'controller_2': os.path.join(current_app.config['UPLOAD_FOLDER'], log_entry.controller_signature_2) if log_entry.controller_signature_2 else None,
        'manager': os.path.join(current_app.config['UPLOAD_FOLDER'], log_entry.manager_signature) if log_entry.manager_signature else None,
    }

    template_name = 'log_pdf_app.html' if logbook_type == 'APP' else 'log_pdf.html'
    
    html = render_template(
        template_name,
        log=log_entry,
        grouped_facilities=get_ordered_facilities(logbook_type),
        atc_positions={pos.position_name: pos for pos in log_entry.atc_positions},
        FacilityCondition=FacilityCondition,
        logo_path=logo_path,
        signature_paths=signature_paths
    )
    return render_pdf(HTML(string=html))

# --- RUTE TEKNIK (Tidak ada perubahan signifikan) ---

@main_bp.route('/dashboard/teknik')
@login_required
def dashboard_teknik():
    if current_user.division != 'teknik':
        flash('Anda tidak memiliki akses ke halaman ini.', 'danger')
        return redirect(url_for('main.index'))
    return render_template('dashboard_teknik.html', title="Pilih Bandara CNSD")

@main_bp.route('/cnsd/unlock', methods=['POST'])
@login_required
def unlock_cnsd_logbook():
    airport_code = request.form.get('airport_code')
    password = request.form.get('airport_password')
    correct_password = current_app.config['AIRPORT_PASSWORDS'].get(airport_code)
    
    if password == correct_password:
        session['unlocked_airport'] = airport_code
        return redirect(url_for('main.cnsd_dashboard', airport_code=airport_code))
    else:
        flash('Kata sandi salah. Coba lagi.', 'danger')
        return redirect(url_for('main.dashboard_teknik'))

@main_bp.route('/cnsd/dashboard/<string:airport_code>')
@login_required
def cnsd_dashboard(airport_code):
    if session.get('unlocked_airport') != airport_code:
        flash('Akses ditolak. Silakan masukkan kata sandi yang benar.', 'warning')
        return redirect(url_for('main.dashboard_teknik'))
        
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    query = CNSDLogbook.query.filter_by(airport=airport_code)
    
    if start_date_str:
        query = query.filter(CNSDLogbook.log_date >= datetime.strptime(start_date_str, '%Y-%m-%d').date())
    if end_date_str:
        query = query.filter(CNSDLogbook.log_date <= datetime.strptime(end_date_str, '%Y-%m-%d').date())

    log_entries = query.order_by(CNSDLogbook.log_date.desc()).all()
    
    return render_template(
        'cnsd_dashboard.html', 
        log_entries=log_entries, 
        airport_code=airport_code,
        title=f"Dashboard CNSD - {airport_code}",
        start_date=start_date_str,
        end_date=end_date_str
    )

@main_bp.route('/cnsd/log/new/<string:airport_code>', methods=['GET', 'POST'])
@login_required
def create_cnsd_log(airport_code):
    if session.get('unlocked_airport') != airport_code:
        return redirect(url_for('main.dashboard_teknik'))

    if request.method == 'POST':
        try:
            new_log = CNSDLogbook(
                airport=airport_code,
                log_date=datetime.strptime(request.form['log_date'], '%Y-%m-%d').date(),
                shift=request.form['shift'],
                user_id=current_user.id
            )
            db.session.add(new_log)
            db.session.flush()

            if 'manager_signature' in request.files:
                file = request.files['manager_signature']
                if file and allowed_file(file.filename):
                    filename = f"manager_{new_log.id}_{secure_filename(file.filename)}"
                    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                    new_log.manager_signature = filename

            personnel_names = request.form.getlist('personnel_name[]')
            personnel_signatures = request.files.getlist('personnel_signature[]')
            for i, name in enumerate(personnel_names):
                if name:
                    personnel = CNSDPersonnel(cnsd_logbook_id=new_log.id, name=name)
                    if i < len(personnel_signatures) and personnel_signatures[i] and allowed_file(personnel_signatures[i].filename):
                        sig_file = personnel_signatures[i]
                        sig_filename = f"personnel_{new_log.id}_{i}_{secure_filename(sig_file.filename)}"
                        sig_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], sig_filename))
                        personnel.signature_path = sig_filename
                    db.session.add(personnel)

            facilities = CNSDFacility.query.filter_by(airport_code=airport_code).all()
            for facility in facilities:
                condition = request.form.get(f'facility_{facility.id}_condition')
                if condition:
                    status = CNSDFacilityStatus(cnsd_logbook_id=new_log.id, cnsd_facility_id=facility.id, condition=condition)
                    db.session.add(status)

            event_times = request.form.getlist('event_time[]')
            descriptions = request.form.getlist('description[]')
            for i, time in enumerate(event_times):
                if time and descriptions[i]:
                    uraian = CNSDUraianKegiatan(cnsd_logbook_id=new_log.id, event_time=time, description=descriptions[i])
                    db.session.add(uraian)

            db.session.commit()
            flash('Logbook CNSD berhasil dibuat!', 'success')
            return redirect(url_for('main.cnsd_dashboard', airport_code=airport_code))
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi error: {e}', 'danger')
            return redirect(url_for('main.create_cnsd_log', airport_code=airport_code))

    grouped_facilities = get_cnsd_facilities_ordered(airport_code)
    return render_template('create_cnsd_log.html', grouped_facilities=grouped_facilities, airport_code=airport_code, title=f"Buat Logbook CNSD - {airport_code}")

@main_bp.route('/cnsd/log/view/<int:log_id>')
@login_required
def view_cnsd_log(log_id):
    log = CNSDLogbook.query.get_or_404(log_id)
    if session.get('unlocked_airport') != log.airport:
        return redirect(url_for('main.dashboard_teknik'))
    
    grouped_facilities = get_cnsd_facilities_ordered(log.airport)
    return render_template('view_cnsd_log.html', log=log, grouped_facilities=grouped_facilities, title=f"Lihat Logbook CNSD #{log.id}")

@main_bp.route('/cnsd/log/edit/<int:log_id>', methods=['GET', 'POST'])
@login_required
def edit_cnsd_log(log_id):
    log = CNSDLogbook.query.get_or_404(log_id)
    if session.get('unlocked_airport') != log.airport:
        return redirect(url_for('main.dashboard_teknik'))
        
    if request.method == 'POST':
        try:
            log.log_date = datetime.strptime(request.form['log_date'], '%Y-%m-%d').date()
            log.shift = request.form['shift']
            db.session.commit()
            flash('Logbook CNSD berhasil diperbarui!', 'success')
            return redirect(url_for('main.cnsd_dashboard', airport_code=log.airport))
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi error saat memperbarui: {e}', 'danger')
            return redirect(url_for('main.edit_cnsd_log', log_id=log_id))

    grouped_facilities = get_cnsd_facilities_ordered(log.airport)
    return render_template('edit_cnsd_log.html', log=log, grouped_facilities=grouped_facilities, title=f"Edit Logbook CNSD #{log.id}")

@main_bp.route('/cnsd/log/download/<int:log_id>')
@login_required
def download_cnsd_log_pdf(log_id):
    log = CNSDLogbook.query.get_or_404(log_id)
    if session.get('unlocked_airport') != log.airport:
        return redirect(url_for('main.dashboard_teknik'))
        
    logo_path = os.path.join(current_app.static_folder, 'img', 'airnav.png')
    
    airport_full_names = {
        'YIA': 'BANDAR UDARA INTERNASIONAL YOGYAKARTA KULONPROGO',
        'Adisutjipto': 'BANDAR UDARA ADISUTJIPTO',
        'AdiSoemarmo': 'BANDAR UDARA INTERNASIONAL ADI SOEMARMO',
        'TunggulWulung': 'BANDAR UDARA TUNGGUL WULUNG'
    }
    
    signature_paths = {}
    if log.manager_signature:
        signature_paths['manager'] = os.path.join(current_app.config['UPLOAD_FOLDER'], log.manager_signature)
    for p in log.personnel:
        if p.signature_path:
            signature_paths[f'personnel_{p.id}'] = os.path.join(current_app.config['UPLOAD_FOLDER'], p.signature_path)

    grouped_facilities = get_cnsd_facilities_ordered(log.airport)
    html = render_template(
        'cnsd_log_pdf.html', 
        log=log, 
        logo_path=logo_path, 
        signature_paths=signature_paths, 
        grouped_facilities=grouped_facilities,
        airport_full_name=airport_full_names.get(log.airport, log.airport)
    )
    return render_pdf(HTML(string=html))
