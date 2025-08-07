# app.py

import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, time

# --- Konfigurasi Aplikasi ---
app = Flask(__name__)
# Path untuk database SQLite di dalam folder 'instance'
db_path = os.path.join(os.path.dirname(app.instance_path), 'instance', 'logbook.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'kunci-rahasia-yang-sangat-aman-ganti-nanti' # Ganti dengan kunci rahasia Anda

# --- Inisialisasi Database ---
# Impor model setelah konfigurasi
from app.models import db, LogbookEntry, Personnel, Facility, FacilityStatus, OperationalLog

# Inisialisasi app dengan ekstensi SQLAlchemy
db.init_app(app)

# --- Routes (URL Endpoints) ---

@app.route('/')
def dashboard():
    """Menampilkan halaman dashboard dengan daftar semua entri logbook."""
    try:
        # Mengambil semua entri logbook, diurutkan dari yang terbaru
        log_entries = LogbookEntry.query.order_by(LogbookEntry.log_date.desc(), LogbookEntry.id.desc()).all()
        return render_template('dashboard.html', log_entries=log_entries)
    except Exception as e:
        # Jika tabel belum ada, tampilkan halaman kosong
        # Ini berguna saat pertama kali menjalankan aplikasi
        flash(f"Error loading dashboard, database might be empty. Try creating a new log. Error: {e}", "warning")
        return render_template('dashboard.html', log_entries=[])


@app.route('/log/new', methods=['GET', 'POST'])
def create_log_entry():
    """Menampilkan form untuk membuat entri baru dan memprosesnya."""
    if request.method == 'POST':
        try:
            # 1. Membuat entri logbook utama
            log_date_str = request.form.get('log_date')
            new_log = LogbookEntry(
                log_date=datetime.strptime(log_date_str, '%Y-%m-%d').date(),
                shift=request.form.get('shift'),
                notam=request.form.get('notam')
                # Untuk position_seat_schedule, Anda perlu logika tambahan untuk mengumpulkannya dari form
            )
            db.session.add(new_log)
            # Commit awal untuk mendapatkan ID dari new_log
            db.session.commit()

            # 2. Menambahkan status fasilitas
            facilities = Facility.query.all()
            for facility in facilities:
                condition = request.form.get(f'facility_{facility.id}_condition')
                notes = request.form.get(f'facility_{facility.id}_notes')
                if condition:
                    status = FacilityStatus(
                        logbook_id=new_log.id,
                        facility_id=facility.id,
                        condition=condition,
                        notes=notes
                    )
                    db.session.add(status)
            
            # 3. Menambahkan log operasional
            # Ini memerlukan JavaScript di frontend untuk menambahkan baris secara dinamis
            # Asumsi kita mendapatkan list dari form
            descriptions = request.form.getlist('op_description[]')
            event_times = request.form.getlist('op_time[]')
            remarks = request.form.getlist('op_remarks[]')
            
            for i in range(len(descriptions)):
                if descriptions[i]: # Hanya jika deskripsi tidak kosong
                    event_time_obj = datetime.strptime(event_times[i], '%H:%M').time()
                    op_log = OperationalLog(
                        logbook_id=new_log.id,
                        event_time=event_time_obj,
                        description=descriptions[i],
                        remarks=remarks[i]
                    )
                    db.session.add(op_log)

            # Commit semua perubahan ke database
            db.session.commit()
            flash('Logbook entry created successfully!', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            db.session.rollback() # Batalkan transaksi jika terjadi error
            flash(f'Error creating log entry: {e}', 'danger')

    # Untuk method GET, tampilkan form
    facilities = Facility.query.all()
    return render_template('create_log.html', facilities=facilities)

# Fungsi untuk membuat database dan data awal (jika diperlukan)
def setup_database(app):
    with app.app_context():
        db.create_all()
        
        # Contoh menambahkan data fasilitas jika tabelnya kosong
        if Facility.query.count() == 0:
            initial_facilities = [
                # Internal Facilities
                Facility(name='VCCS - GAREX', category='Internal'),
                Facility(name='VHF - PARK AIR S4', category='Internal'),
                Facility(name='Air Situation Display (ASD)', category='Internal'),
                # Tambahkan semua fasilitas dari PDF di sini...
                # Airfield Lighting
                Facility(name='PAPI Light', category='ALS'),
                Facility(name='Runway Edge Light', category='ALS'),
            ]
            db.session.bulk_save_objects(initial_facilities)
            db.session.commit()
            print("Initial facilities have been added to the database.")

if __name__ == '__main__':
    # Pastikan folder instance ada
    if not os.path.exists(os.path.join(os.path.dirname(app.instance_path), 'instance')):
        os.makedirs(os.path.join(os.path.dirname(app.instance_path), 'instance'))
    
    # Setup database
    setup_database(app)
    
    # Menjalankan aplikasi
    app.run(debug=True)
