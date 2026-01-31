import os
import sys
import json
import platform
import subprocess
import hashlib
import uuid
import webbrowser
import pandas as pd
from threading import Timer
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from sqlalchemy import or_, extract

# 1. TRY-IMPORT WINREG (Bypass jika di macOS)
try:
    import winreg
except ImportError:
    winreg = None

from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, render_template_string
from flask_login import LoginManager, login_required, current_user
from werkzeug.security import generate_password_hash

# --- IMPORT MODELS & BLUEPRINTS ---
from models import db, User, Identitas, Warga, Iuran, Pengeluaran, Berita, Agenda
from login import auth_bp
from berita import berita_bp
from agenda import agenda_bp
from admin import admin_bp

load_dotenv()

# ==========================================
# 2. DEFINISI PATH & FOLDER (WAJIB DI ATAS)
# ==========================================
if getattr(sys, 'frozen', False):
    # Jika dipackage (EXE/APP)
    basedir = os.path.dirname(sys.executable)
    # Khusus macOS .app, sys.executable berada jauh di dalam Contents/MacOS
    if platform.system() == 'Darwin' and '.app' in basedir:
        # Naik 3 level agar folder 'data_ipl' sejajar dengan file .app
        basedir = os.path.abspath(os.path.join(basedir, '../../..'))
else:
    # Jika mode development (python app.py)
    basedir = os.path.abspath(os.path.dirname(__file__))

# Buat folder data agar LicenseManager tidak error mencari db_dir
db_dir = os.path.join(basedir, 'data_ipl')
if not os.path.exists(db_dir):
    os.makedirs(db_dir)

# ==========================================
# 3. KONFIGURASI LISENSI
# ==========================================
SECRET_SALT = "AURORA_WARGA_SECURE_2026_!@#"
APP_REG_PATH = r"Software\AuroraLedgerWarga_v1"
TRIAL_DAYS = 30
LICENSE_DURATION_DAYS = 365

