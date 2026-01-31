from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from werkzeug.security import generate_password_hash
# Impor db dan model User dari file models.py Anda
from models import db, User 

# Gunakan Blueprint, bukan 'app'
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/users')
@login_required
def user_admin():
    users = User.query.all()
    return render_template('user_admin.html', users=users)

@admin_bp.route('/admin/users/tambah', methods=['POST'])
@login_required
def user_tambah():
    f = request.form
    username = f.get('username').lower().strip()
    password = f.get('password')

    if User.query.filter_by(username=username).first():
        flash("Username sudah digunakan!", "danger")
    else:
        # Hashing password sebelum disimpan
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        baru = User(username=username, password=hashed_pw)
        db.session.add(baru)
        db.session.commit()
        flash("User baru berhasil ditambahkan.", "success")
    
    return redirect(url_for('admin.user_admin')) # Gunakan nama_blueprint.fungsi

@admin_bp.route('/admin/users/edit/<int:id>', methods=['POST'])
@login_required
def user_edit(id):
    user = User.query.get_or_404(id)
    f = request.form
    
    user.username = f.get('username').lower().strip()
    
    # Update password hanya jika diisi
    password_baru = f.get('password')
    if password_baru:
        user.password = generate_password_hash(password_baru, method='pbkdf2:sha256')
    
    db.session.commit()
    flash("Data user berhasil diperbarui.", "success")
    return redirect(url_for('admin.user_admin'))