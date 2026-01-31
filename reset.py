import tkinter as tk
from tkinter import ttk, messagebox
import winreg

# ==========================================
# KONFIGURASI
# ==========================================
APP_REG_PATH = r"Software\AuroraLedgerWarga_v1"
FONT_UI = 'Segoe UI'
STYLE_DANGER = 'Danger.TButton'  # Konstanta untuk Style Tombol Merah

class ResetLicenseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Reset Activation Tool")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        
        # Style Configuration
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', font=(FONT_UI, 10, 'bold'), borderwidth=1)
        style.configure('TLabel', font=(FONT_UI, 10))
        
        # Menggunakan konstanta STYLE_DANGER
        style.configure(STYLE_DANGER, background='#dc3545', foreground='white')
        style.map(STYLE_DANGER, background=[('active', '#bb2d3b')])

        # Layout Container
        main_frame = ttk.Frame(root, padding="25")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Icon & Header
        lbl_icon = ttk.Label(main_frame, text="⚠️", font=(FONT_UI, 40))
        lbl_icon.pack()
        
        lbl_header = ttk.Label(main_frame, text="RESET SYSTEM LICENSE", font=(FONT_UI, 14, 'bold'), foreground="#dc3545")
        lbl_header.pack(pady=(0, 10))

        lbl_desc = ttk.Label(main_frame, text="Aksi ini akan menghapus Serial Number,\nTanggal Aktivasi, dan Data Trial dari Registry Windows.", justify='center')
        lbl_desc.pack(pady=(0, 20))

        # Status Label
        self.lbl_status = ttk.Label(main_frame, text="Status: Menunggu aksi...", foreground="gray", font=(FONT_UI, 9))
        self.lbl_status.pack(pady=(0, 15))

        # Tombol Reset (Menggunakan konstanta STYLE_DANGER)
        btn_reset = ttk.Button(main_frame, text="HAPUS DATA LISENSI (RESET)", style=STYLE_DANGER, command=self.confirm_reset)
        btn_reset.pack(fill=tk.X, ipady=5)

        # Footer
        footer = ttk.Label(main_frame, text="Tools ini hanya untuk Developer/Admin", font=(FONT_UI, 8), foreground="gray")
        footer.pack(side=tk.BOTTOM, pady=(10, 0))

    def confirm_reset(self):
        confirm = messagebox.askyesno(
            "Konfirmasi Hapus", 
            "Apakah Anda yakin ingin menghapus semua data lisensi?\nAplikasi akan kembali ke mode 'Baru Diinstall' (Trial Reset).",
            icon='warning'
        )
        if confirm:
            self.perform_reset()

    def perform_reset(self):
        try:
            # Membuka Key Registry
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, APP_REG_PATH, 0, winreg.KEY_ALL_ACCESS)
            except FileNotFoundError:
                messagebox.showinfo("Info", "Tidak ada data lisensi yang ditemukan (Registry kosong).")
                self.lbl_status.config(text="Status: Data tidak ditemukan.", foreground="blue")
                return

            # Daftar value yang akan dihapus
            targets = ["LicenseKey", "ActivationDate", "InstallDate"]
            deleted_count = 0

            for target in targets:
                try:
                    winreg.DeleteValue(key, target)
                    deleted_count += 1
                except FileNotFoundError:
                    pass # Abaikan jika value tidak ada

            winreg.CloseKey(key)

            if deleted_count > 0:
                self.lbl_status.config(text=f"Sukses: {deleted_count} data registry dihapus.", foreground="green")
                messagebox.showinfo("Berhasil", "Data lisensi berhasil direset!\nSilakan restart aplikasi utama.")
            else:
                self.lbl_status.config(text="Status: Registry bersih (tidak ada yang dihapus).", foreground="blue")
                messagebox.showinfo("Info", "Registry sudah bersih.")

        except Exception as e:
            self.lbl_status.config(text="Error!", foreground="red")
            messagebox.showerror("Error Sistem", f"Gagal mengakses Registry:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ResetLicenseApp(root)
    root.mainloop()