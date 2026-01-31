import tkinter as tk
from tkinter import ttk, messagebox
import hashlib

# ==========================================
# KONFIGURASI
# ==========================================
SECRET_SALT = "AURORA_WARGA_SECURE_2026_!@#" 
FONT_UI = 'Segoe UI'  # Konstanta font untuk UI
FONT_MONO = 'Consolas' # Konstanta font untuk input/output kode

class KeyGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Aurora KeyGen - Admin Tool")
        self.root.geometry("450x350")
        self.root.resizable(False, False)
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Menggunakan konstanta FONT_UI
        style.configure('TButton', font=(FONT_UI, 10, 'bold'), borderwidth=1)
        style.configure('TLabel', font=(FONT_UI, 10))
        style.configure('Header.TLabel', font=(FONT_UI, 14, 'bold'), foreground="#0d6efd")

        # Container
        main_frame = ttk.Frame(root, padding="30")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header = ttk.Label(main_frame, text="LICENSING GENERATOR", style='Header.TLabel')
        header.pack(pady=(0, 20))

        # Input HWID
        lbl_hwid = ttk.Label(main_frame, text="Masukkan Machine ID (HWID) dari Warga:")
        lbl_hwid.pack(anchor=tk.W)
        
        self.entry_hwid = ttk.Entry(main_frame, font=(FONT_MONO, 11))
        self.entry_hwid.pack(fill=tk.X, pady=(5, 15))
        self.entry_hwid.focus()

        # Tombol Generate
        btn_gen = ttk.Button(main_frame, text="GENERATE SERIAL NUMBER", command=self.generate_serial)
        btn_gen.pack(fill=tk.X, pady=10)

        # Output Serial
        lbl_result = ttk.Label(main_frame, text="Serial Number Hasil:")
        lbl_result.pack(anchor=tk.W, pady=(15, 0))

        self.entry_result = ttk.Entry(main_frame, font=(FONT_MONO, 14, 'bold'), foreground="#198754", justify='center')
        self.entry_result.pack(fill=tk.X, pady=(5, 10))

        # Tombol Copy
        btn_copy = ttk.Button(main_frame, text="Salin ke Clipboard", command=self.copy_to_clipboard)
        btn_copy.pack(fill=tk.X)

        # Footer
        footer = ttk.Label(main_frame, text="Hanya untuk Administrator", font=(FONT_UI, 8), foreground="gray")
        footer.pack(side=tk.BOTTOM, pady=(20, 0))

    def generate_serial(self):
        hwid = self.entry_hwid.get().strip()
        
        if not hwid:
            messagebox.showwarning("Peringatan", "Harap masukkan Machine ID (HWID) terlebih dahulu!")
            return

        try:
            # --- LOGIKA INTI ---
            raw_data = f"{hwid}::{SECRET_SALT}"
            hashed = hashlib.sha256(raw_data.encode()).hexdigest()
            serial_key = hashed[:20].upper()
            
            self.entry_result.delete(0, tk.END)
            self.entry_result.insert(0, serial_key)
            
        except Exception as e:
            messagebox.showerror("Error", f"Terjadi kesalahan: {str(e)}")

    def copy_to_clipboard(self):
        serial = self.entry_result.get()
        if serial:
            self.root.clipboard_clear()
            self.root.clipboard_append(serial)
            self.root.update()
            messagebox.showinfo("Sukses", "Serial Number berhasil disalin!")

if __name__ == "__main__":
    root = tk.Tk()
    app = KeyGeneratorApp(root)
    root.mainloop()