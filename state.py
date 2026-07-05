from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class HandTrackingState:
    alan_sureleri: Dict[str, float] = field(default_factory=dict)
    alan_kare_sayaclari: Dict[str, int] = field(default_factory=dict)
    hareket_sureleri: Dict[str, float] = field(default_factory=lambda: {
        "Kutulara Dogru Uzanma": 0.0,
        "Malzeme Tasimi (Masaya Dogru)": 0.0,
        "Malzeme Alma / Kavrama": 0.0,
        "Montaj / Calisma": 0.0,
        "Bosta (Bekleme)": 0.0,
        "El Kaybi": 0.0,
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
class ElDurumu:
    ilk_goruldu: bool = False
    aktif: bool = False
    grace_aktif: bool = False
    grace_baslangic_zamani: float = 0.0
    kayip_baslangic_zamani: float = 0.0
    dondurulmus: bool = False
    son_acisi: Optional[float] = None
    son_pozisyon: Optional[tuple] = None

    def reset(self):
        self.ilk_goruldu = False
        self.aktif = False
        self.grace_aktif = False
        self.grace_baslangic_zamani = 0.0
        self.kayip_baslangic_zamani = 0.0
        self.dondurulmus = False
        self.son_acisi = None
        self.son_pozisyon = None

@dataclass
class CycleTracker:
    ilk_yesil_giris_yapildi: bool = False
    yesil_alanda: bool = False
    bitis_alaninda: bool = False
    bu_giriste_sayildi: bool = False
    son_bitis_sonrasi_yesile_gidildi: bool = False
    dongu_baslangic_zamani: float = 0.0
    bitis_giris_zamani: float = 0.0
    dongu_sureleri: List[float] = field(default_factory=list)
    atlanan_dongu_sureleri: List[float] = field(default_factory=list)
    urun_sayisi: int = 0
    bitis_debounce_sure: float = 0.4
    max_dongu_sure: float = 120.0

    @property
    def cevrim_suresi(self) -> float:
        return sum(self.dongu_sureleri) / len(self.dongu_sureleri) if self.dongu_sureleri else 0.0

    @property
    def standart_sapma(self):
        n = len(self.dongu_sureleri)
        if n < 2:
            return None
        ort = self.cevrim_suresi
        return (sum((x - ort)**2 for x in self.dongu_sureleri) / (n - 1)) ** 0.5

    def reset(self):
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
    sol_el: ElDurumu = field(default_factory=ElDurumu)
    sag_el: ElDurumu = field(default_factory=ElDurumu)
    el_kayip_toplam_sure: float = 0.0
    el_kayip_olay_sayisi: int = 0
    flash_kare_sayaci: int = 0
    flash_alan_tipi: str = ""
    fsm_tracker: Any = None
    fsm_events: List[dict] = field(default_factory=list)
    fsm_eski_durum: str = "IDLE"
    kare_sayaci: int = 0

    def init_alanlar(self, alanlar: dict):
        for alan in alanlar:
            self.hand_state.alan_sureleri.setdefault(alan, 0.0)
            self.hand_state.alan_kare_sayaclari.setdefault(alan, 0)
