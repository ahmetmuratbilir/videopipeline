import cv2
import csv
import numpy as np
from fsm import MOSTTracker, point_in_polygon

# ── MediaPipe ─────────────────────────────────────────────────────────────────
try:
    import mediapipe as mp
    _mp_hands = mp.solutions.hands
    _mp_pose  = mp.solutions.pose
    _mp_drawing = mp.solutions.drawing_utils
    _mp_drawing_styles = mp.solutions.drawing_styles

    eller_dedektoru = _mp_hands.Hands(
        max_num_hands=2,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    )
    pose_dedektoru = _mp_pose.Pose(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        model_complexity=0
    )
    MEDIAPIPE_HAZIR = True
except Exception as e:
    print(f"[UYARI] MediaPipe yüklenemedi, simülasyon moduna geçiliyor: {e}")
    MEDIAPIPE_HAZIR = False

# ── xlsx isteğe bağlı ─────────────────────────────────────────────────────────
try:
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    XLSX_HAZIR = True
except ImportError:
    XLSX_HAZIR = False


# ── Yardımcı Fonksiyonlar ─────────────────────────────────────────────────────

def alan_poligonunu_al(veri):
    """Poligon varsa onu, yoksa bounding box'tan 4 köşeli poligon üretir."""
    if "polygon" in veri and veri["polygon"]:
        return veri["polygon"]
    x, y, w, h = veri["x"], veri["y"], veri["w"], veri["h"]
    return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]


def calculate_angle(a, b, c):
    """Üç 2B nokta arasındaki açıyı derece cinsinden hesaplar.
    b noktası açının köşesidir (dirsek). optiMOST / unified_analyzer.py ile aynı mantık."""
    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)
    c = np.array(c, dtype=np.float32)
    ba, bc = a - b, c - b
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))


def calculate_trunk_angle(hip, shoulder):
    """
    Kalça-omuz hattının dikey eksenden (yukarı vektör) sapma açısını hesaplar.
    0° = tam dikey (ideal duruş), 90° = tam yatay (öne eğilme).
    """
    hip = np.array(hip, dtype=np.float32)
    shoulder = np.array(shoulder, dtype=np.float32)
    trunk_vector = shoulder - hip
    norm = np.linalg.norm(trunk_vector)
    if norm < 1e-6:
        return None
        
    vertical_vector = np.array([0, -1], dtype=np.float32)  # Görüntü koordinatında "yukarı"
    
    cosine_angle = np.dot(trunk_vector, vertical_vector) / (norm * np.linalg.norm(vertical_vector))
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine_angle)))


def aci_rengini_al(aci):
    """Ergonomi risk rengi: ≥150° kırmızı · 120-150° sarı · <120° yeşil"""
    if aci >= 150:
        return (0, 0, 255)
    elif aci >= 120:
        return (0, 200, 255)
    return (0, 200, 0)


def alanlardan_fsm_config_uret(tanimlanan_alanlar):
    """self.alanlar → MOSTTracker workspace_config. Alet Alanları sıraya göre recipe'ye girer."""
    stations, recipe = [], []
    for alan_adi, veri in tanimlanan_alanlar.items():
        polygon = alan_poligonunu_al(veri)
        if veri["tip"] == "Calisma Alanı":
            fsm_adi = "Assembly Area"
        else:
            fsm_adi = alan_adi
            recipe.append(fsm_adi)
        stations.append({"name": fsm_adi, "polygon": polygon})
    recipe.append("Assembly Area")
    return {
        "stations": stations,
        "recipe": recipe,
        "grasp": {
            "pinch_threshold": 0.28,
            "release_threshold": 0.40,
            "velocity_threshold": 8.0,
            "grasp_confirm_time": 0.15,
            "release_confirm_time": 0.10
        }
    }


def el_landmarklarini_sozluge_cevir(el_noktalari):
    return [{"x": lm.x, "y": lm.y} for lm in el_noktalari.landmark]


# ── Aşama 4: HUD Çizim Yardımcıları ─────────────────────────────────────────

def _yari_saydam_dikdortgen(kare, x1, y1, x2, y2, renk=(0, 0, 0), alfa=0.55):
    """Video karesi üzerine yarı-saydam dolu dikdörtgen çizer (overlay tekniği)."""
    overlay = kare.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), renk, -1)
    cv2.addWeighted(overlay, alfa, kare, 1 - alfa, 0, kare)


