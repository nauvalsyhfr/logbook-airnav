from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from .models import db, User

auth_bp = Blueprint('auth', __name__)

def create_initial_users():
    """Membuat pengguna awal jika database kosong."""
    if User.query.count() == 0:
        print("Membuat akun pengguna awal...")
        user_ops = User(username='operasi', division='operasi')
        user_ops.set_password('1234')
        user_tek = User(username='teknik', division='teknik')
        user_tek.set_password('1234')
        db.session.add(user_ops)
        db.session.add(user_tek)
        db.session.commit()
        print("Akun pengguna awal berhasil dibuat.")

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.division == 'operasi':
            return redirect(url_for('main.dashboard_operasi'))
        else:
            return redirect(url_for('main.dashboard_teknik'))
            
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=True)
        
        if user.division == 'operasi':
            next_page = url_for('main.dashboard_operasi')
        else:
            next_page = url_for('main.dashboard_teknik')
        return redirect(next_page)

    return render_template('login.html', title='Login')

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))
