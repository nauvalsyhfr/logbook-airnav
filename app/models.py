# app/models.py

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import enum

db = SQLAlchemy()

# Tabel asosiasi untuk personel ATC yang bertugas
atc_duty_association = db.Table('atc_duty_association',
    db.Column('logbook_entry_id', db.Integer, db.ForeignKey('logbook_entry.id'), primary_key=True),
    db.Column('atc_personnel_id', db.Integer, db.ForeignKey('atc_personnel.id'), primary_key=True)
)

# Enum untuk kondisi fasilitas
class FacilityCondition(enum.Enum):
    # --- PERUBAHAN: Menggunakan singkatan agar cocok dengan nilai dari form ---
    GOOD = "G"
    FAIR = "F"
    POOR = "P"
    UNSERVICEABLE = "U/S"
    READABLE_5 = "5"
    READABLE_4 = "4"
    READABLE_3 = "3"
    READABLE_2 = "2"
    READABLE_1 = "1"

    @classmethod
    def choices(cls):
        return [(choice.value, choice.name) for choice in cls]

    @classmethod
    def coerce(cls, item):
        return cls(item) if item is not None else None

    def __str__(self):
        return str(self.value)

# Model untuk Pengguna
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    division = db.Column(db.String(64), nullable=False)
    logbook_entries = db.relationship('LogbookEntry', backref='creator', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

# Model untuk Personel ATC
class ATCPersonnel(db.Model):
    __tablename__ = 'atc_personnel'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)

    def __repr__(self):
        return f'<ATCPersonnel {self.name}>'

# Model untuk Entri Logbook Utama
class LogbookEntry(db.Model):
    __tablename__ = 'logbook_entry'
    id = db.Column(db.Integer, primary_key=True)
    
    logbook_type = db.Column(db.String(20), nullable=False, default='TWR') # TWR untuk Tower, APP untuk Approach
    
    log_date = db.Column(db.Date, nullable=False)
    shift = db.Column(db.String(50), nullable=False)
    notam = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    
    controller_signature_1 = db.Column(db.String(255), nullable=True)
    controller_signature_2 = db.Column(db.String(255), nullable=True)
    manager_signature = db.Column(db.String(255), nullable=True)

    atc_on_duty_personnel = db.relationship(
        'ATCPersonnel', secondary=atc_duty_association,
        backref=db.backref('logbook_entries', lazy='dynamic'),
        lazy='subquery'
    )
    
    facility_statuses = db.relationship('FacilityStatus', backref='logbook_entry', lazy=True, cascade="all, delete-orphan")
    operational_logs = db.relationship('OperationalLog', backref='logbook_entry', lazy=True, cascade="all, delete-orphan")
    atc_positions = db.relationship('ATCPosition', backref='logbook_entry', lazy=True, cascade="all, delete-orphan")
    atc_position_header = db.relationship('ATCPositionHeader', backref='logbook_entry', uselist=False, cascade="all, delete-orphan")

# Model untuk Header Posisi ATC
class ATCPositionHeader(db.Model):
    __tablename__ = 'atc_position_header'
    id = db.Column(db.Integer, primary_key=True)
    logbook_id = db.Column(db.Integer, db.ForeignKey('logbook_entry.id'), nullable=False)
    header_1 = db.Column(db.String(50))
    header_2 = db.Column(db.String(50))
    header_3 = db.Column(db.String(50))
    header_4 = db.Column(db.String(50))
    header_5 = db.Column(db.String(50))
    header_6 = db.Column(db.String(50))

# Model untuk Posisi ATC
class ATCPosition(db.Model):
    __tablename__ = 'atc_position'
    id = db.Column(db.Integer, primary_key=True)
    logbook_id = db.Column(db.Integer, db.ForeignKey('logbook_entry.id'), nullable=False)
    position_name = db.Column(db.String(100), nullable=False)
    time_slot_1 = db.Column(db.String(100))
    time_slot_2 = db.Column(db.String(100))
    time_slot_3 = db.Column(db.String(100))
    time_slot_4 = db.Column(db.String(100))
    time_slot_5 = db.Column(db.String(100))
    time_slot_6 = db.Column(db.String(100))

