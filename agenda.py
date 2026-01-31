from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from models import db, Agenda
from datetime import datetime

agenda_bp = Blueprint('agenda', __name__)

@agenda_bp.route('/agenda') # Ini rute publik
def list_publik():
    data = Agenda.query.all()
    return render_template('agenda_publik.html', data=data,now=datetime.now())

@agenda_bp.route('/admin/agenda')
@login_required
def list_admin():
    data = Agenda.query.order_by(Agenda.tanggal_kegiatan.asc()).all()
    return render_template('agenda_admin.html', data=data)

@agenda_bp.route('/admin/agenda/tambah', methods=['POST'])
@login_required
def tambah():
    f = request.form
    # Konversi string tanggal dari HTML ke objek Python DateTime
    tgl_obj = datetime.strptime(f.get('tanggal'), '%Y-%m-%dT%H:%M')
    
    baru = Agenda(
        nama_kegiatan=f.get('nama_kegiatan'),
        tanggal_kegiatan=tgl_obj,
        lokasi=f.get('lokasi'),
        keterangan=f.get('keterangan'),
        penulis=current_user.username
    )
    db.session.add(baru)
    db.session.commit()
    flash("Agenda berhasil ditambahkan!", "success")
    return redirect(url_for('agenda.list_admin'))

@agenda_bp.route('/admin/agenda/hapus/<int:id>')
@login_required
def hapus(id):
    item = Agenda.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash("Agenda telah dihapus!", "warning")
    return redirect(url_for('agenda.list_admin'))