def _ilerleme_cubugu(kare, x, y, genislik, yukseklik, oran, arka=(60, 60, 60), on=(0, 200, 100)):
    """0-1 arasında oran değeriyle yatay progress bar çizer."""
    cv2.rectangle(kare, (x, y), (x + genislik, y + yukseklik), arka, -1)
    dolu = int(genislik * max(0.0, min(1.0, oran)))
    if dolu > 0:
        cv2.rectangle(kare, (x, y), (x + dolu, y + yukseklik), on, -1)
    cv2.rectangle(kare, (x, y), (x + genislik, y + yukseklik), (120, 120, 120), 1)


def _risk_ikonu(kare, cx, cy, aci):
    """Dirsek açısına göre renkli daire (trafik ışığı) çizer."""
    renk = aci_rengini_al(aci)
    cv2.circle(kare, (cx, cy), 9, renk, -1)
    cv2.circle(kare, (cx, cy), 9, (255, 255, 255), 1)


def hud_ciz(kare, durum, fsm_metrikleri, sol_aci, sag_aci, govde_acisi, fsm_recipe, fsm_recipe_idx):
    """Ana HUD panelini video üzerine çizer.

    Parametre açıklamaları:
    - durum          : string, anlık hareket durumu
    - fsm_metrikleri : dict, MOSTTracker.get_metrics() çıktısı (veya None)
    - sol_aci, sag_aci: float veya None, dirsek açıları
    - govde_acisi    : float veya None, omurganın dikeyden sapma açısı
    - fsm_recipe     : list, reçete adımları (["Kutu1", "Kutu2", "Assembly Area"])
    - fsm_recipe_idx : int, şu anki reçete indeksi
    """
    h, w = kare.shape[:2]

    # Panel boyutu ve konumu (sol alt köşe)
    panel_x1 = 10
    panel_y1 = h - 250
    panel_x2 = 420
    panel_y2 = h - 10

    _yari_saydam_dikdortgen(kare, panel_x1, panel_y1, panel_x2, panel_y2,
                            renk=(10, 10, 20), alfa=0.65)
    # İnce çerçeve
    cv2.rectangle(kare, (panel_x1, panel_y1), (panel_x2, panel_y2), (80, 80, 140), 1)

    satir_y = panel_y1 + 22
    ic_x = panel_x1 + 12

    # ── Durum ─────────────────────────────────────────────────────────────────
    durum_renkleri = {
        "Montaj / Calısma":         (0, 255, 120),
        "Malzeme Alma / Kavrama":   (0, 200, 255),
        "Malzeme Tasıma (Masaya Dogru)": (255, 200, 0),
        "Kutulara Dogru Uzanma":    (255, 160, 40),
        "Bosta (Bekleme)":          (160, 160, 160),
    }
    d_renk = durum_renkleri.get(durum, (200, 200, 200))
    cv2.putText(kare, "DURUM", (ic_x, satir_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 180, 180), 1)
    cv2.putText(kare, durum, (ic_x + 65, satir_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, d_renk, 2)
    satir_y += 28

    # ── Dirsek Açıları + Trafik Işığı ─────────────────────────────────────────
    if sol_aci is not None:
        _risk_ikonu(kare, ic_x + 8, satir_y - 5, sol_aci)
        cv2.putText(kare, f"Sol dirsek: {sol_aci:.0f}",
                    (ic_x + 24, satir_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, aci_rengini_al(sol_aci), 1)
    else:
        cv2.putText(kare, "Sol dirsek: --", (ic_x + 24, satir_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (120, 120, 120), 1)

    satir_y += 22
    if sag_aci is not None:
        _risk_ikonu(kare, ic_x + 8, satir_y - 5, sag_aci)
        cv2.putText(kare, f"Sag dirsek: {sag_aci:.0f}",
                    (ic_x + 24, satir_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, aci_rengini_al(sag_aci), 1)
    else:
        cv2.putText(kare, "Sag dirsek: --", (ic_x + 24, satir_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (120, 120, 120), 1)

    satir_y += 22
    if govde_acisi is not None:
        _risk_ikonu(kare, ic_x + 8, satir_y - 5, govde_acisi)
        cv2.putText(kare, f"Govde (Egilme): {govde_acisi:.0f}",
                    (ic_x + 24, satir_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, aci_rengini_al(govde_acisi), 1)
    else:
        cv2.putText(kare, "Govde (Egilme): --", (ic_x + 24, satir_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (120, 120, 120), 1)
    satir_y += 26

    # ── FSM Bölümü ─────────────────────────────────────────────────────────────
    if fsm_metrikleri:
        fsm_state  = fsm_metrikleri.get("state", "IDLE")
        tmu        = fsm_metrikleri.get("tmu", 0.0)
        cycle_sn   = fsm_metrikleri.get("cycle_time_sec", 0.0)
        pinch      = fsm_metrikleri.get("pinch_ratio", 0.0)
        seq_err    = fsm_metrikleri.get("sequence_error", False)
        guidance   = fsm_metrikleri.get("guidance", "")

        # Reçete ilerleme bilgisi
        if fsm_recipe and len(fsm_recipe) > 0:
            toplam = len(fsm_recipe)
            gunceli = min(fsm_recipe_idx, toplam)
            siradaki = fsm_recipe[min(gunceli, toplam - 1)]
            cv2.putText(kare, f"Siradaki: {siradaki}  ({gunceli}/{toplam})",
                        (ic_x, satir_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.44, (200, 220, 255), 1)
            # Reçete ilerleme barı
            bar_oran = gunceli / toplam if toplam > 0 else 0
            _ilerleme_cubugu(kare, ic_x, satir_y + 5, 195, 8, bar_oran,
                             arka=(50, 50, 70), on=(80, 140, 255))
            satir_y += 25

        # FSM Durum + TMU
        fsm_renk = (0, 80, 255) if seq_err else (0, 200, 255)
        cv2.putText(kare, f"FSM: {fsm_state}  |  {cycle_sn:.1f}s  ({tmu:.0f} TMU)",
                    (ic_x, satir_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.46, fsm_renk, 1)
        satir_y += 20

        # Pinch oranı progress bar
        cv2.putText(kare, "Kavrama:", (ic_x, satir_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (180, 180, 180), 1)
        pinch_renk = (0, 80, 255) if pinch > 0.28 else (0, 200, 100)
        _ilerleme_cubugu(kare, ic_x + 72, satir_y - 9, 120, 10, pinch,
                         arka=(50, 50, 50), on=pinch_renk)
        cv2.putText(kare, f"{pinch:.2f}", (ic_x + 200, satir_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (200, 200, 200), 1)
        satir_y += 20

        # Rehberlik mesajı
        if guidance:
            cv2.putText(kare, guidance, (ic_x, satir_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 255, 180), 1)
            satir_y += 18

        # Sıra hatası uyarısı
        if seq_err:
            cv2.putText(kare, "! SIRA HATASI TESPIT EDILDI", (ic_x, satir_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 0, 255), 2)

    else:
        cv2.putText(kare, "FSM: Hazir degil (alan tanimlayin)", (ic_x, satir_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (120, 120, 120), 1)


# ── Ana Analiz Fonksiyonu ─────────────────────────────────────────────────────

def el_takip_ve_ergonomi_motoru_kare(kare, tanimlanan_alanlar, ctx, kare_suresi, fps):
    yukseklik, genislik, _ = kare.shape

    ctx.kare_sayaci += 1
    kare_sayaci = ctx.kare_sayaci

    # 1. Alan Poligonlarını Çizme
    for alan_adi, veri in tanimlanan_alanlar.items():
        renk = (0, 255, 0) if veri["tip"] == "Calisma Alanı" else (255, 0, 0)
        poligon = alan_poligonunu_al(veri)
        pts = np.array(poligon, dtype=np.int32)
        cv2.polylines(kare, [pts], isClosed=True, color=renk, thickness=2)
        etiket_x, etiket_y = int(pts[:, 0].min()), int(pts[:, 1].min())
        cv2.putText(kare,
                    f"{alan_adi}: {ctx.hand_state.alan_sureleri[alan_adi]:.2f} sn",
                    (etiket_x, etiket_y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, renk, 2)

    elin_oldugu_aktif_alan = None
    o_anki_durum = "Bosta (Bekleme)"
    tespit_edilen_alanlar = []

    # 2. MediaPipe Analizi
    if MEDIAPIPE_HAZIR:
        kare_rgb = cv2.cvtColor(kare, cv2.COLOR_BGR2RGB)

        # ── 2a. Hands ──────────────────────────────────────────────────────────
        sonuclar = eller_dedektoru.process(kare_rgb)
        if sonuclar.multi_hand_landmarks:
            for el_noktalari in sonuclar.multi_hand_landmarks:
                bilek = el_noktalari.landmark[_mp_hands.HandLandmark.WRIST]
                bx, by = int(bilek.x * genislik), int(bilek.y * yukseklik)
                _mp_drawing.draw_landmarks(kare, el_noktalari, _mp_hands.HAND_CONNECTIONS)
                cv2.circle(kare, (bx, by), 8, (0, 0, 255), cv2.FILLED)
                for alan_adi, veri in tanimlanan_alanlar.items():
                    if point_in_polygon((bx, by), alan_poligonunu_al(veri)):
                        tespit_edilen_alanlar.append(alan_adi)

            if ctx.fsm_tracker is not None:
                try:
                    ilk_el = el_landmarklarini_sozluge_cevir(sonuclar.multi_hand_landmarks[0])
                    ctx.fsm_tracker.update(ilk_el, (yukseklik, genislik))
                except Exception as e:
                    print(f"[UYARI] FSM güncellemesi başarısız: {e}")
        else:
            if ctx.fsm_tracker is not None:
                try:
                    ctx.fsm_tracker.update(None, (yukseklik, genislik))
                except Exception as e:
                    print(f"[UYARI] FSM (None) güncellemesi başarısız: {e}")

        # ── 2b. Pose (her 2 karede bir) ─────────────────────────────────────
        if kare_sayaci % 2 == 0:
            try:
                pose_sonuc = pose_dedektoru.process(kare_rgb)
                if pose_sonuc.pose_landmarks:
                    lm = pose_sonuc.pose_landmarks.landmark
                    PL = _mp_pose.PoseLandmark

                    def lm_px(idx):
                        return (int(lm[idx].x * genislik), int(lm[idx].y * yukseklik))

                    sol_omuz   = lm_px(PL.LEFT_SHOULDER)
                    sol_dirsek = lm_px(PL.LEFT_ELBOW)
                    sol_bilek  = lm_px(PL.LEFT_WRIST)
                    sag_omuz   = lm_px(PL.RIGHT_SHOULDER)
                    sag_dirsek = lm_px(PL.RIGHT_ELBOW)
                    sag_bilek  = lm_px(PL.RIGHT_WRIST)
                    sol_kalca  = lm_px(PL.LEFT_HIP)

                    sol_aci = calculate_angle(sol_omuz, sol_dirsek, sol_bilek)
                    sag_aci = calculate_angle(sag_omuz, sag_dirsek, sag_bilek)
                    govde_acisi = calculate_trunk_angle(sol_kalca, sol_omuz)

                    ctx.ergo_state.is_pose_fresh = True
                    ctx.ergo_state.dirsek_acisi_gecmisi_sol.append((sol_aci, True))
                    ctx.ergo_state.dirsek_acisi_gecmisi_sag.append((sag_aci, True))
                    if govde_acisi is not None:
                        ctx.ergo_state.govde_acisi_gecmisi.append((govde_acisi, True))

                    # İskelet çizimi
                    for (p1, p2) in [(sol_omuz, sol_dirsek), (sol_dirsek, sol_bilek),
                                     (sag_omuz, sag_dirsek), (sag_dirsek, sag_bilek)]:
                        cv2.line(kare, p1, p2, (180, 180, 180), 2)
                    for pt in [sol_omuz, sol_dirsek, sol_bilek,
                                sag_omuz, sag_dirsek, sag_bilek]:
                        cv2.circle(kare, pt, 5, (255, 255, 0), -1)

                    # Dirsek üzerine açı değeri
                    cv2.putText(kare, f"{sol_aci:.0f}",
                                (sol_dirsek[0] + 8, sol_dirsek[1]),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, aci_rengini_al(sol_aci), 2)
                    cv2.putText(kare, f"{sag_aci:.0f}",
                                (sag_dirsek[0] + 8, sag_dirsek[1]),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, aci_rengini_al(sag_aci), 2)

                    ctx.ergo_state.son_sol_aci = sol_aci
                    ctx.ergo_state.son_sag_aci = sag_aci
                    ctx.ergo_state.son_govde_acisi = govde_acisi
            except Exception as e:
                print(f"[UYARI] Pose analizi başarısız: {e}")
        else:
            ctx.ergo_state.is_pose_fresh = False
            if ctx.ergo_state.son_sol_aci is not None:
                ctx.ergo_state.dirsek_acisi_gecmisi_sol.append((ctx.ergo_state.son_sol_aci, False))
            if ctx.ergo_state.son_sag_aci is not None:
                ctx.ergo_state.dirsek_acisi_gecmisi_sag.append((ctx.ergo_state.son_sag_aci, False))
            if ctx.ergo_state.son_govde_acisi is not None:
                ctx.ergo_state.govde_acisi_gecmisi.append((ctx.ergo_state.son_govde_acisi, False))

    # 3. Çift El Öncelik Filtresi
    if tespit_edilen_alanlar:
        alet_alanlari = [a for a in tespit_edilen_alanlar
                         if tanimlanan_alanlar[a]["tip"] == "Alet Alanı"]
        elin_oldugu_aktif_alan = alet_alanlari[0] if alet_alanlari else tespit_edilen_alanlar[0]

    # --- Simülasyon (kütüphane yoksa) ----------------------------------------
    if not MEDIAPIPE_HAZIR and not elin_oldugu_aktif_alan:
        toplam = sum(ctx.hand_state.hareket_sureleri.values())
        alan_listesi = list(tanimlanan_alanlar.keys())
        if len(alan_listesi) > 0 and 2.0 < toplam <= 6.0:
            elin_oldugu_aktif_alan = alan_listesi[0]
        elif len(alan_listesi) > 1 and 9.0 < toplam <= 15.0:
            elin_oldugu_aktif_alan = alan_listesi[1]
    # -------------------------------------------------------------------------

    # 4. Durum & Kronometre
    if elin_oldugu_aktif_alan:
        alan_tipi = tanimlanan_alanlar[elin_oldugu_aktif_alan]["tip"]
        if alan_tipi == "Calisma Alanı":
            o_anki_durum = "Montaj / Calısma"
            ctx.hand_state.son_bilinen_konum = "Calisma"
        else:
            ctx.hand_state.alan_kare_sayaclari[elin_oldugu_aktif_alan] += 1
            if ctx.hand_state.alan_kare_sayaclari[elin_oldugu_aktif_alan] >= 4:
                o_anki_durum = "Malzeme Alma / Kavrama"
                ctx.hand_state.son_bilinen_konum = "Alet"
            else:
                o_anki_durum = "Kutulara Dogru Uzanma"
        ctx.hand_state.alan_sureleri[elin_oldugu_aktif_alan] += kare_suresi
    else:
        for alan in tanimlanan_alanlar:
            ctx.hand_state.alan_kare_sayaclari[alan] = 0
        if ctx.hand_state.son_bilinen_konum == "Alet":
            o_anki_durum = "Malzeme Tasıma (Masaya Dogru)"
        elif ctx.hand_state.son_bilinen_konum == "Calisma":
            o_anki_durum = "Kutulara Dogru Uzanma"
        else:
            o_anki_durum = "Bosta (Bekleme)"

    # 5. Süre
    if o_anki_durum in ctx.hand_state.hareket_sureleri:
        ctx.hand_state.hareket_sureleri[o_anki_durum] += kare_suresi

    # 6. Video süresi (sol üst)
    cv2.putText(kare,
                f"Video: {kare_sayaci * kare_suresi:.1f}s",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    # 7. HUD Paneli (Aşama 4)
    fsm_metrikleri = None
    fsm_recipe = []
    fsm_recipe_idx = 0
    if ctx.fsm_tracker is not None:
        tracker = ctx.fsm_tracker
        fsm_metrikleri = tracker.get_metrics()
        fsm_recipe = getattr(tracker, "recipe", [])
        fsm_recipe_idx = getattr(tracker, "current_recipe_idx", 0)

        # Event tracking for Phase 6
        yeni_durum = tracker.state
        if ctx.fsm_eski_durum == "GRASP" and yeni_durum == "MOVE":
            ctx.fsm_events.append({"type": "GRASP", "timestamp": round(kare_sayaci * kare_suresi, 3)})
        elif ctx.fsm_eski_durum == "PLACE" and (yeni_durum == "REACH" or yeni_durum == "RETURNING_HOME" or yeni_durum == "IDLE"):
            ctx.fsm_events.append({"type": "PLACE", "timestamp": round(kare_sayaci * kare_suresi, 3)})
        ctx.fsm_eski_durum = yeni_durum

    hud_ciz(
        kare,
        o_anki_durum,
        fsm_metrikleri,
        ctx.ergo_state.son_sol_aci,
        ctx.ergo_state.son_sag_aci,
        ctx.ergo_state.son_govde_acisi,
        fsm_recipe,
        fsm_recipe_idx
    )

    return kare


# ── Rapor Kaydetme ────────────────────────────────────────────────────────────

def _xlsx_raporu_yaz(video_adi, alan_sureleri, hareket_sureleri, fsm_tracker, dirsek_acisi_gecmisi, govde_acisi_gecmisi):
    """openpyxl ile renkli, biçimlendirilmiş Excel (.xlsx) raporu oluşturur."""
    if not XLSX_HAZIR:
        return

    wb = openpyxl.Workbook()

    # ── Sayfa 1: Özet ──────────────────────────────────────────────────────────
    ws = wb.active
    ws.title = "Özet"

    baslik_doldur = PatternFill("solid", fgColor="1E3A5F")
    baslik_font   = Font(bold=True, color="FFFFFF", size=11)
    ust_baslik_doldur = PatternFill("solid", fgColor="2E86AB")
    ust_baslik_font   = Font(bold=True, color="FFFFFF", size=12)
    kenarlık = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    yesil = PatternFill("solid", fgColor="C8E6C9")
    sari  = PatternFill("solid", fgColor="FFF9C4")
    kirmizi = PatternFill("solid", fgColor="FFCDD2")

    def baslik_satir(ws, satir, metin, genis=4):
        ws.merge_cells(start_row=satir, start_column=1,
                       end_row=satir, end_column=genis)
        h = ws.cell(satir, 1, metin)
        h.fill = ust_baslik_doldur
        h.font = ust_baslik_font
        h.alignment = Alignment(horizontal="center")

    def ust_baslik(ws, satir, sutunlar):
        for c, metin in enumerate(sutunlar, 1):
            cell = ws.cell(satir, c, metin)
            cell.fill = baslik_doldur
            cell.font = baslik_font
            cell.alignment = Alignment(horizontal="center")
            cell.border = kenarlık

    satir = 1
    ws.cell(satir, 1, f"Video: {video_adi}").font = Font(bold=True, size=13)
    satir += 2

    # Hareket Analizi
    baslik_satir(ws, satir, "HAREKET ANALİZİ")
    satir += 1
    ust_baslik(ws, satir, ["Hareket", "Süre (sn)", "Süre (TMU)", "Oran (%)"])
    satir += 1
    toplam_sure = sum(hareket_sureleri.values()) or 1
    for hareket, sure in hareket_sureleri.items():
        tmu = sure * 27.8
        oran = 100 * sure / toplam_sure
        for c, val in enumerate([hareket, f"{sure:.2f}", f"{tmu:.0f}", f"{oran:.1f}%"], 1):
            cell = ws.cell(satir, c, val)
            cell.border = kenarlık
            cell.alignment = Alignment(horizontal="center" if c > 1 else "left")
        satir += 1

    satir += 1
    # Bölge / Alan Analizi
    baslik_satir(ws, satir, "BÖLGE / ALAN ANALİZİ")
    satir += 1
    ust_baslik(ws, satir, ["Alan Adı", "Süre (sn)", "", ""])
    satir += 1
    for alan, sure in alan_sureleri.items():
        for c, val in enumerate([alan, f"{sure:.2f}", "", ""], 1):
            cell = ws.cell(satir, c, val)
            cell.border = kenarlık
        satir += 1

    satir += 1
    # Dirsek Açısı Analizi
    if dirsek_acisi_gecmisi:
        baslik_satir(ws, satir, "DİRSEK AÇI ANALİZİ (Ergonomi)")
        satir += 1
        ust_baslik(ws, satir, ["Kol", "Ort Açı (°)", "Maks Açı (°)", "Yüksek Risk (%)", "Not"])
        satir += 1
        for taraf, aciler_tuples in dirsek_acisi_gecmisi.items():
            if not aciler_tuples:
                continue
            aciler = [a[0] for a in aciler_tuples]
            interpolated = any(not a[1] for a in aciler_tuples)
            ort  = float(np.mean(aciler))
            maks = float(np.max(aciler))
            risk = 100.0 * sum(1 for a in aciler if a >= 150) / len(aciler)
            not_str = "Tahmini (Interpolated)" if interpolated else "Gerçek Zamanlı"
            for c, val in enumerate([taraf.capitalize(), f"{ort:.1f}", f"{maks:.1f}", f"{risk:.1f}%", not_str], 1):
                cell = ws.cell(satir, c, val)
                cell.border = kenarlık
                cell.alignment = Alignment(horizontal="center" if c > 1 else "left")
            # Renk kodlama
            if maks >= 150:
                ws.cell(satir, 3).fill = kirmizi
            elif maks >= 120:
                ws.cell(satir, 3).fill = sari
            else:
                ws.cell(satir, 3).fill = yesil
            satir += 1

    if govde_acisi_gecmisi:
        baslik_satir(ws, satir, "GÖVDE AÇI ANALİZİ (Ergonomi)")
        satir += 1
        ust_baslik(ws, satir, ["Bölge", "Ort Açı (°)", "Maks Açı (°)", "Yüksek Risk (%)", "Not"])
        satir += 1
        
        aciler = [a[0] for a in govde_acisi_gecmisi]
        if aciler:
            interpolated = any(not a[1] for a in govde_acisi_gecmisi)
            ort  = float(np.mean(aciler))
            maks = float(np.max(aciler))
            risk = 100.0 * sum(1 for a in aciler if a >= 60) / len(aciler)
            not_str = "Tahmini (Interpolated)" if interpolated else "Gerçek Zamanlı"
            
            for c, val in enumerate(["Gövde", f"{ort:.1f}", f"{maks:.1f}", f"{risk:.1f}%", not_str], 1):
                cell = ws.cell(satir, c, val)
                cell.border = kenarlık
                cell.alignment = Alignment(horizontal="center" if c > 1 else "left")
            
            if maks >= 60:
                ws.cell(satir, 3).fill = kirmizi
            elif maks >= 45:
                ws.cell(satir, 3).fill = sari
            else:
                ws.cell(satir, 3).fill = yesil
            satir += 1

    # Sütun genişlikleri
    ws.column_dimensions['A'].width = 32
    for col in ['B', 'C', 'D']:
        ws.column_dimensions[col].width = 16

    # ── Sayfa 2: FSM Çevrimler ─────────────────────────────────────────────────
    if fsm_tracker is not None and getattr(fsm_tracker, "reported_cycles", None):
        ws2 = wb.create_sheet("FSM Çevrimler")
        ust_baslik(ws2, 1, ["Çevrim No", "İstasyon", "Durum Geçişleri",
                             "Süre (sn)", "TMU", "Sıra Doğru?"])
        for c in ['A', 'B', 'C', 'D', 'E', 'F']:
            ws2.column_dimensions[c].width = 18
        for r, cyc in enumerate(fsm_tracker.reported_cycles, 2):
            degerler = [
                cyc["cycle_no"], cyc["station"], cyc["state_sequence"],
                cyc["duration_sec"], cyc["tmu"],
                "✓ Evet" if cyc["sequence_ok"] else "✗ Hayır"
            ]
            for c, val in enumerate(degerler, 1):
                cell = ws2.cell(r, c, val)
                cell.border = kenarlık
                cell.alignment = Alignment(horizontal="center")
            # Sıra hatası → kırmızı satır
            if not cyc["sequence_ok"]:
                for c in range(1, 7):
                    ws2.cell(r, c).fill = kirmizi

    dosya_adi = f"{video_adi}_rapor.xlsx"
    wb.save(dosya_adi)
    print(f"[RAPOR] Excel kaydedildi: {dosya_adi}")


def excel_raporu_kaydet(video_adi, alan_sureleri, hareket_sureleri,
                        fsm_tracker=None, dirsek_acisi_gecmisi=None, govde_acisi_gecmisi=None):
    """CSV + XLSX (eğer openpyxl yüklüyse) raporları oluşturur."""

    # ── CSV (her zaman) ────────────────────────────────────────────────────────
    dosya_adi = f"{video_adi}_ergonomi_raporu.csv"
    with open(dosya_adi, mode='w', newline='', encoding='utf-8-sig') as f:
        yazici = csv.writer(f, delimiter=';')
        yazici.writerow(["Analiz Tipi", "Islem / Bölge Adı", "Süre / Değer"])

        yazici.writerow(["HAREKET ANALIZI", "", ""])
        for hareket, sure in hareket_sureleri.items():
            yazici.writerow(["", hareket, f"{sure:.2f}"])

        yazici.writerow(["BÖLGE/ALAN ANALIZI", "", ""])
        for alan, sure in alan_sureleri.items():
            yazici.writerow(["", alan, f"{sure:.2f}"])

        if dirsek_acisi_gecmisi:
            yazici.writerow(["DİRSEK AÇI ANALİZİ (Ergonomi)", "", ""])
            for taraf, aciler_tuples in dirsek_acisi_gecmisi.items():
                if aciler_tuples:
                    aciler = [a[0] for a in aciler_tuples]
                    interpolated = any(not a[1] for a in aciler_tuples)
                    ort  = np.mean(aciler)
                    maks = np.max(aciler)
                    risk = 100.0 * sum(1 for a in aciler if a >= 150) / len(aciler)
                    yazici.writerow(["", f"{taraf.capitalize()} dirsek - Ort (°)",  f"{ort:.1f}"])
                    yazici.writerow(["", f"{taraf.capitalize()} dirsek - Maks (°)", f"{maks:.1f}"])
                    yazici.writerow(["", f"{taraf.capitalize()} dirsek - Risk (%)", f"{risk:.1f}"])
                    if interpolated:
                        yazici.writerow(["", f"{taraf.capitalize()} dirsek - Veri Kaynağı", "Tahmini (Interpolated)"])

        if govde_acisi_gecmisi:
            yazici.writerow(["GÖVDE AÇI ANALİZİ (Ergonomi)", "", ""])
            aciler = [a[0] for a in govde_acisi_gecmisi]
            if aciler:
                interpolated = any(not a[1] for a in govde_acisi_gecmisi)
                ort  = np.mean(aciler)
                maks = np.max(aciler)
                risk = 100.0 * sum(1 for a in aciler if a >= 60) / len(aciler)
                yazici.writerow(["", "Gövde - Ort (°)",  f"{ort:.1f}"])
                yazici.writerow(["", "Gövde - Maks (°)", f"{maks:.1f}"])
                yazici.writerow(["", "Gövde - Risk (%)", f"{risk:.1f}"])
                if interpolated:
                    yazici.writerow(["", "Gövde - Veri Kaynağı", "Tahmini (Interpolated)"])

    # FSM çevrim CSV
    if fsm_tracker is not None and getattr(fsm_tracker, "reported_cycles", None):
        fsm_csv = f"{video_adi}_fsm_raporu.csv"
        with open(fsm_csv, mode='w', newline='', encoding='utf-8-sig') as f:
            yazici = csv.writer(f, delimiter=';')
            yazici.writerow(["Cevrim No", "Istasyon", "Durum Gecisleri",
                             "Sure (sn)", "TMU", "Sira Dogru Mu"])
            for c in fsm_tracker.reported_cycles:
                yazici.writerow([
                    c["cycle_no"], c["station"], c["state_sequence"],
                    c["duration_sec"], c["tmu"], c["sequence_ok"]
                ])

    # ── XLSX (openpyxl varsa) ──────────────────────────────────────────────────
    if XLSX_HAZIR:
        try:
            _xlsx_raporu_yaz(video_adi, alan_sureleri, hareket_sureleri, fsm_tracker, dirsek_acisi_gecmisi, govde_acisi_gecmisi)
        except Exception as e:
            print(f"[UYARI] Excel (.xlsx) dosyası yazılamadı: {e}")