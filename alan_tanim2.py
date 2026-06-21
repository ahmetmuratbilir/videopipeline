import cv2
import json
import os
import csv
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
from datetime import datetime
from el_takip_analizi import el_takip_ve_ergonomi_motoru_kare, excel_raporu_kaydet, alanlardan_fsm_config_uret
from fsm import MOSTTracker

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
        tk.Label(self.sol_panel, text="(Sıra numarası = Alet Alanı alım sırası)", font=("Arial", 8), bg="#ffffff", fg="#999999").pack(anchor=tk.W, padx=15)

        liste_cerceve = tk.Frame(self.sol_panel, bg="#ffffff")
        liste_cerceve.pack(fill=tk.X, padx=15, pady=5)

        self.lst_alanlar = tk.Listbox(liste_cerceve, font=("Arial", 9), bd=1, relief=tk.SOLID, height=6)
        self.lst_alanlar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.lst_alanlar.bind("<<ListboxSelect>>", self.liste_secimi_degisti)

        sira_buton_cerceve = tk.Frame(liste_cerceve, bg="#ffffff")
        sira_buton_cerceve.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 0))

        self.btn_sira_yukari = tk.Button(sira_buton_cerceve, text="▲", command=lambda: self.sirayi_degistir(-1),
                                          bg="#ecf0f1", fg="#333333", font=("Arial", 9, "bold"), relief=tk.FLAT,
                                          state=tk.DISABLED, width=3)
        self.btn_sira_yukari.pack(side=tk.TOP, fill=tk.Y, expand=True, pady=(0, 2))

        self.btn_sira_asagi = tk.Button(sira_buton_cerceve, text="▼", command=lambda: self.sirayi_degistir(1),
                                         bg="#ecf0f1", fg="#333333", font=("Arial", 9, "bold"), relief=tk.FLAT,
                                         state=tk.DISABLED, width=3)
        self.btn_sira_asagi.pack(side=tk.TOP, fill=tk.Y, expand=True)

        self.btn_alan_sil = tk.Button(self.sol_panel, text="🗑️ Seçili Alanı Listeden Sil", command=self.secili_alani_sil,
                                       bg="#ecf0f1", fg="#c0392b", font=("Arial", 9, "bold"), relief=tk.FLAT, pady=4)
        self.btn_alan_sil.pack(fill=tk.X, padx=15, pady=(0, 5))

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
                    
                    self.listeyi_yenile()
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

    def listeyi_yenile(self):
        """self.alanlar sözlüğünü baz alarak listeyi numaralı şekilde yeniden çizer.
        Alet Alanı tipindeki öğeler tanımlama/alım sırasına göre 1, 2, 3... şeklinde numaralanır.
        Çalışma Alanı tipindeki öğeler sıraya girmez, ayrı bir işaretle gösterilir."""
        self.lst_alanlar.delete(0, tk.END)
        alet_sira_no = 0
        for alan_adi, veri in self.alanlar.items():
            if veri["tip"] == "Alet Alanı":
                alet_sira_no += 1
                satir = f"{alet_sira_no}) [Alet] {alan_adi}"
            else:
                satir = f"✓ [Çalışma] {alan_adi}"
            self.lst_alanlar.insert(tk.END, satir)
        self.sira_buton_durumunu_guncelle()

    def liste_secimi_degisti(self, event=None):
        self.sira_buton_durumunu_guncelle()

    def sira_buton_durumunu_guncelle(self):
        """Sadece Alet Alanı seçiliyken ve sıra değiştirmeye uygun konumdaysa
        ▲/▼ butonlarını aktif eder."""
        secili = self.lst_alanlar.curselection()
        if not secili:
            self.btn_sira_yukari.config(state=tk.DISABLED)
            self.btn_sira_asagi.config(state=tk.DISABLED)
            return

        secili_indis = secili[0]
        alan_adlari = list(self.alanlar.keys())
        secili_alan_adi = alan_adlari[secili_indis]
        secili_tip = self.alanlar[secili_alan_adi]["tip"]

        if secili_tip != "Alet Alanı":
            self.btn_sira_yukari.config(state=tk.DISABLED)
            self.btn_sira_asagi.config(state=tk.DISABLED)
            return

        alet_indisleri = [i for i, ad in enumerate(alan_adlari) if self.alanlar[ad]["tip"] == "Alet Alanı"]
        konum_alet_icinde = alet_indisleri.index(secili_indis)

        self.btn_sira_yukari.config(state=tk.NORMAL if konum_alet_icinde > 0 else tk.DISABLED)
        self.btn_sira_asagi.config(state=tk.NORMAL if konum_alet_icinde < len(alet_indisleri) - 1 else tk.DISABLED)

    def sirayi_degistir(self, yon):
        """Seçili Alet Alanını, diğer Alet Alanlarına göre bir yukarı (-1) veya bir aşağı (+1) taşır.
        Çalışma Alanı öğeleri sıralamaya dahil edilmez, yerinde kalır."""
        secili = self.lst_alanlar.curselection()
        if not secili:
            return

        secili_indis = secili[0]
        alan_adlari = list(self.alanlar.keys())
        secili_alan_adi = alan_adlari[secili_indis]

        if self.alanlar[secili_alan_adi]["tip"] != "Alet Alanı":
            return

        alet_adlari = [ad for ad in alan_adlari if self.alanlar[ad]["tip"] == "Alet Alanı"]
        konum = alet_adlari.index(secili_alan_adi)
        yeni_konum = konum + yon

        if yeni_konum < 0 or yeni_konum >= len(alet_adlari):
            return

        alet_adlari[konum], alet_adlari[yeni_konum] = alet_adlari[yeni_konum], alet_adlari[konum]

        yeni_alanlar = {}
        alet_kuyrugu = list(alet_adlari)
        for ad in alan_adlari:
            if self.alanlar[ad]["tip"] == "Alet Alanı":
                guncel_ad = alet_kuyrugu.pop(0)
                yeni_alanlar[guncel_ad] = self.alanlar[guncel_ad]
            else:
                yeni_alanlar[ad] = self.alanlar[ad]

        self.alanlar = yeni_alanlar
        self.listeyi_yenile()

        yeni_alan_adlari = list(self.alanlar.keys())
        self.lst_alanlar.selection_set(yeni_alan_adlari.index(secili_alan_adi))
        self.sira_buton_durumunu_guncelle()

    def secili_alani_sil(self):
        secili = self.lst_alanlar.curselection()
        if not secili:
            messagebox.showwarning("Uyarı", "Lütfen önce listeden silinecek bir alan seçin.")
            return

        alan_adlari = list(self.alanlar.keys())
        secilen_ad = alan_adlari[secili[0]]

        if messagebox.askyesno("Alanı Sil", f"'{secilen_ad}' alanını listeden silmek istediğinize emin misiniz?"):
            del self.alanlar[secilen_ad]
            self.listeyi_yenile()
            self.ekranı_guncelle(self.ilk_kare)

    def ekranı_guncelle(self, kare):
        if kare is None:
            return

        img_canvas = kare.copy()

        alet_sira_no = 0
        for alan_adi, veri in self.alanlar.items():
            renk = (0, 255, 0) if veri["tip"] == "Calisma Alanı" else (255, 0, 0)

            if "polygon" in veri and veri["polygon"]:
                pts = np.array(veri["polygon"], dtype=np.int32)
            else:
                # Eski (poligonsuz) kayıtlar için bounding box'ı 4 köşeli poligona çevir
                x, y, w, h = veri["x"], veri["y"], veri["w"], veri["h"]
                pts = np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], dtype=np.int32)

            cv2.polylines(img_canvas, [pts], isClosed=True, color=renk, thickness=2)

            etiket_x, etiket_y = int(pts[:, 0].min()), int(pts[:, 1].min())
            if veri["tip"] == "Alet Alanı":
                alet_sira_no += 1
                etiket = f"{alet_sira_no}) {alan_adi}"
            else:
                etiket = alan_adi

            cv2.putText(img_canvas, etiket, (etiket_x, etiket_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, renk, 2)

        gorunum_w = self.sag_panel.winfo_width() if self.sag_panel.winfo_width() > 100 else 700
        gorunum_h = self.sag_panel.winfo_height() if self.sag_panel.winfo_height() > 100 else 550
        
        img_rgb = cv2.cvtColor(img_canvas, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        img_pil.thumbnail((gorunum_w, gorunum_h))
        
        self.gosterim_karesi = ImageTk.PhotoImage(img_pil)
        self.video_etiket.config(image=self.gosterim_karesi, text="")

    def poligon_sec(self, pencere_adi, kare):
        """OpenCV penceresinde fareyle çokgen (poligon) çizimi sağlar.
        Sol tık: nokta ekler. ENTER: poligonu kapatır ve kaydeder (en az 3 nokta gerekir).
        ESC veya 'q': seçimi iptal eder. R / Backspace: son noktayı geri al.
        Geri dönüş: [[x1,y1],[x2,y2],...] veya iptal edilirse None."""
        noktalar = []
        kopya = kare.copy()

        def yeniden_ciz():
            nonlocal kopya
            kopya = kare.copy()
            for i, (px, py) in enumerate(noktalar):
                cv2.circle(kopya, (px, py), 4, (0, 0, 255), -1)
                if i > 0:
                    cv2.line(kopya, noktalar[i - 1], noktalar[i], (0, 0, 255), 2)
            if len(noktalar) > 2:
                # Son noktadan ilk noktaya kesik bir önizleme çizgisi (henüz kapanmadığını gösterir)
                cv2.line(kopya, noktalar[-1], noktalar[0], (0, 165, 255), 1)
            cv2.imshow(pencere_adi, kopya)

        def mouse_geri_cagrisi(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                noktalar.append((x, y))
                yeniden_ciz()

        cv2.namedWindow(pencere_adi, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(pencere_adi, mouse_geri_cagrisi)
        cv2.imshow(pencere_adi, kopya)

        sonuc = None
        while True:
            tus = cv2.waitKey(20) & 0xFF
            if tus == 13:  # ENTER
                if len(noktalar) >= 3:
                    sonuc = [list(p) for p in noktalar]
                    break
                else:
                    print("[UYARI] Poligon için en az 3 nokta gereklidir.")
            elif tus == 27 or tus == ord('q'):  # ESC veya q
                sonuc = None
                break
            elif tus == ord('r') or tus == 8:  # 'r' veya Backspace: son noktayı geri al
                if noktalar:
                    noktalar.pop()
                    yeniden_ciz()

        cv2.destroyWindow(pencere_adi)
        return sonuc

    def alan_ciz(self, alan_tipi):
        ozel_isim = self.txt_alan_adi.get().strip()
        if not ozel_isim:
            messagebox.showwarning("Uyarı", "Lütfen önce alana vermek istediğiniz ismi yazın!")
            return

        if ozel_isim in self.alanlar:
            messagebox.showwarning("Uyarı", "Bu isimde bir alan zaten mevcut.")
            return

        messagebox.showinfo(
            "Seçim Başlıyor",
            f"Şimdi açılacak harici pencerede fareyle '{ozel_isim}' bölgesinin köşelerine "
            f"SOL TIK ile noktalar bırakın.\n\nENTER: Poligonu kapat ve kaydet (en az 3 nokta)\n"
            f"R / Backspace: Son noktayı geri al\nESC / Q: İptal et"
        )

        pencere_adi = f"{ozel_isim} Secimi (ENTER ile kapat)"
        poligon = self.poligon_sec(pencere_adi, self.ilk_kare)

        if poligon:
            xs = [p[0] for p in poligon]
            ys = [p[1] for p in poligon]
            x, y = min(xs), min(ys)
            w, h = max(xs) - x, max(ys) - y

            self.alanlar[ozel_isim] = {
                "tip": alan_tipi,
                "x": int(x), "y": int(y), "w": int(w), "h": int(h),
                "polygon": poligon
            }
            self.listeyi_yenile()
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
                yazar.writerow(["Sira", "Alan Adi", "Alan Tipi", "X Koordinati", "Y Koordinati", "Genislik (W)", "Yukseklik (H)"])

                alet_sira_no = 0
                for alan_adi, veri in self.alanlar.items():
                    if veri["tip"] == "Alet Alanı":
                        alet_sira_no += 1
                        sira_deger = alet_sira_no
                    else:
                        sira_deger = "-"
                    yazar.writerow([
                        sira_deger, alan_adi, veri["tip"], veri["x"], veri["y"], veri["w"], veri["h"]
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
            "son_bilinen_konum": "Bosta",
            "fsm_tracker": None,
            "kare_sayaci": 0,
            "dirsek_acisi_gecmisi": {"sol": [], "sag": []}
        }

        if self.alanlar:
            try:
                fsm_config = alanlardan_fsm_config_uret(self.alanlar)
                self.durum_hafizasi["fsm_tracker"] = MOSTTracker(fsm_config)
            except Exception as e:
                print(f"[UYARI] FSM kurulumu başarısız, sıra/TMU takibi olmadan devam edilecek: {e}")

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
                self.window.after(30, kare_ilerlet)
                return

            ret, kare = self.cap.read()
            if ret:
                islenmis_kare = el_takip_ve_ergonomi_motoru_kare(
                    kare, self.alanlar, self.durum_hafizasi, self.kare_suresi, self.fps
                )

                self.ekranı_guncelle(islenmis_kare)
                
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
        
        if hasattr(self, 'durum_hafizasi'):
            video_ismi = self.video_adi if self.video_adi else "video_analiz"
            fsm_tracker = self.durum_hafizasi.get("fsm_tracker")
            dirsek_gecmisi = self.durum_hafizasi.get("dirsek_acisi_gecmisi")
            excel_raporu_kaydet(
                video_ismi,
                self.durum_hafizasi["alan_sureleri"],
                self.durum_hafizasi["hareket_sureleri"],
                fsm_tracker,
                dirsek_gecmisi
            )

            rapor_metni = "📊 ANALİZ EXCEL DOSYASINA KAYDEDİLDİ!\n\nÖzet Ölçümler:\n"
            for hareket, sure in self.durum_hafizasi["hareket_sureleri"].items():
                rapor_metni += f"• {hareket}: {sure:.2f} sn\n"

            # Dirsek açısı özeti
            if dirsek_gecmisi:
                import numpy as _np
                for taraf, aciler in dirsek_gecmisi.items():
                    if aciler:
                        ort = _np.mean(aciler)
                        maks = _np.max(aciler)
                        risk = 100.0 * sum(1 for a in aciler if a >= 150) / len(aciler)
                        rapor_metni += f"\n💪 {taraf.capitalize()} dirsek: Ort {ort:.0f}° | Maks {maks:.0f}° | Risk %{risk:.0f}"

            if fsm_tracker is not None and fsm_tracker.reported_cycles:
                rapor_metni += f"\n\n🔁 MOST/FSM Tamamlanan Çevrim Sayısı: {len(fsm_tracker.reported_cycles)}\n"
                son_cevrim = fsm_tracker.reported_cycles[-1]
                rapor_metni += f"   Son çevrim: {son_cevrim['duration_sec']} sn ({son_cevrim['tmu']} TMU), Sıra doğru mu: {son_cevrim['sequence_ok']}\n"

            messagebox.showinfo("Rapor Hazır", rapor_metni)

        if self.ilk_kare is not None:
            self.ekranı_guncelle(self.ilk_kare)

if __name__ == "__main__":
    root = tk.Tk()
    app = ErgonomiArayuz(root)
    root.after(500, app.ekranı_guncelle, app.ilk_kare)
    root.mainloop()