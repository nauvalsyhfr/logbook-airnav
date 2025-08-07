# app/__init__.py

import os
import calendar
from flask import Flask
from config import Config
from .models import db, User, Facility, FacilityApp, CNSDFacility, ATCPersonnel
from flask_login import LoginManager

# ... (fungsi month_name_filter tidak berubah) ...
def month_name_filter(month_number):
    month_names_id = [
        "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]
    try:
        return month_names_id[int(month_number)]
    except (IndexError, ValueError):
        return ""

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login' 
    login_manager.login_message = "Silakan login untuk mengakses halaman ini."
    login_manager.login_message_category = "warning"

    app.jinja_env.filters['month_name'] = month_name_filter

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        from . import routes
        from . import auth
        app.register_blueprint(routes.main_bp)
        app.register_blueprint(auth.auth_bp)
        
        db.create_all()

        create_initial_users()
        seed_initial_data()
        # --- PERUBAHAN: Memanggil fungsi seed yang telah diperbarui ---
        seed_app_facilities()
        seed_cnsd_facilities()
        seed_adisucipto_facilities()
        seed_adi_soemarmo_facilities()
        seed_tunggul_wulung_facilities()
        seed_atc_personnel()

        return app

# --- PERUBAHAN: Memperbarui daftar fasilitas sesuai gambar terbaru ---
def seed_app_facilities():
    """Mengisi data awal untuk fasilitas Approach Control Unit (APP) sesuai gambar."""
    # Hapus data lama untuk memastikan data baru yang di-seed
    FacilityApp.query.delete()
    db.session.commit()

    if FacilityApp.query.count() == 0:
        print("Mengisi data fasilitas Approach Control Unit (APP) sesuai gambar...")
        facilities = [
            # Kategori COM. & NAV.
            FacilityApp(name='VCU 1', remark='LES', category='COM. & NAV.'),
            FacilityApp(name='VCU 2', remark='LES', category='COM. & NAV.'),
            FacilityApp(name='VCU 3', remark='LES', category='COM. & NAV.'),
            FacilityApp(name='VCU 4', remark='LES', category='COM. & NAV.'),
            FacilityApp(name='VCU 5', remark='LES', category='COM. & NAV.'),
            FacilityApp(name='VHF BACKUP', remark='FREQ 123.4 MHz', category='COM. & NAV.'),
            FacilityApp(name='MONITOR RADIO TOWER ADI 112.4 MHz', remark='PARK AIR TSMC', category='COM. & NAV.'),
            FacilityApp(name='TELEPHONE SLJJ ATS UNIT LAIN', remark='PANASONIC', category='COM. & NAV.'),
            FacilityApp(name='TELEPHONE COOR TWR - APP 1', remark='PANASONIC', category='COM. & NAV.'),
            FacilityApp(name='TELEPHONE COOR TWR - APP 2', remark='PANASONIC', category='COM. & NAV.'),
            FacilityApp(name='TELEPHONE INTERNAL', remark='PANASONIC', category='COM. & NAV.'),
            FacilityApp(name='TELEPHONE DS APP YIA', remark='PANASONIC', category='COM. & NAV.'),
            # Kategori FACILITIES
            FacilityApp(name='COMPUTER', remark='HP', category='FACILITIES'),
            FacilityApp(name='ASD APP SUP', remark='DELL', category='FACILITIES'),
            FacilityApp(name='ASD APP RADAR', remark='DELL', category='FACILITIES'),
            FacilityApp(name='ASD APP DIRECTOR', remark='DELL', category='FACILITIES'),
            FacilityApp(name='FDD APP RADAR', remark='DELL', category='FACILITIES'),
            FacilityApp(name='FDD APP DIRECTOR', remark='DELL', category='FACILITIES'),
            FacilityApp(name='DIGITAL CLOCK (UTC)', remark='', category='FACILITIES'),
            FacilityApp(name='ROOM LIGHTING', remark='', category='FACILITIES'),
            FacilityApp(name='AIR CONDITIONER', remark='', category='FACILITIES'),
            FacilityApp(name='INTERNET', remark='WAME', category='FACILITIES'),
            FacilityApp(name='MONITOR OMS ADI', remark='VAISALA', category='FACILITIES'),
            FacilityApp(name='MONITOR ILS ADI', remark='NORMARC', category='FACILITIES'),
        ]
        db.session.bulk_save_objects(facilities)
        db.session.commit()
        print("Data fasilitas APP berhasil diperbarui sesuai gambar.")

# ... (Sisa file tidak berubah, salin dari kode Anda yang sudah ada) ...
def seed_atc_personnel():
    """Mengisi data awal untuk personel ATC."""
    if ATCPersonnel.query.count() == 0:
        print("Mengisi data personel ATC...")
        atc_names = [
            "Donny Virgin Setiawan", "Frizintia Krisnahati Indarto", "Gusti Putu Andika W", 
            "Hartanto", "Agustina Wulandari", "Widi Antara Sudarman", "Idham Azhar Bijahimo",
            "Ari Aris Susanti", "Ira Susanti", "Dendy Mahendra", "Indras R. Irawan", 
            "Heriyawati", "Winda Mediawati", "Lalu Zulkarnaen", "Astiko Bayu Aji", 
            "Qozin Asrori", "Franciscus Dwi Suryo Prabowo", "Elwahyudi Cucuk Sumarto", 
            "Erlla Dewi Pramesti", "R.R Diah Rinta Wandansari", "Rizka Aprilia Ardani", 
            "Elisabeth Dwi Setyani", "Sri Kanti", "Aji Suryo Buwono", "Firliansyah Fuzzyndo", 
            "Firdia Dwi Juni Putri", "Nyoman Dicky Surya Negara", "Gema Aulia Haq", 
            "Galuh Ajeng Putri Wardani", "Maria Emaculata Dewi Cahyani", "Imam Syafi'i", 
            "Yayuk Sukaryati", "Leni Ambar Lusiananingrum"
        ]
        for name in atc_names:
            personnel = ATCPersonnel(name=name)
            db.session.add(personnel)
        db.session.commit()
        print("Data personel ATC berhasil diisi.")

def create_initial_users():
    if User.query.count() == 0:
        print("Membuat akun pengguna awal...")
        operasi_user = User(username='operasi', division='operasi')
        operasi_user.set_password('1234')
        db.session.add(operasi_user)
        
        teknik_user = User(username='teknik', division='teknik')
        teknik_user.set_password('1234')
        db.session.add(teknik_user)
        
        db.session.commit()
        print("Akun 'operasi' dan 'teknik' berhasil dibuat.")

def seed_initial_data():
    if Facility.query.count() == 0:
        print("Mengisi data fasilitas Operasi (TWR)...")
        facilities = [
            Facility(name='VCCS', remark='GAREX', category='Internal Facilities - COM. & NAV.'),
            Facility(name='VHF', remark='PARK AIR S4', category='Internal Facilities - COM. & NAV.'),
            Facility(name='VHF', remark='PARK AIR T6TR', category='Internal Facilities - COM. & NAV.'),
            Facility(name='VHF', remark='BECKER', category='Internal Facilities - COM. & NAV.'),
            Facility(name='VHF', remark='OTE AK 100', category='Internal Facilities - COM. & NAV.'),
            Facility(name='VHF ATIS (127.85MHz)', remark='Skytrax D-ATIS', category='Internal Facilities - COM. & NAV.'),
            Facility(name='VCCS APP ADI - YIA', remark='GAREX', category='Internal Facilities - COM. & NAV.'),
            Facility(name='ILS Runway 11', remark='LOCALIZER, GLIDE PATH, DME', category='Internal Facilities - COM. & NAV.'),
            Facility(name='Remote Status Unit', remark='ILS Monitor', category='Internal Facilities - COM. & NAV.'),
            Facility(name='Telephone Internal', remark='PANASONIC', category='Internal Facilities - COM. & NAV.'),
            Facility(name='Air Situation Display (ASD)', category='Internal Support Facility'),
            Facility(name='Flight Data Display (FDD)', category='Internal Support Facility'),
            Facility(name='ATIS Display (computer)', category='Internal Support Facility'),
            Facility(name='GUN LIGHT', category='Internal Support Facility'),
            Facility(name='BINOCULAR', category='Internal Support Facility'),
            Facility(name='DIGITAL CLOCK (Bodet UTC)', category='Internal Support Facility'),
            Facility(name='ANALOG CLOCK (WIB & UTC)', category='Internal Support Facility'),
            Facility(name='AIR CONDITIONER', category='Internal Support Facility'),
            Facility(name='ROOM LIGHTING', category='Internal Support Facility'),
            Facility(name='COMPUTER', category='Internal Support Facility'),
            Facility(name='INTERNET', category='Internal Support Facility'),
            Facility(name='HP Operational', category='Internal Support Facility'),
            Facility(name='AFL CTRL SYSTEM', remark='COMPUTER 1 & 2', category='External Support Facilities'),
            Facility(name='AWOS', remark='IMS', category='External Support Facilities'),
            Facility(name='LLWAS', remark='IMS', category='External Support Facilities'),
            Facility(name='WIND SOCK', remark='RWY 11 & 29', category='External Support Facilities'),
            Facility(name='HT (HYTERA)', remark='Radio Trunking', category='External Support Facilities'),
            Facility(name='TELEPHONE UNIFY', remark='AMC, Elecrical dll', category='External Support Facilities'),
            Facility(name='TELP. DIRECT ARFF', remark='DIRECT SPEECH ARFF', category='External Support Facilities'),
            Facility(name='CRASH BELL', category='External Support Facilities'),
            Facility(name='SIRENE', category='External Support Facilities'),
            Facility(name='PAPI Light', category='Airfield Lighting Control System (ALS Cat.1)'),
            Facility(name='Runway Edge Light', category='Airfield Lighting Control System (ALS Cat.1)'),
            Facility(name='Runway Centre Light', category='Airfield Lighting Control System (ALS Cat.1)'),
            Facility(name='Runway Guard Light', category='Airfield Lighting Control System (ALS Cat.1)'),
            Facility(name='Taxiway Edge Light', category='Airfield Lighting Control System (ALS Cat.1)'),
            Facility(name='Taxiway Centre Light', category='Airfield Lighting Control System (ALS Cat.1)'),
            Facility(name='Rapid Exit Light', category='Airfield Lighting Control System (ALS Cat.1)'),
            Facility(name='Approach Light', category='Airfield Lighting Control System (ALS Cat.1)'),
            Facility(name='Flasher Light', category='Airfield Lighting Control System (ALS Cat.1)'),
            Facility(name='Rotating Beacon', category='Airfield Lighting Control System (ALS Cat.1)'),
        ]
        db.session.bulk_save_objects(facilities)
        db.session.commit()
        print("Data fasilitas Operasi (TWR) berhasil diisi.")

def seed_cnsd_facilities():
    if CNSDFacility.query.filter_by(airport_code='YIA').count() == 0:
        print("Mengisi data fasilitas CNSD YIA...")
        facilities = [
            CNSDFacility(name='ADC PRIMARY', sub_name='TX 1', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='ADC PRIMARY', sub_name='RX 1', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='ADC Back Up Trx', sub_name='TX 1', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='ADC Back Up Trx', sub_name='RX 1', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='VHF ER Ground', sub_name='TX 1', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='VHF ER Ground', sub_name='RX 1', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='ER MATSC SECONDARY', sub_name='TX 1', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='ER MATSC SECONDARY', sub_name='RX 1', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='ER MATSC PRIMARY', sub_name='TX 1', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='ER MATSC PRIMARY', sub_name='RX 1', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='ER MATSC SECONDARY', sub_name='TX 2', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='ER MATSC SECONDARY', sub_name='RX 2', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='ER JATSC PRIMARY', sub_name='TX 1', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='ER JATSC PRIMARY', sub_name='RX 1', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='ER JATSC SECONDARY', sub_name='TX 1', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='ER JATSC SECONDARY', sub_name='RX 1', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='ER JATSC SECONDARY', sub_name='TX 2', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='ER JATSC SECONDARY', sub_name='RX 2', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='ER APP TMA 120.200MHz', sub_name='TX 1', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='ER APP TMA 120.200MHz', sub_name='RX 1', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='VHF ATIS', sub_name='TX 1', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='VHF ATIS', sub_name='RX 1', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='ATIS', sub_name='SERVER', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='ATIS', sub_name='DSPL BMKG', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='ATIS', sub_name='Reproducer', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='ATIS', sub_name='PC Client ATIS', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='RECORDER', sub_name='SKYTRAX', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='AFTN TELEPRINTER', sub_name='ARO', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='AFTN TELEPRINTER', sub_name='BMKG', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='VCCS GAREX', sub_name='BDS', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='DS YIA - JOG', sub_name='', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='IP TWR - AMC', sub_name='', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='IP TELP TOWER - AP2', sub_name='', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='IP PBX / IP Phone', sub_name='', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='PSTN Backup DS', sub_name='', category='COMMUNICATION', airport_code='YIA'),
            CNSDFacility(name='LOCALIZER', sub_name='TX 1', category='NAVIGATION', airport_code='YIA'),
            CNSDFacility(name='LOCALIZER', sub_name='TX 2', category='NAVIGATION', airport_code='YIA'),
            CNSDFacility(name='GLIDE PATH', sub_name='TX 1', category='NAVIGATION', airport_code='YIA'),
            CNSDFacility(name='GLIDE PATH', sub_name='TX 2', category='NAVIGATION', airport_code='YIA'),
            CNSDFacility(name='TOME', sub_name='TX 1', category='NAVIGATION', airport_code='YIA'),
            CNSDFacility(name='TOME', sub_name='TX 2', category='NAVIGATION', airport_code='YIA'),
            CNSDFacility(name='ILS & Tome Remote Control (PMDT)', sub_name='', category='NAVIGATION', airport_code='YIA'),
            CNSDFacility(name='ADSB INTELCAN', sub_name='Ground Station 1', category='SURVEILLANCE', airport_code='YIA'),
            CNSDFacility(name='ADSB INTELCAN', sub_name='Ground Station 2', category='SURVEILLANCE', airport_code='YIA'),
            CNSDFacility(name='ASD / FDO Tower', sub_name='', category='SURVEILLANCE', airport_code='YIA'),
            CNSDFacility(name='MASTER CLOCK', sub_name='', category='DATA PROCESSING', airport_code='YIA'),
            CNSDFacility(name='Jaringan Data Pusat', sub_name='', category='DATA PROCESSING', airport_code='YIA'),
            CNSDFacility(name='Internet LA', sub_name='', category='DATA PROCESSING', airport_code='YIA'),
            CNSDFacility(name='FO Network', sub_name='', category='DATA PROCESSING', airport_code='YIA'),
            CNSDFacility(name='LAN Network', sub_name='', category='DATA PROCESSING', airport_code='YIA'),
            CNSDFacility(name='WIFI Kantor', sub_name='', category='DATA PROCESSING', airport_code='YIA'),
            CNSDFacility(name='Radio Link Gedung TX', sub_name='', category='DATA PROCESSING', airport_code='YIA'),
            CNSDFacility(name='Radio Link BMKG', sub_name='', category='DATA PROCESSING', airport_code='YIA'),
            CNSDFacility(name='Radio Link Localizer', sub_name='', category='DATA PROCESSING', airport_code='YIA'),
            CNSDFacility(name='Radio Link Glide Path', sub_name='', category='DATA PROCESSING', airport_code='YIA'),
            CNSDFacility(name='Multiplexer Loop (ILS & Gd. TX)', sub_name='', category='DATA PROCESSING', airport_code='YIA'),
            CNSDFacility(name='Jaringan Ruang Server', sub_name='', category='DATA PROCESSING', airport_code='YIA'),
            CNSDFacility(name='Computer & Jaringan Perkantoran', sub_name='', category='DATA PROCESSING', airport_code='YIA'),
        ]
        db.session.bulk_save_objects(facilities)
        db.session.commit()
        print("Data fasilitas CNSD YIA berhasil ditambahkan.")

def seed_adisucipto_facilities():
    if CNSDFacility.query.filter_by(airport_code='Adisutjipto').count() == 0:
        print("Mengisi data fasilitas CNSD Adisutjipto...")
        facilities = [
            CNSDFacility(name='VHF-A/G ADC', sub_name='Merk OTE DE100/DB100', category='COMMUNICATION', airport_code='Adisutjipto'),
            CNSDFacility(name='VHF-A/G ADC', sub_name='Merk Rohde & Schwarz', category='COMMUNICATION', airport_code='Adisutjipto'),
            CNSDFacility(name='VHF-A/G APP', sub_name='Merk Park Air T6T/T6R (Primary)', category='COMMUNICATION', airport_code='Adisutjipto'),
            CNSDFacility(name='VHF-A/G APP', sub_name='Merk Park Air T6T/T6R (Secondary)', category='COMMUNICATION', airport_code='Adisutjipto'),
            CNSDFacility(name='Voice Recorder', sub_name='', category='COMMUNICATION', airport_code='Adisutjipto'),
            CNSDFacility(name='DVOR', sub_name='', category='NAVIGATION', airport_code='Adisutjipto'),
            CNSDFacility(name='DME', sub_name='', category='NAVIGATION', airport_code='Adisutjipto'),
            CNSDFacility(name='NDB', sub_name='', category='NAVIGATION', airport_code='Adisutjipto'),
            CNSDFacility(name='MSSR Mode-S', sub_name='', category='SURVEILLANCE', airport_code='Adisutjipto'),
            CNSDFacility(name='AMSC (Main System)', sub_name='', category='DATA PROCESSING', airport_code='Adisutjipto'),
            CNSDFacility(name='ATC System', sub_name='', category='DATA PROCESSING', airport_code='Adisutjipto'),
        ]
        db.session.bulk_save_objects(facilities)
        db.session.commit()
        print("Data fasilitas CNSD Adisutjipto berhasil ditambahkan.")

def seed_adi_soemarmo_facilities():
    if CNSDFacility.query.filter_by(airport_code='AdiSoemarmo').count() == 0:
        print("Mengisi data fasilitas CNSD Adi Soemarmo...")
        facilities = [
            CNSDFacility(name='ATIS', sub_name='', category='COMMUNICATION', airport_code='AdiSoemarmo'),
            CNSDFacility(name='UHF Radio Link', sub_name='', category='COMMUNICATION', airport_code='AdiSoemarmo'),
            CNSDFacility(name='VHF-A/G ADC', sub_name='', category='COMMUNICATION', airport_code='AdiSoemarmo'),
            CNSDFacility(name='Voice Recorder', sub_name='', category='COMMUNICATION', airport_code='AdiSoemarmo'),
            CNSDFacility(name='DME', sub_name='', category='NAVIGATION', airport_code='AdiSoemarmo'),
            CNSDFacility(name='DVOR', sub_name='', category='NAVIGATION', airport_code='AdiSoemarmo'),
            CNSDFacility(name='ILS', sub_name='', category='NAVIGATION', airport_code='AdiSoemarmo'),
            CNSDFacility(name='NDB', sub_name='', category='NAVIGATION', airport_code='AdiSoemarmo'),
            CNSDFacility(name='AMSC (Main System)', sub_name='', category='DATA PROCESSING', airport_code='AdiSoemarmo'),
        ]
        db.session.bulk_save_objects(facilities)
        db.session.commit()
        print("Data fasilitas CNSD Adi Soemarmo berhasil ditambahkan.")

def seed_tunggul_wulung_facilities():
    if CNSDFacility.query.filter_by(airport_code='TunggulWulung').count() == 0:
        print("Mengisi data fasilitas CNSD Tunggul Wulung...")
        facilities = [
            CNSDFacility(name='VHF Portable', sub_name='', category='COMMUNICATION', airport_code='TunggulWulung'),
            CNSDFacility(name='VHF-A/G ADC', sub_name='', category='COMMUNICATION', airport_code='TunggulWulung'),
            CNSDFacility(name='Voice Recorder', sub_name='', category='COMMUNICATION', airport_code='TunggulWulung'),
            CNSDFacility(name='DME', sub_name='', category='NAVIGATION', airport_code='TunggulWulung'),
            CNSDFacility(name='DVOR', sub_name='', category='NAVIGATION', airport_code='TunggulWulung'),
            CNSDFacility(name='ADS-B', sub_name='', category='SURVEILLANCE', airport_code='TunggulWulung'),
            CNSDFacility(name='AFTN Workstation/Teleprinter', sub_name='(Standalone)', category='DATA PROCESSING', airport_code='TunggulWulung'),
        ]
        db.session.bulk_save_objects(facilities)
        db.session.commit()
        print("Data fasilitas CNSD Tunggul Wulung berhasil ditambahkan.")
