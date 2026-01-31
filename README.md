# 🚀 Aurora Ledger Warga (Hybrid Version)

Sistem manajemen keanggotaan dan iuran warga yang dirancang untuk berjalan secara hibrid di **Windows** dan **macOS**. Aplikasi ini menggunakan Flask sebagai backend dan Google Chrome sebagai interface (App Mode).

## ✨ Fitur Utama
- **Cross-Platform:** Mendukung Windows (Registry) dan macOS (File-based) untuk sistem lisensi.
- **Hybrid Launcher:** Otomatis mendeteksi Google Chrome dan membukanya dalam mode aplikasi (tanpa address bar).
- **License Manager:** Fitur Trial 30 hari dan aktivasi menggunakan Serial Number unik per perangkat (Hardware Bound).
- **Automated DB:** Otomatis membuat folder data dan database SQLite saat pertama kali dijalankan.

---

## 🛠 Struktur Proyek


```text
.
├── app.py              # Entry point aplikasi & Launcher
├── models.py           # Definisi database (SQLAlchemy)
├── login.py/admin.py   # Blueprint modul
├── data_ipl/           # Folder database & lisensi (Auto-generated)
├── static/             # File CSS, JS, dan Gambar
├── templates/          # File HTML (Jinja2)
└── .gitignore          # Konfigurasi file yang diabaikan Git