# --- TEMPLATE HTML HALAMAN AKTIVASI ---
ACTIVATION_PAGE_HTML = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <title>Aktivasi Diperlukan</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <style>
        body { background: #eef2f6; height: 100vh; display: flex; align-items: center; justify-content: center; font-family: 'Segoe UI', sans-serif; }
        .card-activation { border: none; border-radius: 20px; box-shadow: 0 15px 40px rgba(0,0,0,0.1); width: 480px; background: white; overflow: hidden; }
        .card-header { background: linear-gradient(135deg, #dc3545, #c82333); color: white; padding: 30px; text-align: center; }
        .hwid-box { background: #f8f9fa; border: 2px dashed #dee2e6; border-radius: 12px; padding: 15px; margin: 25px 0; cursor: pointer; }
        .hwid-code { font-family: 'Consolas', monospace; font-weight: bold; font-size: 1.1rem; color: #333; }
    </style>
</head>
<body>
    <div class="card card-activation">
        <div class="card-header">
            <i class="bi bi-shield-lock-fill" style="font-size: 3rem;"></i>
            <h4 class="fw-bold mt-2">Lisensi Tidak Aktif</h4>
        </div>
        <div class="card-body p-4 text-center">
            <p class="text-muted small">Kirim <b>Machine ID</b> ini ke admin:</p>
            <div class="hwid-box" onclick="navigator.clipboard.writeText('{{ hwid }}'); alert('ID Tersalin!');">
                <div class="hwid-code">{{ hwid }}</div>
                <small class="text-primary fw-bold">Klik untuk Salin</small>
            </div>
            <form action="/activate-license-system" method="POST">
                <div class="mb-3 text-start">
                    <label class="form-label fw-bold small text-secondary">SERIAL NUMBER</label>
                    <input type="text" name="serial_number" class="form-control text-center fw-bold" placeholder="XXXX-XXXX-XXXX-XXXX" required>
                </div>
                <button type="submit" class="btn btn-danger w-100 rounded-pill">AKTIFKAN SEKARANG</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

class LicenseManager:
    def __init__(self):
        self.reg_path = APP_REG_PATH
        self.secret_salt = SECRET_SALT
        self.time_format = "%Y-%m-%d %H:%M:%S"
        self.license_file = os.path.join(db_dir, '.app_license.json')

    def get_hwid(self):
        """Mendapatkan ID unik perangkat (Hybrid)"""
        try:
            sys_plat = platform.system()
            if sys_plat == 'Windows':
                cmd = 'wmic csproduct get uuid'
                return subprocess.check_output(cmd, shell=True).decode().split('\n')[1].strip()
            elif sys_plat == 'Darwin':  # macOS
                cmd = "ioreg -rd1 -c IOPlatformExpertDevice | grep -E '(IOPlatformUUID|uuid)'"
                output = subprocess.check_output(cmd, shell=True).decode()
                return output.split('"')[-2]
            return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()[:16].upper()
        except Exception:
            return "UNKNOWN-MACHINE-ID"

    def get_expected_key(self):
        hwid = self.get_hwid()
        raw = f"{hwid}::{self.secret_salt}"
        return hashlib.sha256(raw.encode()).hexdigest()[:20].upper()

    def _save_license_file(self, data):
        with open(self.license_file, 'w') as f:
            json.dump(data, f)

    def _load_license_file(self):
        if os.path.exists(self.license_file):
            try:
                with open(self.license_file, 'r') as f:
                    return json.load(f)
            except: return None
        return None

    def check_license(self):
        hwid = self.get_hwid()
        expected = self.get_expected_key()

        # LOGIKA WINDOWS (REGISTRY)
        if platform.system() == 'Windows' and winreg:
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.reg_path, 0, winreg.KEY_ALL_ACCESS)
                try:
                    stored_key, _ = winreg.QueryValueEx(key, "LicenseKey")
                    if stored_key == expected:
                        act_str, _ = winreg.QueryValueEx(key, "ActivationDate")
                        act_dt = datetime.strptime(act_str, self.time_format)
                        rem = (act_dt + timedelta(days=LICENSE_DURATION_DAYS) - datetime.now()).days
                        if rem > 0: return "ACTIVE", rem
                except: pass

                inst_str, _ = winreg.QueryValueEx(key, "InstallDate")
                inst_dt = datetime.strptime(inst_str, self.time_format)
                rem_t = (inst_dt + timedelta(days=TRIAL_DAYS) - datetime.now()).days
                return ("TRIAL", rem_t) if rem_t > 0 else ("EXPIRED", 0)
            except OSError:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.reg_path)
                winreg.SetValueEx(key, "InstallDate", 0, winreg.REG_SZ, datetime.now().strftime(self.time_format))
                return "TRIAL", TRIAL_DAYS

        # LOGIKA MACOS / FILE BASED
        else:
            data = self._load_license_file()
            if not data:
                data = {"InstallDate": datetime.now().strftime(self.time_format)}
                self._save_license_file(data)
                return "TRIAL", TRIAL_DAYS

            if data.get("LicenseKey") == expected:
                act_dt = datetime.strptime(data["ActivationDate"], self.time_format)
                rem = (act_dt + timedelta(days=LICENSE_DURATION_DAYS) - datetime.now()).days
                if rem > 0: return "ACTIVE", rem

            inst_dt = datetime.strptime(data["InstallDate"], self.time_format)
            rem_t = (inst_dt + timedelta(days=TRIAL_DAYS) - datetime.now()).days
            return ("TRIAL", rem_t) if rem_t > 0 else ("EXPIRED", 0)

    def activate(self, serial_input):
        sn = serial_input.strip().upper()
        if sn != self.get_expected_key(): return False
        now_str = datetime.now().strftime(self.time_format)
        
        if platform.system() == 'Windows' and winreg:
            try:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.reg_path)
                winreg.SetValueEx(key, "LicenseKey", 0, winreg.REG_SZ, sn)
                winreg.SetValueEx(key, "ActivationDate", 0, winreg.REG_SZ, now_str)
                return True
            except: return False
        else:
            data = self._load_license_file() or {}
            data.update({"LicenseKey": sn, "ActivationDate": now_str})
            self._save_license_file(data)
            return True

# Inisialisasi sekarang aman
license_mgr = LicenseManager()

# ==========================================
# 3. KONFIGURASI FLASK APP (FIX DATABASE PATH)
# ==========================================
if getattr(sys, 'frozen', False):
    # JIKA JADI EXE: Gunakan folder tempat file .exe berada
    basedir = os.path.dirname(sys.executable)
    
    # Template tetap diambil dari folder temporary (_MEIPASS)
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    # JIKA SCRIPT PYTHON BIASA: Gunakan folder file ini
    basedir = os.path.abspath(os.path.dirname(__file__))
    app = Flask(__name__)

# --- MEMASTIKAN FOLDER DATA_IPL TERBUAT DI SEBELAH EXE ---
db_dir = os.path.join(basedir, 'data_ipl') # Path absolut ke folder data
if not os.path.exists(db_dir):
    os.makedirs(db_dir) # Buat folder jika belum ada

db_file = os.path.join(db_dir, 'database.db')
sqlite_uri = f"sqlite:///{db_file}"

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-key-aman-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = sqlite_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- WIRING DATABASE & LOGIN ---
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Registrasi Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(berita_bp)
app.register_blueprint(agenda_bp)
app.register_blueprint(admin_bp)

# Buat Tabel & Data Default
with app.app_context():
    db.create_all()
    
    if not Identitas.query.first():
        db.session.add(Identitas(nama_app="Aurora Ledger", alamat="Alamat Default", kota="Kota Default"))
    
    admin_user = os.getenv('ADMIN_USERNAME', 'admin')
    admin_pass = os.getenv('ADMIN_PASSWORD', 'AuroraSecureFallback77!@') 
    if not User.query.filter_by(username=admin_user).first():
        hashed_pw = generate_password_hash(admin_pass, method='pbkdf2:sha256')
        db.session.add(User(username=admin_user, password=hashed_pw))
    db.session.commit()


# ==========================================
# 4. MIDDLEWARE PROTEKSI & CONTEXT PROCESSOR
# ==========================================

@app.before_request
def check_app_license():
    """
    Middleware ini berjalan sebelum SETIAP request.
    Jika lisensi EXPIRED, user akan dipaksa melihat halaman aktivasi.
    """
    # Jangan blokir akses ke file statis (css/js) atau proses aktivasi itu sendiri
    if request.endpoint and ('static' in request.endpoint or 'activate_license' in request.endpoint):
        return

    # Cek status ke Registry
    status, days_left = license_mgr.check_license()

    if status == "EXPIRED":
        # Tampilkan Layar Kunci
        return render_template_string(ACTIVATION_PAGE_HTML, hwid=license_mgr.get_hwid())

    # Simpan info lisensi ke request agar bisa dipakai di template
    request.license_status = status
    request.license_days_left = days_left


@app.context_processor
def inject_globals():
    """Mengirim variabel global ke semua template HTML"""
    # Ambil 5 berita terbaru & 3 agenda
    berita_sidebar = Berita.query.order_by(Berita.tanggal.desc()).limit(5).all()
    agenda_sidebar = Agenda.query.order_by(Agenda.tanggal_kegiatan.asc()).limit(3).all()
    
    # Ambil info lisensi dari middleware
    status = getattr(request, 'license_status', 'ACTIVE')
    days = getattr(request, 'license_days_left', 0)
    
    return {
        'datetime': datetime, 
        'identitas': Identitas.query.first(),
        'active_page': request.path,
        'current_user': current_user,
        'sidebar_berita': berita_sidebar,
        'sidebar_agenda': agenda_sidebar,
        # Variabel Lisensi Baru
        'is_trial': (status == 'TRIAL'),
        'license_days': days,
        'machine_id': license_mgr.get_hwid()
    }

# ==========================================
# 5. FUNGSI HELPER
# ==========================================
def get_date_obj(date_str):
    if not date_str: return None
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.replace(tzinfo=timezone.utc)
    except ValueError: return None

def clean_bulk_data(val):
    s = str(val).strip()
    return "" if s.lower() in ['nan', 'none'] else s


# ==========================================
# 6. RUTE APLIKASI UTAMA
# ==========================================

# --- RUTE BARU: PROSES AKTIVASI ---
@app.route('/activate-license-system', methods=['POST'])
def activate_license_post():
    serial = request.form.get('serial_number', '').strip().upper()
    if license_mgr.activate(serial):
        flash("Aktivasi Berhasil! Terima kasih telah menggunakan layanan penuh.", "success")
        return redirect(url_for('index'))
    else:
        # Jika gagal, kembalikan ke halaman kunci (otomatis via middleware)
        # Kita bisa pakai render_template_string lagi dengan alert script
        script_alert = "<script>alert('Serial Number TIDAK VALID!'); window.history.back();</script>"
        return script_alert

# --- RUTE DASHBOARD ---
@app.route('/')
@login_required
def index():
    sudah_bayar = Iuran.query.order_by(Iuran.tanggal.desc()).all()
    return render_template('index.html', sudah_bayar=sudah_bayar)

# --- RUTE API PENCARIAN ---
@app.route('/api/search_warga')
@login_required
def search_warga():
    term = request.args.get('term', '')
    if not term:
        return jsonify([])

    list_w = Warga.query.filter(
        or_(
            Warga.nama.ilike(f'%{term}%'),
            Warga.alamat.ilike(f'%{term}%'),
            Warga.blok.ilike(f'%{term}%'),
            Warga.zona.ilike(f'%{term}%')
        )
    ).limit(10).all()

    results = []
    for w in list_w:
        label = f"{w.nama} | {w.blok} - {w.zona}"
        if w.alamat:
            label += f" | {w.alamat[:20]}..." 
            
        results.append({
            'label': label,        
            'value': w.nama,      
            'no_hp': w.no_hp,
            'blok': w.blok,
            'zona': w.zona,
            'alamat': w.alamat
        })
        
    return jsonify(results)

# --- RUTE PEMBAYARAN ---
@app.route('/bayar', methods=['POST'])
@login_required
def bayar():
    f = request.form
    nama = f.get('nama').strip()
    bulan = f.get('bulan')
    tahun_ini = datetime.now().year 

    exists = Iuran.query.filter(
        Iuran.nama_warga == nama,
        Iuran.bulan_iuran == bulan,
        extract('year', Iuran.tanggal) == tahun_ini
    ).first()

    if exists:
        flash(f"Gagal! {nama} sudah membayar untuk bulan {bulan} {tahun_ini}.", "danger")
        return redirect(url_for('index'))

    w_master = Warga.query.filter_by(nama=nama).first()
    if not w_master:
        db.session.add(Warga(nama=nama, blok=f.get('blok'), no_hp=f.get('no_hp'), zona=f.get('zona')))
    else:
        w_master.blok, w_master.no_hp, w_master.zona = f.get('blok'), f.get('no_hp'), f.get('zona')
    
    db.session.add(Iuran(
        nama_warga=nama, 
        blok_rumah=f.get('blok'), 
        no_hp=f.get('no_hp'), 
        zona=f.get('zona'), 
        bulan_iuran=bulan, 
        jumlah=float(f.get('jumlah')), 
        keterangan=f.get('keterangan')
    ))
    
    db.session.commit()
    flash("Pembayaran berhasil disimpan.", "success")
    return redirect(url_for('index'))

@app.route('/edit_iuran/<int:id>', methods=['POST'])
@login_required
def edit_iuran(id):
    i = Iuran.query.get_or_404(id)
    f = request.form
    i.nama_warga = f.get('nama')
    i.blok_rumah = f.get('blok')
    i.no_hp = f.get('no_hp')
    i.zona = f.get('zona')
    i.bulan_iuran = f.get('bulan')
    i.jumlah = float(f.get('jumlah'))
    i.keterangan = f.get('keterangan')
    db.session.commit()
    flash("Data pembayaran diperbarui.", "success")
    return redirect(url_for('index'))

# --- HELPER FUNGSI TERBILANG ---
def num_to_words(n):
    try:
        n = int(n)
        satuan = ["", "Satu", "Dua", "Tiga", "Empat", "Lima", "Enam", "Tujuh", "Delapan", "Sembilan", "Sepuluh", "Sebelas"]
        if n >= 0 and n <= 11:
            return " " + satuan[n]
        elif n < 20:
            return num_to_words(n - 10) + " Belas"
        elif n < 100:
            return num_to_words(n / 10) + " Puluh" + num_to_words(n % 10)
        elif n < 200:
            return " Seratus" + num_to_words(n - 100)
        elif n < 1000:
            return num_to_words(n / 100) + " Ratus" + num_to_words(n % 100)
        elif n < 2000:
            return " Seribu" + num_to_words(n - 1000)
        elif n < 1000000:
            return num_to_words(n / 1000) + " Ribu" + num_to_words(n % 1000)
        elif n < 1000000000:
            return num_to_words(n / 1000000) + " Juta" + num_to_words(n % 1000000)
        else:
            return "Angka Terlalu Besar"
    except Exception: # PERBAIKAN: Menambahkan 'Exception' di sini
        return ""

# --- RUTE CETAK KUITANSI ---
@app.route('/cetak_kuitansi/<int:id>')
@login_required
def cetak_kuitansi(id):
    # Ambil data iuran berdasarkan ID
    data_iuran = Iuran.query.get_or_404(id)
    # Ambil identitas aplikasi untuk header
    identitas_app = Identitas.query.first()
    
    # Generate terbilang
    teks_terbilang = num_to_words(data_iuran.jumlah) + ""
    
    return render_template('kuitansi.html', 
                           data=data_iuran, 
                           identitas=identitas_app,
                           terbilang=teks_terbilang)

@app.route('/hapus_iuran/<int:id>')
@login_required
def hapus_iuran(id):
    db.session.delete(Iuran.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('index'))

# --- RUTE PENGELUARAN ---
@app.route('/pengeluaran', methods=['GET', 'POST'])
@login_required
def pengeluaran():
    if request.method == 'POST':
        dt = get_date_obj(request.form.get('tanggal')) or datetime.now(timezone.utc)
        db.session.add(Pengeluaran(keterangan=request.form.get('keterangan'), 
                                   jumlah=float(request.form.get('jumlah')), tanggal=dt))
        db.session.commit()
        return redirect(url_for('pengeluaran'))
    data = Pengeluaran.query.order_by(Pengeluaran.tanggal.desc()).all()
    return render_template('pengeluaran.html', data=data)

@app.route('/edit_pengeluaran/<int:id>', methods=['POST'])
@login_required
def edit_pengeluaran(id):
    p = Pengeluaran.query.get_or_404(id)
    p.keterangan = request.form.get('keterangan')
    p.jumlah = float(request.form.get('jumlah'))
    if request.form.get('tanggal'):
        p.tanggal = get_date_obj(request.form.get('tanggal'))
    db.session.commit()
    return redirect(url_for('pengeluaran'))

@app.route('/hapus_pengeluaran/<int:id>')
@login_required
def hapus_pengeluaran(id):
    db.session.delete(Pengeluaran.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('pengeluaran'))

# --- RUTE LAPORAN ---
@app.route('/laporan')
@login_required
def laporan():
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    s_dt = get_date_obj(start_str)
    e_dt = get_date_obj(end_str)
    
    saldo_awal = 0
    if s_dt:
        sum_i = db.session.query(db.func.sum(Iuran.jumlah)).filter(Iuran.tanggal < s_dt).scalar() or 0
        sum_p = db.session.query(db.func.sum(Pengeluaran.jumlah)).filter(Pengeluaran.tanggal < s_dt).scalar() or 0
        saldo_awal = sum_i - sum_p

    i_q = Iuran.query
    p_q = Pengeluaran.query

    if s_dt:
        i_q = i_q.filter(Iuran.tanggal >= s_dt)
        p_q = p_q.filter(Pengeluaran.tanggal >= s_dt)
    if e_dt:
        i_q = i_q.filter(Iuran.tanggal <= e_dt)
        p_q = p_q.filter(Pengeluaran.tanggal <= e_dt)

    tx = []
    for i in i_q.all(): 
        tx.append({'tanggal': i.tanggal, 'keterangan': f"IPL: {i.nama_warga} ({i.bulan_iuran})", 'masuk': i.jumlah, 'keluar': 0})
    for p in p_q.all(): 
        tx.append({'tanggal': p.tanggal, 'keterangan': p.keterangan, 'masuk': 0, 'keluar': p.jumlah})
    
    tx.sort(key=lambda x: x['tanggal'])
    
    sb = saldo_awal
    for t in tx:
        sb += (t['masuk'] - t['keluar'])
        t['saldo_akhir'] = sb

    return render_template('laporan.html', transaksi=tx, saldo_awal=saldo_awal, 
                           masuk=sum(t['masuk'] for t in tx), keluar=sum(t['keluar'] for t in tx), saldo_akhir=sb)

@app.route('/laporan/tunggakan')
@login_required
def tunggakan_page():
    bulan = request.args.get('bulan')
    tahun = request.args.get('tahun')
    zona = request.args.get('zona')
    
    list_z = [z[0] for z in db.session.query(Warga.zona).distinct().all() if z[0]]
    
    if not (bulan and tahun):
        return render_template('tunggakan.html', data=[], list_zona=list_z, periode="")

    iuran_query = Iuran.query.filter(Iuran.bulan_iuran == bulan)
    iuran_query = iuran_query.filter(extract('year', Iuran.tanggal) == int(tahun))
    
    sudah_bayar = {i.nama_warga for i in iuran_query.all()}
    
    query_w = Warga.query
    if zona: 
        query_w = query_w.filter_by(zona=zona)
    
    data_tunggakan = [w for w in query_w.all() if w.nama not in sudah_bayar]
    
    periode = f"{bulan} {tahun}"
    return render_template('tunggakan.html', data=data_tunggakan, list_zona=list_z, 
                           bulan_selected=bulan, tahun_selected=tahun, zona_selected=zona, periode=periode)

# --- RUTE MASTER WARGA ---
@app.route('/warga') 
@app.route('/anggota') 
@app.route('/pelanggan')
@login_required
def warga_page():
    return render_template('warga.html', data=Warga.query.order_by(Warga.nama.asc()).all())

@app.route('/<label>/tambah', methods=['POST'])
@login_required
def tambah_warga(label):
    f = request.form
    nama = f.get('nama').strip()
    
    if nama and not Warga.query.filter_by(nama=nama).first():
        baru = Warga(
            nama=nama, 
            blok=f.get('blok'), 
            no_hp=f.get('no_hp'), 
            alamat=f.get('alamat'),
            zona=f.get('zona')
        )
        db.session.add(baru)
        db.session.commit()
        flash(f"Data {label} berhasil ditambahkan.", "success")
    else:
        flash(f"Nama {label} sudah ada atau kosong!", "warning")
    
    return redirect(url_for('warga_page'))

@app.route('/<label>/edit/<int:id>', methods=['POST'])
@login_required
def edit_warga(label, id):
    w = Warga.query.get_or_404(id)
    f = request.form
    
    w.nama = f.get('nama')
    w.alamat = f.get('alamat')
    w.blok = f.get('blok')
    w.no_hp = f.get('no_hp')
    w.zona = f.get('zona')
    
    db.session.commit()
    flash(f"Data {label} diperbarui.", "success")
    return redirect(url_for('warga_page'))

@app.route('/<label>/hapus/<int:id>')
@login_required
def hapus_warga(label, id):
    w = Warga.query.get_or_404(id)
    db.session.delete(w)
    db.session.commit()
    flash(f"Data {label} dihapus.", "warning")
    return redirect(url_for('warga_page'))

@app.route('/<label>/upload_masal', methods=['POST'])
@login_required
def upload_masal_warga(label):
    file = request.files.get('file_masal')
    if file and file.filename != '':
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            
            count = 0
            for index, row in df.iterrows():
                nama_val = str(row.get('nama', '')).strip()
                if nama_val and not Warga.query.filter_by(nama=nama_val).first():
                    w_baru = Warga(
                        nama=nama_val,
                        alamat=row.get('alamat', ''),
                        blok=row.get('blok', ''),
                        no_hp=str(row.get('no_hp', '')),
                        zona=row.get('zona', '')
                    )
                    db.session.add(w_baru)
                    count += 1
            
            db.session.commit()
            flash(f"Berhasil mengimpor {count} data {label} baru!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Gagal impor: {str(e)}", "danger")
    return redirect(url_for('warga_page'))

# --- RUTE IDENTITAS & TENTANG ---
@app.route('/identitas')
@login_required
def identitas_page():
    return render_template('identitas.html', data=Identitas.query.all())

@app.route('/identitas/edit/<int:id>', methods=['POST'])
@login_required
def edit_identitas(id):
    i = Identitas.query.get_or_404(id)
    f = request.form
    i.nama_app = f.get('nama_app')
    i.alamat = f.get('alamat')
    i.kota = f.get('kota')
    i.no_hp = f.get('no_hp')
    i.ketua = f.get('ketua')
    i.sekretaris = f.get('sekretaris')
    i.keterangan = f.get('keterangan')
    i.label_anggota = f.get('label_anggota')
    i.label_iuran = f.get('label_iuran')
    i.label_tingkat1 = f.get('label_tingkat1')
    i.label_tingkat2 = f.get('label_tingkat2')
    i.label_tingkat3 = f.get('label_tingkat3')
    db.session.commit()
    flash("Identitas aplikasi diperbarui.", "success")
    return redirect(url_for('identitas_page'))

@app.route('/tentang')
def tentang_publik():
    iden = Identitas.query.first()
    return render_template('tentang_publik.html', identitas=iden)

# ==========================================
# 7. LAUNCHER (CHROME & SERVER - HYBRID)
# ==========================================
def launch_app():
    url = "http://127.0.0.1:5005"
    sys_plat = platform.system()
    
    try:
        if sys_plat == 'Windows':
            # Gunakan folder TEMP standar Windows
            temp_profile = os.path.join(os.environ.get('TEMP', 'C:\\Temp'), 'aurora_chrome_profile')
            # Perintah start khusus Windows
            chrome_cmd = f'start chrome --app="{url}" --start-maximized --user-data-dir="{temp_profile}" --no-first-run'
            subprocess.Popen(chrome_cmd, shell=True)
            
        elif sys_plat == 'Darwin':  # macOS
            # Lokasi standar Chrome di macOS
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            # Folder profile sementara di macOS
            temp_profile = os.path.expanduser("~/Library/Application Support/AuroraChromeProfile")
            
            if os.path.exists(chrome_path):
                # Menjalankan Chrome dalam mode App (tanpa toolbar/address bar)
                subprocess.Popen([
                    chrome_path, 
                    f"--app={url}", 
                    f"--user-data-dir={temp_profile}", 
                    "--no-first-run"
                ])
            else:
                # Fallback jika Chrome tidak ditemukan di folder Applications
                subprocess.Popen(['open', url])
                
        else:  # Linux atau lainnya
            webbrowser.open_new(url)
            
    except Exception as e:
        print(f"Gagal membuka browser otomatis: {e}")
        # Last resort fallback
        webbrowser.open_new(url)

if __name__ == '__main__':
    # Membuka browser setelah 1.5 detik agar server siap dulu
    # WERKZEUG_RUN_MAIN mencegah browser terbuka 2x saat Flask reload (debug mode)
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        Timer(1.5, launch_app).start()
    
    # Matikan reloader jika ingin mencoba launcher dengan lebih stabil
    app.run(port=5005, debug=True, use_reloader=True)