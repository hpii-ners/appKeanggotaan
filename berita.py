import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
# Import dari models agar tidak circular
from models import db, Berita, Identitas
from datetime import datetime

berita_bp = Blueprint('berita', __name__)

# --- KONSTANTA (Sesuai saran SonarLint untuk Clean Code) ---
UPLOAD_FOLDER = 'static/uploads'
ENDPOINT_ADMIN = 'berita.list_admin'

def allowed_file(filename):
    """Validasi ekstensi file gambar yang diizinkan."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@berita_bp.route('/berita')
def list_publik():
    """Menampilkan daftar berita untuk publik."""
    all_news = Berita.query.order_by(Berita.tanggal.desc()).all()
    iden = Identitas.query.first()
    
    return render_template('utama.html', 
                           data=all_news,
                           sidebar_data=all_news[:5],
                           identitas=iden, 
                           now=datetime.now())

@berita_bp.route('/berita/<int:id>')
def detail(id):
    """Menampilkan detail berita spesifik."""
    item = Berita.query.get_or_404(id)
    iden = Identitas.query.first()
    others = Berita.query.filter(Berita.id != id).order_by(Berita.tanggal.desc()).limit(5).all()
    
    return render_template('berita_detail.html', 
                           item=item, 
                           sidebar_data=others,
                           identitas=iden, 
                           now=datetime.now())

@berita_bp.route('/tentang')
def tentang_publik():
    """Menampilkan halaman profil organisasi di sisi publik."""
    # Import dilakukan di dalam fungsi jika diperlukan untuk menghindari circular import
    iden = Identitas.query.first()
    # PERBAIKAN: Nama file template harus sesuai dengan file fisik (tentang_publik.html)
    return render_template('tentang_publik.html', identitas=iden,now=datetime.now())

@berita_bp.route('/admin/berita')
@login_required
def list_admin():
    """Halaman manajemen berita untuk admin."""
    data = Berita.query.order_by(Berita.tanggal.desc()).all()
    return render_template('berita_admin.html', data=data)

@berita_bp.route('/admin/berita/tambah', methods=['POST'])
@login_required
def tambah():
    """Proses penambahan berita baru."""
    f = request.form
    file = request.files.get('gambar')
    filename = None

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        upload_path = os.path.join(current_app.root_path, UPLOAD_FOLDER)
        os.makedirs(upload_path, exist_ok=True)
        file.save(os.path.join(upload_path, filename))

    baru = Berita(
        judul=f.get('judul'),
        isi=f.get('isi'),
        path_image=filename,
        penulis=current_user.username
    )
    db.session.add(baru)
    db.session.commit()
    flash("Berita berhasil diterbitkan!", "success")
    return redirect(url_for(ENDPOINT_ADMIN))

@berita_bp.route('/admin/berita/edit/<int:id>', methods=['POST'])
@login_required
def edit(id):
    """Proses pembaruan data berita yang sudah ada."""
    item = Berita.query.get_or_404(id)
    f = request.form
    file = request.files.get('gambar')

    item.judul = f.get('judul')
    item.isi = f.get('isi')

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        upload_path = os.path.join(current_app.root_path, UPLOAD_FOLDER)
        os.makedirs(upload_path, exist_ok=True)
        file.save(os.path.join(upload_path, filename))
        item.path_image = filename

    db.session.commit()
    flash("Berita berhasil diperbarui!", "success")
    return redirect(url_for(ENDPOINT_ADMIN))

@berita_bp.route('/admin/berita/hapus/<int:id>')
@login_required
def hapus(id):
    """Proses penghapusan berita beserta file gambarnya."""
    item = Berita.query.get_or_404(id)
    
    if item.path_image:
        try:
            file_path = os.path.join(current_app.root_path, UPLOAD_FOLDER, item.path_image)
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            # Tetap lanjut hapus record di DB jika file fisik gagal dihapus
            pass

    db.session.delete(item)
    db.session.commit()
    flash("Berita telah dihapus!", "warning")
    return redirect(url_for(ENDPOINT_ADMIN))