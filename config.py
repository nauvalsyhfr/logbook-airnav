import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Menyimpan semua variabel konfigurasi untuk aplikasi Flask."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'kunci-rahasia-yang-sangat-aman-dan-sulit-ditebak'
    
    # Konfigurasi Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'logbook.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- KONFIGURASI BARU UNTUK DIVISI TEKNIK ---

    # Lokasi folder untuk menyimpan file yang diunggah (paraf, dll.)
    UPLOAD_FOLDER = os.path.join(basedir, 'app/static/uploads')
    
    # Ekstensi file yang diizinkan untuk diunggah
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

    # Kata sandi untuk mengakses logbook setiap bandara
    AIRPORT_PASSWORDS = {
        'YIA': 'kulonprogo',
        'Adisutjipto': 'sleman',
        'AdiSoemarmo': 'solo',
        'TunggulWulung': 'cilacap'
    }
