from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class HandTrackingState:
    alan_sureleri: Dict[str, float] = field(default_factory=dict)
    alan_kare_sayaclari: Dict[str, int] = field(default_factory=dict)
    hareket_sureleri: Dict[str, float] = field(default_factory=lambda: {
        "Kutulara Dogru Uzanma": 0.0,
        "Malzeme Tasıma (Masaya Dogru)": 0.0,
        "Malzeme Alma / Kavrama": 0.0,
        "Montaj / Calısma": 0.0,
        "Bosta (Bekleme)": 0.0
    })
    son_bilinen_konum: str = "Bosta"

@dataclass
class ErgonomicsState:
    dirsek_acisi_gecmisi_sol: List[tuple] = field(default_factory=list)
    dirsek_acisi_gecmisi_sag: List[tuple] = field(default_factory=list)
    govde_acisi_gecmisi: List[tuple] = field(default_factory=list)
    son_sol_aci: Optional[float] = None
    son_sag_aci: Optional[float] = None
    son_govde_acisi: Optional[float] = None
    is_pose_fresh: bool = False

@dataclass
class CycleTracker:
    """Çevrim süresi ve ürün sayısı takibini yapar.
    Döngü mantığı: Yeşil alandan çıkış → Bitiş alanına giriş (≥0.4s) = 1 ürün.
    """
    # Bayraklar
    ilk_yesil_giris_yapildi: bool = False
    yesil_alanda: bool = False
    bitis_alaninda: bool = False
    bu_giriste_sayildi: bool = False          # Aynı girişte tekrar sayım engeli
    son_bitis_sonrasi_yesile_gidildi: bool = False  # Yeşilsiz çift bitiş koruması

    # Zamanlama
    dongu_baslangic_zamani: float = 0.0
    bitis_giris_zamani: float = 0.0

    # Kayıtlar
    dongu_sureleri: List[float] = field(default_factory=list)
    atlanan_dongu_sureleri: List[float] = field(default_factory=list)  # Aykırı değerler
    urun_sayisi: int = 0

    # Parametreler
    bitis_debounce_sure: float = 0.4   # Bitiş alanında min kalış süresi (sn)
    max_dongu_sure: float = 120.0      # Aykırı değer üst sınırı — ileride arayüzden ayarlanabilir

    @property
    def cevrim_suresi(self) -> float:
        """Ortalama çevrim süresi (Lean: Cycle Time). Takt Time değil."""
        return sum(self.dongu_sureleri) / len(self.dongu_sureleri) \
               if self.dongu_sureleri else 0.0

    @property
    def standart_sapma(self):
        """Örneklem std (n-1). n<2 ise None döner → HUD/Excel'de 'N/A' gösterilir."""
        n = len(self.dongu_sureleri)
        if n < 2:
            return None
        ort = self.cevrim_suresi
        return (sum((x - ort)**2 for x in self.dongu_sureleri) / (n - 1)) ** 0.5

    def reset(self):
        """Video yeniden başlatıldığında veya analiz sıfırlandığında çağrılır."""
        self.ilk_yesil_giris_yapildi = False
        self.yesil_alanda = False
        self.bitis_alaninda = False
        self.bu_giriste_sayildi = False
        self.son_bitis_sonrasi_yesile_gidildi = False
        self.dongu_baslangic_zamani = 0.0
        self.bitis_giris_zamani = 0.0
        self.dongu_sureleri = []
        self.atlanan_dongu_sureleri = []
        self.urun_sayisi = 0

@dataclass
class AnalysisContext:
    hand_state: HandTrackingState = field(default_factory=HandTrackingState)
    ergo_state: ErgonomicsState = field(default_factory=ErgonomicsState)
    cycle_tracker: CycleTracker = field(default_factory=CycleTracker)
    fsm_tracker: Any = None
    fsm_events: List[dict] = field(default_factory=list)
    fsm_eski_durum: str = "IDLE"
    kare_sayaci: int = 0

    def init_alanlar(self, alanlar: dict):
        """Video baslamadan once tanimli alanlara gore sozlukleri hazirlar."""
        for alan in alanlar:
            self.hand_state.alan_sureleri.setdefault(alan, 0.0)
            self.hand_state.alan_kare_sayaclari.setdefault(alan, 0)
