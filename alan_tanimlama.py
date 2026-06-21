import cv2
import json
import os
import csv
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

class ErgonomiArayuz:
    def __init__(self, window):
        self.window = window
        self.window.title("Endüstriyel Ergonomi ve Alan Tanımlama Paneli")
        self.window.geometry("1100x650")
        self.window.configure(bg="#f0f2f5")

        # Değişkenler
        self.video_path = ""
        self.video_adi = "" # Videonun uzantısız adını tutmak için yeni değişken
        self.ilk_kare = None
        self.gosterim_karesi = None
        self.alanlar = {} 
        self.video_oyniyor = False
        self.video_duraklatildi = False 
        self.cap = None 

        # Sol Panel (Kontrol Paneli)
        self.sol_panel = tk.Frame(window, bg="#ffffff", width=350, bd=1, relief=tk.SOLID)
        self.sol_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        self.sol_panel.pack_propagate(False)

        # Sağ Panel (Video Gösterim Alanı)
        self.sag_panel = tk.Frame(window, bg="#dbdbdb")
        self.sag_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.video_etiket = tk.Label(self.sag_panel, text="Lütfen bir video seçin...", bg="#dbdbdb", font=("Arial", 14))
        self.video_etiket.pack(fill=tk.BOTH, expand=True)

        self.arayuz_elemanlarini_olustur()

    def arayuz_elemanlarini_olustur(self):
        # 1. Video Yükleme Bölümü
        tk.Label(self.sol_panel, text="1. ADIM: VİDEO SEÇİMİ", font=("Arial", 11, "bold"), bg="#ffffff", fg="#333333").pack(anchor=tk.W, padx=15, pady=(15, 5))
        self.btn_video_sec = tk.Button(self.sol_panel, text="📁 Video Dosyası Yükle", command=self.video_yukle, bg="#4a90e2", fg="white", font=("Arial", 10, "bold"), relief=tk.FLAT, pady=5)
        self.btn_video_sec.pack(fill=tk.X, padx=15, pady=(0, 15))

        ttk.Separator(self.sol_panel, orient='horizontal').pack(fill=tk.X, padx=15, pady=5)

        # 2. Alan Tanımlama Bölümü
        tk.Label(self.sol_panel, text="2. ADIM: ALAN TANIMLAMA", font=("Arial", 11, "bold"), bg="#ffffff", fg="#333333").pack(anchor=tk.W, padx=15, pady=10)
        
        tk.Label(self.sol_panel, text="Alanın Özel Adı (Örn: Masa, Vida Kutusu):", font=("Arial", 9), bg="#ffffff", fg="#666666").pack(anchor=tk.W, padx=15)
        self.txt_alan_adi = tk.Entry(self.sol_panel, font=("Arial", 11), bd=1, relief=tk.SOLID)
        self.txt_alan_adi.pack(fill=tk.X, padx=15, pady=(2, 10))

        self.btn_calisma_sec = tk.Button(self.sol_panel, text="🟢 Çalışma Alanı Tanımla", command=lambda: self.alan_ciz("Calisma Alani"), bg="#2ecc71", fg="white", font=("Arial", 10, "bold"), relief=tk.FLAT, state=tk.DISABLED, pady=5)
        self.btn_calisma_sec.pack(fill=tk.X, padx=15, pady=5)

        self.btn_alet_sec = tk.Button(self.sol_panel, text="🔵 Alet Alanı Tanımla", command=lambda: self.alan_ciz("Alet Alani"), bg="#3498db", fg="white", font=("Arial", 10, "bold"), relief=tk.FLAT, state=tk.DISABLED, pady=5)
        self.btn_alet_sec.pack(fill=tk.X, padx=15, pady=5)

        ttk.Separator(self.sol_panel, orient='horizontal').pack(fill=tk.X, padx=15, pady=15)

        # 3. Tanımlanan Alanlar Listesi
        tk.Label(self.sol_panel, text="TANIMLANAN ALANLARIN LİSTESİ", font=("Arial", 10, "bold"), bg="#ffffff", fg="#333333").pack(anchor=tk.W, padx=15)
        self.lst_alanlar = tk.Listbox(self.sol_panel, font=("Arial", 9), bd=1, relief=tk.SOLID, height=5)
        self.lst_alanlar.pack(fill=tk.X, padx=15, pady=5)

        # 4. Kaydetme ve Video Kontrol Butonları
        self.btn_kaydet = tk.Button(self.sol_panel, text="💾 Seçimleri Dosyaya Kaydet", command=self.dosyaya_kaydet, bg="#e67e22", fg="white", font=("Arial", 10, "bold"), relief=tk.FLAT, state=tk.DISABLED, pady=5)
        self.btn_kaydet.pack(fill=tk.X, padx=15, pady=5)

        # VİDEOYU BAŞLATMA BUTONU
        self.btn_video_baslat = tk.Button(self.sol_panel, text="▶️ Videoyu Başlat ve Analiz Et", command=self.videoyu_oynat, bg="#9b59b6", fg="white", font=("Arial", 11, "bold"), relief=tk.FLAT, state=tk.DISABLED, pady=5)
        self.btn_video_baslat.pack(fill=tk.X, padx=15, pady=(5, 2))

        # DURDUR / DEVAM ET BUTONU
        self.btn_video_durdur = tk.Button(self.sol_panel, text="⏸️ Duraklat", command=self.videoyu_duraklat_devam_ettir, bg="#f1c40f", fg="black", font=("Arial", 10, "bold"), relief=tk.FLAT, state=tk.DISABLED, pady=4)
        self.btn_video_durdur.pack(fill=tk.X, padx=15, pady=2)

        # ANALİZİ BİTİR BUTONU
        self.btn_video_bitir = tk.Button(self.sol_panel, text="⏹️ Analizi Bitir", command=self.analizi_bitir, bg="#e74c3c", fg="white", font=("Arial", 10, "bold"), relief=tk.FLAT, state=tk.DISABLED, pady=4)
        self.btn_video_bitir.pack(fill=tk.X, padx=15, pady=2)

    def video_yukle(self):
        self.video_path = filedialog.askopenfilename(
            title="Video Dosyası Seçin",
            filetypes=[("Video Dosyaları", "*.mp4 *.avi *.mov *.mkv")]
        )
        if self.video_path:
            # DİNAMİK İSİMLENDİRME: Seçilen videonun sadece adını uzantısı olmadan alıyoruz
            dosya_adi_tam = os.path.basename(self.video_path) # Örn: video1.mp4
            self.video_adi = os.path.splitext(dosya_adi_tam)[0] # Örn: video1
            
            if self.cap is not None:
                self.cap.release()
            self.cap = cv2.VideoCapture(self.video_path)
            ret, frame = self.cap.read()

            if ret:
                self.ilk_kare = frame
                self.ekranı_guncelle(self.ilk_kare)
                self.btn_calisma_sec.config(state=tk.NORMAL)
                self.btn_alet_sec.config(state=tk.NORMAL)
                self.btn_kaydet.config(state=tk.NORMAL)
                self.btn_video_baslat.config(state=tk.NORMAL)
                messagebox.showinfo("Başarılı", f"'{dosya_adi_tam}' başarıyla yüklendi!")
            else:
                messagebox.showerror("Hata", "Videodan ilk kare okunamadı.")

    def ekranı_guncelle(self, kare):
        if kare is None:
            return

        img_canvas = kare.copy()

        for alan_adi, veri in self.alanlar.items():
            x, y, w, h = veri["x"], veri["y"], veri["w"], veri["h"]
            renk = (0, 255, 0) if veri["tip"] == "Calisma Alani" else (255, 0, 0)
            cv2.rectangle(img_canvas, (x, y), (x + w, y + h), renk, 2)
            cv2.putText(img_canvas, f"{alan_adi}", (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, renk, 2)

        gorunum_w = self.sag_panel.winfo_width() if self.sag_panel.winfo_width() > 100 else 700
        gorunum_h = self.sag_panel.winfo_height() if self.sag_panel.winfo_height() > 100 else 550
        
        img_rgb = cv2.cvtColor(img_canvas, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        img_pil.thumbnail((gorunum_w, gorunum_h))
        
        self.gosterim_karesi = ImageTk.PhotoImage(img_pil)
        self.video_etiket.config(image=self.gosterim_karesi, text="")

    def alan_ciz(self, alan_tipi):
        ozel_isim = self.txt_alan_adi.get().strip()
        if not ozel_isim:
            messagebox.showwarning("Uyarı", "Lütfen önce alana vermek istediğiniz ismi yazın!")
            return

        if ozel_isim in self.alanlar:
            messagebox.showwarning("Uyarı", "Bu isimde bir alan zaten mevcut.")
            return

        messagebox.showinfo("Seçim Başlıyor", f"Şimdi açılacak harici pencerede fareyle '{ozel_isim}' bölgesini seçip ENTER'a basın.")
        
        pencere_adi = f"{ozel_isim} Secimi (ENTER'a basin)"
        cv2.namedWindow(pencere_adi, cv2.WINDOW_NORMAL)
        roi = cv2.selectROI(pencere_adi, self.ilk_kare, fromCenter=False, showCrosshair=True)
        cv2.destroyWindow(pencere_adi)

        if roi[2] > 0 and roi[3] > 0:
            self.alanlar[ozel_isim] = {
                "tip": alan_tipi, "x": int(roi[0]), "y": int(roi[1]), "w": int(roi[2]), "h": int(roi[3])
            }
            self.lst_alanlar.insert(tk.END, f"[{'Çalışma' if alan_tipi=='Calisma Alani' else 'Alet'}] {ozel_isim}")
            self.txt_alan_adi.delete(0, tk.END)
            self.ekranı_guncelle(self.ilk_kare)
        else:
            messagebox.showwarning("İptal Edildi", "Alan seçimi yapılmadı.")

    def dosyaya_kaydet(self):
        if not self.alanlar:
            messagebox.showwarning("Uyarı", "Kaydedilecek hiçbir alan tanımlanmadı!")
            return

        # DİNAMİK İSİMLENDİRME UYGULANIYOR
        json_dosya_adi = f"{self.video_adi}_alanlar.json"
        csv_dosya_adi = f"{self.video_adi}_alanlar.csv"

        # 1. JSON OLARAK KAYDET
        with open(json_dosya_adi, "w", encoding="utf-8") as f:
            json.dump(self.alanlar, f, indent=4, ensure_ascii=False)

        # 2. CSV OLARAK KAYDET
        try:
            with open(csv_dosya_adi, mode="w", newline="", encoding="utf-8-sig") as f:
                yazar = csv.writer(f, delimiter=";")
                yazar.writerow(["Alan Adi", "Alan Tipi", "X Koordinati", "Y Koordinati", "Genislik (W)", "Yukseklik (H)"])
                
                for alan_adi, veri in self.alanlar.items():
                    yazar.writerow([
                        alan_adi,
                        veri["tip"],
                        veri["x"],
                        veri["y"],
                        veri["w"],
                        veri["h"]
                    ])
                    
            messagebox.showinfo("Başarılı", f"Alanlar video adına özel olarak kaydedildi!\n\n1. {json_dosya_adi}\n2. {csv_dosya_adi}")
        except Exception as e:
            messagebox.showerror("Hata", f"CSV dosyası kaydedilirken hata oluştu: {str(e)}")

    def videoyu_oynat(self):
        if not self.video_path:
            return
        
        self.video_oyniyor = True
        self.video_duraklatildi = False
        self.cap = cv2.VideoCapture(self.video_path)
        fps = self.cap.get(cv2.CAP_PROP_FPS) if self.cap.get(cv2.CAP_PROP_FPS) > 0 else 30
        
        self.btn_video_baslat.config(state=tk.DISABLED)
        self.btn_video_durdur.config(state=tk.NORMAL, text="⏸️ Duraklat")
        self.btn_video_bitir.config(state=tk.NORMAL)
        
        def kare_ilerlet():
            if not self.video_oyniyor:
                return

            if self.video_duraklatildi:
                self.window.after(100, kare_ilerlet)
                return

            ret, frame = self.cap.read()
            if ret:
                mevcut_kare = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
                gecen_saniye = mevcut_kare / fps
                
                cv2.putText(frame, f"Sure: {gecen_saniye:.2f} sn", (20, 40), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                self.ekranı_guncelle(frame)
                
                delay = int(1000 / fps)
                self.window.after(delay, kare_ilerlet)
            else:
                self.analiz_dongusunu_kapat()
                messagebox.showinfo("Bitti", "Video sonuna gelindi. Analiz tamamlandı!")

        kare_ilerlet()

    def videoyu_duraklat_devam_ettir(self):
        if not self.video_oyniyor:
            return
            
        if not self.video_duraklatildi:
            self.video_duraklatildi = True
            self.btn_video_durdur.config(text="▶️ Devam Et")
            print("[BİLGİ] Video duraklatıldı.")
        else:
            self.video_duraklatildi = False
            self.btn_video_durdur.config(text="⏸️ Duraklat")
            print("[BİLGİ] Video devam ediyor.")

    def analizi_bitir(self):
        if messagebox.askyesno("Analizi Bitir", "Video analizini şu anki saniyede sonlandırmak istiyor musunuz?"):
            self.analiz_dongusunu_kapat()
            messagebox.showinfo("Sonlandırıldı", "Analiz kullanıcı tarafından bitirildi!")

    def analiz_dongusunu_kapat(self):
        self.video_oyniyor = False
        self.video_duraklatildi = False
        if self.cap is not None:
            self.cap.release()
        
        self.btn_video_baslat.config(state=tk.NORMAL)
        self.btn_video_durdur.config(state=tk.DISABLED, text="⏸️ Duraklat")
        self.btn_video_bitir.config(state=tk.DISABLED)
        
        if self.ilk_kare is not None:
            self.ekranı_guncelle(self.ilk_kare)

if __name__ == "__main__":
    root = tk.Tk()
    app = ErgonomiArayuz(root)
    root.after(500, app.ekranı_guncelle, app.ilk_kare)
    root.mainloop()