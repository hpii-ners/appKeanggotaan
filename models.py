from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone

# Inisialisasi DB Kosong
db = SQLAlchemy()

# --- TABEL USER (LOGIN) ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

# --- TABEL IDENTITAS APLIKASI ---
class Identitas(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_app = db.Column(db.String(100))
    alamat = db.Column(db.String(255))
    kota = db.Column(db.String(50))
    no_hp = db.Column(db.String(20))
    ketua = db.Column(db.String(100))
    sekretaris = db.Column(db.String(100))
    keterangan = db.Column(db.String(255))
    visi = db.Column(db.Text)
    misi = db.Column(db.Text)
    sejarah = db.Column(db.Text)
    label_anggota = db.Column(db.String(50), default='Warga')
    label_iuran = db.Column(db.String(50), default='Iuran')
    label_tingkat1 = db.Column(db.String(50), default='Zona')
    label_tingkat2 = db.Column(db.String(50), default='Blok')
    label_tingkat3 = db.Column(db.String(50), default='Cluster')

# --- TABEL WARGA ---
class Warga(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), unique=True, nullable=False)
    blok = db.Column(db.String(20))
    alamat = db.Column(db.Text)
    no_hp = db.Column(db.String(20))
    zona = db.Column(db.String(50))

# --- TABEL KEUANGAN (IURAN & PENGELUARAN) ---
class Iuran(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_warga = db.Column(db.String(100), nullable=False)
    blok_rumah = db.Column(db.String(20))
    no_hp = db.Column(db.String(20))
    zona = db.Column(db.String(50))
    bulan_iuran = db.Column(db.String(20))
    jumlah = db.Column(db.Float, default=0)
    keterangan = db.Column(db.String(200))
    tanggal = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Pengeluaran(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keterangan = db.Column(db.String(200))
    jumlah = db.Column(db.Float)
    tanggal = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

# --- TABEL BERITA ---
class Berita(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    judul = db.Column(db.String(200), nullable=False)
    isi = db.Column(db.Text, nullable=False)
    path_image = db.Column(db.String(255))
    tanggal = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    penulis = db.Column(db.String(100))

class Agenda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_kegiatan = db.Column(db.String(200), nullable=False)
    tanggal_kegiatan = db.Column(db.DateTime, nullable=False)
    lokasi = db.Column(db.String(200))
    keterangan = db.Column(db.Text)
    penulis = db.Column(db.String(100))