# Model untuk Fasilitas TWR (Aerodrome Control Tower)
class Facility(db.Model):
    __tablename__ = 'facility'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) 
    remark = db.Column(db.String(100), nullable=True)
    category = db.Column(db.String(100), nullable=False)

# Model untuk Fasilitas APP (Approach Control Unit)
class FacilityApp(db.Model):
    __tablename__ = 'facility_app'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    remark = db.Column(db.String(100), nullable=True)
    category = db.Column(db.String(100), nullable=False)

# Model untuk Status Fasilitas (Generik)
class FacilityStatus(db.Model):
    __tablename__ = 'facility_status'
    id = db.Column(db.Integer, primary_key=True)
    logbook_id = db.Column(db.Integer, db.ForeignKey('logbook_entry.id'), nullable=False)
    
    facility_id = db.Column(db.Integer, nullable=False)
    facility_type = db.Column(db.String(10), nullable=False) # 'TWR' atau 'APP'

    condition = db.Column(db.Enum(FacilityCondition, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    notes = db.Column(db.Text, nullable=True)

    @property
    def facility(self):
        if self.facility_type == 'TWR':
            return Facility.query.get(self.facility_id)
        elif self.facility_type == 'APP':
            return FacilityApp.query.get(self.facility_id)
        return None

# Model untuk Log Operasional
class OperationalLog(db.Model):
    __tablename__ = 'operational_log'
    id = db.Column(db.Integer, primary_key=True)
    logbook_id = db.Column(db.Integer, db.ForeignKey('logbook_entry.id'), nullable=False)
    event_time = db.Column(db.Time, nullable=False)
    description = db.Column(db.Text, nullable=False)
    remarks = db.Column(db.Text, nullable=True)

# Model untuk Logbook CNSD
class CNSDLogbook(db.Model):
    __tablename__ = 'cnsd_logbook'
    id = db.Column(db.Integer, primary_key=True)
    airport = db.Column(db.String(100), nullable=False)
    log_date = db.Column(db.Date, nullable=False)
    shift = db.Column(db.String(50), nullable=False)
    manager_signature = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User')
    personnel = db.relationship('CNSDPersonnel', backref='logbook', cascade="all, delete-orphan")
    facility_statuses = db.relationship('CNSDFacilityStatus', backref='logbook', cascade="all, delete-orphan")
    uraian_kegiatan = db.relationship('CNSDUraianKegiatan', backref='logbook', cascade="all, delete-orphan")

class CNSDPersonnel(db.Model):
    __tablename__ = 'cnsd_personnel'
    id = db.Column(db.Integer, primary_key=True)
    cnsd_logbook_id = db.Column(db.Integer, db.ForeignKey('cnsd_logbook.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    signature_path = db.Column(db.String(255), nullable=True)

class CNSDFacility(db.Model):
    __tablename__ = 'cnsd_facility'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    sub_name = db.Column(db.String(100), nullable=True)
    category = db.Column(db.String(100), nullable=False)
    airport_code = db.Column(db.String(20), nullable=False)

class CNSDFacilityStatus(db.Model):
    __tablename__ = 'cnsd_facility_status'
    id = db.Column(db.Integer, primary_key=True)
    cnsd_logbook_id = db.Column(db.Integer, db.ForeignKey('cnsd_logbook.id'), nullable=False)
    cnsd_facility_id = db.Column(db.Integer, db.ForeignKey('cnsd_facility.id'), nullable=False)
    condition = db.Column(db.String(20), nullable=False)
    facility = db.relationship('CNSDFacility')

class CNSDUraianKegiatan(db.Model):
    __tablename__ = 'cnsd_uraian_kegiatan'
    id = db.Column(db.Integer, primary_key=True)
    cnsd_logbook_id = db.Column(db.Integer, db.ForeignKey('cnsd_logbook.id'), nullable=False)
    event_time = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=False)