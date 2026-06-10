import cv2
import json
import os
import csv
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
from datetime import datetime
from el_takip_analizi import el_takip_ve_ergonomi_motoru_kare, excel_raporu_kaydet

class ErgonomiArayuz:
    def __init__(self, window):
        self.window = window
        self.window.title("Endüstriyel Ergonomi ve Alan Tanımlama Paneli")
        self.window.geometry("1100x650")
        self.window.configure(bg="#f0f2f5")

        # Değişkenler
        self.video_path = ""
        self.video_adi = "" 
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

        self.btn_calisma_sec = tk.Button(self.sol_panel, text="🟢 Çalışma Alanı Tanımla", command=lambda: self.alan_ciz("Calisma Alanı"), bg="#2ecc71", fg="white", font=("Arial", 10, "bold"), relief=tk.FLAT, state=tk.DISABLED, pady=5)
        self.btn_calisma_sec.pack(fill=tk.X, padx=15, pady=5)

        self.btn_alet_sec = tk.Button(self.sol_panel, text="🔵 Alet Alanı Tanımla", command=lambda: self.alan_ciz("Alet Alanı"), bg="#3498db", fg="white", font=("Arial", 10, "bold"), relief=tk.FLAT, state=tk.DISABLED, pady=5)
        self.btn_alet_sec.pack(fill=tk.X, padx=15, pady=5)

        ttk.Separator(self.sol_panel, orient='horizontal').pack(fill=tk.X, padx=15, pady=15)

        # 3. Tanımlanan Alanlar Listesi
        tk.Label(self.sol_panel, text="TANIMLANAN ALANLARIN LİSTESİ", font=("Arial", 10, "bold"), bg="#ffffff", fg="#333333").pack(anchor=tk.W, padx=15)
        self.lst_alanlar = tk.Listbox(self.sol_panel, font=("Arial", 9), bd=1, relief=tk.SOLID, height=5)
        self.lst_alanlar.pack(fill=tk.X, padx=15, pady=5)

        # 4. Kaydetme ve Video Kontrol Butonları
        self.btn_kaydet = tk.Button(self.sol_panel, text="💾 Seçimleri Dosyaya Kaydet", command=self.dosyaya_kaydet, bg="#e67e22", fg="white", font=("Arial", 10, "bold"), relief=tk.FLAT, state=tk.DISABLED, pady=5)
        self.btn_kaydet.pack(fill=tk.X, padx=15, pady=5)

        # VİDEOYU BAŞLATMA BUTONU - Buton komutunu temiz 'videoyu_oynat' fonksiyonuna bağladık
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
            dosya_adi_tam = os.path.basename(self.video_path) 
            self.video_adi = os.path.splitext(dosya_adi_tam)[0] 
            
            self.alanlar = {}
            self.lst_alanlar.delete(0, tk.END)

            if self.cap is not None:
                self.cap.release()
            self.cap = cv2.VideoCapture(self.video_path)
            ret, frame = self.cap.read()

            if ret:
                self.ilk_kare = frame
                self.gecmis_kayitlari_kontrol_et_ve_yukle()
                self.ekranı_guncelle(self.ilk_kare)
                
                self.btn_calisma_sec.config(state=tk.NORMAL)
                self.btn_alet_sec.config(state=tk.NORMAL)
                self.btn_kaydet.config(state=tk.NORMAL)
                self.btn_video_baslat.config(state=tk.NORMAL)
            else:
                messagebox.showerror("Hata", "Videodan ilk kare okunamadı.")

    def gecmis_kayitlari_kontrol_et_ve_yukle(self):
        gecmis_dosyalar = []
        for dosya in os.listdir("."):
            if dosya.startswith(f"{self.video_adi}_alanlar_") and dosya.endswith(".json"):
                gecmis_dosyalar.append(dosya)
        
        if not gecmis_dosyalar:
            return

        gecmis_dosyalar.sort(reverse=True)

        secim_penceresi = tk.Toplevel(self.window)
        secim_penceresi.title("Geçmiş Kayıt Seçimi")
        secim_penceresi.geometry("450x300")
        secim_penceresi.configure(bg="#ffffff")
        secim_penceresi.transient(self.window)
        secim_penceresi.grab_set()

        tk.Label(secim_penceresi, text="Bu videoya ait geçmiş alan seçimleri bulundu.\nLütfen yüklemek istediğiniz analizi seçin:", 
                 font=("Arial", 10, "bold"), bg="#ffffff", fg="#333333", justify=tk.LEFT).pack(padx=15, pady=15)

        liste_kutusu = tk.Listbox(secim_penceresi, font=("Arial", 10), bd=1, relief=tk.SOLID)
        liste_kutusu.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        for dosya in gecmis_dosyalar:
            try:
                zaman_parcasi = dosya.replace(f"{self.video_adi}_alanlar_", "").replace(".json", "")
                dt = datetime.strptime(zaman_parcasi, "%Y%m%d_%H%M%S")
                gosterim_adi = dt.strftime("%d.%m.%Y - %H:%M:%S")
            except:
                gosterim_adi = dosya
            
            liste_kutusu.insert(tk.END, gosterim_adi)
        
        liste_kutusu.selection_set(0)

        def yukle_ve_kapat():
            secili_indis = liste_kutusu.curselection()
            if secili_indis:
                secilen_dosya = gecmis_dosyalar[secili_indis[0]]
                try:
                    with open(secilen_dosya, "r", encoding="utf-8") as f:
                        self.alanlar = json.load(f)
                    
                    self.lst_alanlar.delete(0, tk.END)
                    for alan_adi, veri in self.alanlar.items():
                        tip_str = 'Çalışma' if veri['tip']=='Calisma Alanı' else 'Alet'
                        self.lst_alanlar.insert(tk.END, f"[{tip_str}] {alan_adi}")
                    
                    self.ekranı_guncelle(self.ilk_kare)
                    print(f"[BAŞARILI] Alanlar '{secilen_dosya}' dosyasından geri yüklendi.")
                except Exception as e:
                    messagebox.showerror("Hata", f"Kayıt yüklenirken hata oluştu: {str(e)}")
            secim_penceresi.destroy()

        def iptal_et_ve_kapat():
            secim_penceresi.destroy()

        buton_grup = tk.Frame(secim_penceresi, bg="#ffffff")
        buton_grup.pack(fill=tk.X, padx=15, pady=15)

        tk.Button(buton_grup, text="❌ İptal (Sıfırdan Çiz)", command=iptal_et_ve_kapat, bg="#95a5a6", fg="white", font=("Arial", 9, "bold"), relief=tk.FLAT, padx=10, pady=5).pack(side=tk.LEFT)
        tk.Button(buton_grup, text="✅ Seçilen Analizi Yükle", command=yukle_ve_kapat, bg="#2ecc71", fg="white", font=("Arial", 9, "bold"), relief=tk.FLAT, padx=10, pady=5).pack(side=tk.RIGHT)

        self.window.wait_window(secim_penceresi)

    def ekranı_guncelle(self, kare):
        if kare is None:
            return

        img_canvas = kare.copy()

        for alan_adi, veri in self.alanlar.items():
            x, y, w, h = veri["x"], veri["y"], veri["w"], veri["h"]
            renk = (0, 255, 0) if veri["tip"] == "Calisma Alanı" else (255, 0, 0)
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
            self.lst_alanlar.insert(tk.END, f"[{'Çalışma' if alan_tipi=='Calisma Alanı' else 'Alet'}] {ozel_isim}")
            self.txt_alan_adi.delete(0, tk.END)
            self.ekranı_guncelle(self.ilk_kare)
        else:
            messagebox.showwarning("İptal Edildi", "Alan seçimi yapılmadı.")

    def dosyaya_kaydet(self):
        if not self.alanlar:
            messagebox.showwarning("Uyarı", "Kaydedilecek hiçbir alan tanımlanmadı!")
            return

        zaman_damgasi = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_dosya_adi = f"{self.video_adi}_alanlar_{zaman_damgasi}.json"
        csv_dosya_adi = f"{self.video_adi}_alanlar_{zaman_damgasi}.csv"

        with open(json_dosya_adi, "w", encoding="utf-8") as f:
            json.dump(self.alanlar, f, indent=4, ensure_ascii=False)

        try:
            with open(csv_dosya_adi, mode="w", newline="", encoding="utf-8-sig") as f:
                yazar = csv.writer(f, delimiter=";")
                yazar.writerow(["Alan Adi", "Alan Tipi", "X Koordinati", "Y Koordinati", "Genislik (W)", "Yukseklik (H)"])
                
                for alan_adi, veri in self.alanlar.items():
                    yazar.writerow([
                        alan_adi, veri["tip"], veri["x"], veri["y"], veri["w"], veri["h"]
                    ])
                    
            messagebox.showinfo("Başarılı", f"Alanlar benzersiz zaman damgasıyla kaydedildi!\n\n1. {json_dosya_adi}\n2. {csv_dosya_adi}")
        except Exception as e:
            messagebox.showerror("Hata", f"CSV dosyası kaydedilirken hata oluştu: {str(e)}")

    def videoyu_oynat(self):
        """Yapay zeka ve zaman etüdü döngüsünü içeren ana video oynatıcı fonksiyon."""
        if not self.video_path:
            return
        
        self.video_oyniyor = True
        self.video_duraklatildi = False
        self.btn_video_baslat.config(state=tk.DISABLED)
        self.btn_video_durdur.config(state=tk.NORMAL, text="⏸️ Duraklat")
        self.btn_video_bitir.config(state=tk.NORMAL)

        self.durum_hafizasi = {
            "alan_sureleri": {alan: 0.0 for alan in self.alanlar},
            "alan_kare_sayaclari": {alan: 0 for alan in self.alanlar},
            "hareket_sureleri": {
                "Kutulara Dogru Uzanma": 0.0, "Malzeme Tasıma (Masaya Dogru)": 0.0,
                "Malzeme Alma / Kavrama": 0.0, "Montaj / Calısma": 0.0, "Bosta (Bekleme)": 0.0
            },
            "son_bilinen_konum": "Bosta"
        }

        if self.cap is not None:
            self.cap.release()
        self.cap = cv2.VideoCapture(self.video_path)
        
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) if self.cap.get(cv2.CAP_PROP_FPS) > 0 else 30
        self.kare_suresi = 1.0 / self.fps

        def kare_ilerlet():
            if not self.video_oyniyor:
                self.analiz_raporunu_kapat()
                return
            
            if self.video_duraklatildi:
                self.window.after(30, kare_ilerlet) # self.root hatası window olarak düzeltildi
                return

            ret, kare = self.cap.read()
            if ret:
                islenmis_kare = el_takip_ve_ergonomi_motoru_kare(
                    kare, self.alanlar, self.durum_hafizasi, self.kare_suresi, self.fps
                )
                
                mevcut_kare = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
                cv2.putText(islenmis_kare, f"Video Suresi: {mevcut_kare / self.fps:.2f} sn", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                
                self.ekranı_guncelle(islenmis_kare) # Harf uyuşmazlığı düzeltildi
                
                delay = int(1000 / self.fps)
                self.window.after(delay, kare_ilerlet)
            else:
                self.analiz_raporunu_kapat()
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
            self.analiz_raporunu_kapat()
            messagebox.showinfo("Sonlandırıldı", "Analiz kullanıcı tarafından bitirildi!")

    def analiz_raporunu_kapat(self):
        """Video akışı bittiğinde veya durdurulduğunda dosyayı kapatıp Excel raporu üreten sistem."""
        self.video_oyniyor = False
        self.video_duraklatildi = False
        if self.cap is not None:
            self.cap.release()
        
        self.btn_video_baslat.config(state=tk.NORMAL)
        self.btn_video_durdur.config(state=tk.DISABLED, text="⏸️ Duraklat")
        self.btn_video_bitir.config(state=tk.DISABLED)
        
        # Süreler biriktiyse Excel raporlamasını tetikle
        if hasattr(self, 'durum_hafizasi'):
            video_ismi = self.video_adi if self.video_adi else "video_analiz"
            excel_raporu_kaydet(video_ismi, self.durum_hafizasi["alan_sureleri"], self.durum_hafizasi["hareket_sureleri"])
            
            rapor_metni = "📊 ANALİZ EXCEL DOSYASINA KAYDEDİLDİ!\n\nÖzet Ölçümler:\n"
            for hareket, sure in self.durum_hafizasi["hareket_sureleri"].items():
                rapor_metni += f"• {hareket}: {sure:.2f} sn\n"
            messagebox.showinfo("Rapor Hazır", rapor_metni)

        if self.ilk_kare is not None:
            self.ekranı_guncelle(self.ilk_kare)

if __name__ == "__main__":
    root = tk.Tk()
    app = ErgonomiArayuz(root)
    root.after(500, app.ekranı_guncelle, app.ilk_kare)
    root.mainloop()