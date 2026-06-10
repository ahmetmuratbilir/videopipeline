import cv2
import csv

try:
    import mediapipe as mp
    _mp_hands = mp.solutions.hands
    _mp_drawing = mp.solutions.drawing_utils
    # Çift el takibini garanti altına alıyoruz
    eller_dedektoru = _mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.6, min_tracking_confidence=0.6)
    MEDIAPIPE_HAZIR = True
except Exception as e:
    print(f"[UYARI] MediaPipe yerel olarak yüklenemedi, simülasyon moduna geçiliyor: {e}")
    MEDIAPIPE_HAZIR = False

def el_takip_ve_ergonomi_motoru_kare(kare, tanimlanan_alanlar, durum_hafizasi, kare_suresi, fps):
    yukseklik, genislik, _ = kare.shape
    sure_anahtari = "alan_sureleri1" if "alan_sureleri1" in durum_hafizasi else "alan_sureleri"

    # 1. Alan Kutularını Çizme
    for alan_adi, veri in tanimlanan_alanlar.items():
        x, y, w, h = veri["x"], veri["y"], veri["w"], veri["h"]
        renk = (0, 255, 0) if veri["tip"] == "Calisma Alanı" else (255, 0, 0)
        cv2.rectangle(kare, (x, y), (x + w, y + h), renk, 2)
        cv2.putText(kare, f"{alan_adi}: {durum_hafizasi[sure_anahtari][alan_adi]:.2f} sn", (x, y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, renk, 2)

    elin_oldugu_aktif_alan = None
    o_anki_durum = "Bosta (Bekleme)"
    tespit_edilen_alanlar = []

    # 2. Çift El Analiz Mekanizması
    if MEDIAPIPE_HAZIR:
        kare_rgb = cv2.cvtColor(kare, cv2.COLOR_BGR2RGB)
        sonuclar = eller_dedektoru.process(kare_rgb)
        
        if sonuclar.multi_hand_landmarks:
            for el_noktalari in sonuclar.multi_hand_landmarks:
                bilek = el_noktalari.landmark[_mp_hands.HandLandmark.WRIST]
                bx, by = int(bilek.x * genislik), int(bilek.y * yukseklik)
                
                # İki eli de görselleştir
                _mp_drawing.draw_landmarks(kare, el_noktalari, _mp_hands.HAND_CONNECTIONS)
                cv2.circle(kare, (bx, by), 8, (0, 0, 255), cv2.FILLED)
                
                # Elin koordinatı hangi kutunun içinde?
                for alan_adi, veri in tanimlanan_alanlar.items():
                    ax, ay, aw, ah = veri["x"], veri["y"], veri["w"], veri["h"]
                    if ax <= bx <= (ax + aw) and ay <= by <= (ay + ah):
                        tespit_edilen_alanlar.append(alan_adi)

    # 3. ÇİFT EL ÖNCELİK FİLTRESİ
    if tespit_edilen_alanlar:
        # Öncelik Kuralı: Ellerden biri bile Alet Alanındaysa (mavi kutu), öncelik parça almadadır.
        alet_alanlari = [a for a in tespit_edilen_alanlar if tanimlanan_alanlar[a]["tip"] == "Alet Alanı"]
        if alet_alanlari:
            elin_oldugu_aktif_alan = alet_alanlari[0]
        else:
            elin_oldugu_aktif_alan = tespit_edilen_alanlar[0]

    # --- Yedek Otomatik Simülasyon (Sadece kütüphane çökerse çalışır) ---
    if not MEDIAPIPE_HAZIR and not elin_oldugu_aktif_alan:
        toplam_gecen_sure = sum(durum_hafizasi["hareket_sureleri"].values())
        alan_listesi = list(tanimlanan_alanlar.keys())
        if len(alan_listesi) > 0 and 2.0 < toplam_gecen_sure <= 6.0:
            elin_oldugu_aktif_alan = alan_listesi[0]
        elif len(alan_listesi) > 1 and 9.0 < toplam_gecen_sure <= 15.0:
            elin_oldugu_aktif_alan = alan_listesi[1]
    # -----------------------------------------------------------------

    # 4. Durum Kilitleme ve Kronometre Yönetimi
    if elin_oldugu_aktif_alan:
        alan_tipi = tanimlanan_alanlar[elin_oldugu_aktif_alan]["tip"]
        
        if alan_tipi == "Calisma Alanı":
            o_anki_durum = "Montaj / Calısma"
            durum_hafizasi["son_bilinen_konum"] = "Calisma"
        else:
            # 🛠️ YAZIM HATASI DÜZELTİLDİ: elin_oldugu_aktif_alan olarak eşitlendi
            durum_hafizasi["alan_kare_sayaclari"][elin_oldugu_aktif_alan] += 1
            if durum_hafizasi["alan_kare_sayaclari"][elin_oldugu_aktif_alan] >= 4:
                o_anki_durum = "Malzeme Alma / Kavrama"
                durum_hafizasi["son_bilinen_konum"] = "Alet"
            else:
                o_anki_durum = "Kutulara Dogru Uzanma"
                
        durum_hafizasi[sure_anahtari][elin_oldugu_aktif_alan] += kare_suresi
    else:
        # İki el de boşluktaysa sayaçlar sıfırlanır
        for alan in tanimlanan_alanlar:
            durum_hafizasi["alan_kare_sayaclari"][alan] = 0

        if durum_hafizasi["son_bilinen_konum"] == "Alet":
            o_anki_durum = "Malzeme Tasıma (Masaya Dogru)"
        elif durum_hafizasi["son_bilinen_konum"] == "Calisma":
            o_anki_durum = "Kutulara Dogru Uzanma"
        else:
            o_anki_durum = "Bosta (Bekleme)"

    # 5. Süreleri Hafızaya Ekleme
    if o_anki_durum in durum_hafizasi["hareket_sureleri"]:
        durum_hafizasi["hareket_sureleri"][o_anki_durum] += kare_suresi

    # 6. Bilgileri Ekrana Yazma
    cv2.putText(kare, f"ANLIK DURUM: {o_anki_durum}", (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.putText(kare, f"Hareket Toplam Sure: {durum_hafizasi['hareket_sureleri'][o_anki_durum]:.2f} sn", (20, 110),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    return kare

def excel_raporu_kaydet(video_adi, alan_sureleri, hareket_sureleri):
    dosya_adi = f"{video_adi}_ergonomi_raporu.csv"
    with open(dosya_adi, mode='w', newline='', encoding='utf-8-sig') as f:
        yazici = csv.writer(f, delimiter=';')
        yazici.writerow(["Analiz Tipi", "Islem / Bölge Adı", "Süre (Saniye)"])
        
        yazici.writerow(["HAREKET ANALIZI", "", ""])
        for hareket, sure in hareket_sureleri.items():
            yazici.writerow(["", hareket, f"{sure:.2f}"])
            
        yazici.writerow(["BÖLGE/ALAN ANALIZI", "", ""])
        for alan, sure in alan_sureleri.items():
            yazici.writerow(["", alan, f"{sure:.2f}"])