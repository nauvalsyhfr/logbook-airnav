from app import create_app

# Membuat instance aplikasi menggunakan factory
app = create_app()

if __name__ == '__main__':
    # Menjalankan aplikasi dalam mode debug
    # Mode debug akan otomatis me-reload server jika ada perubahan kode
    app.run(debug=True)
