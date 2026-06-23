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
class AnalysisContext:
    hand_state: HandTrackingState = field(default_factory=HandTrackingState)
    ergo_state: ErgonomicsState = field(default_factory=ErgonomicsState)
    fsm_tracker: Any = None
    fsm_events: List[dict] = field(default_factory=list)
    fsm_eski_durum: str = "IDLE"
    kare_sayaci: int = 0

    def init_alanlar(self, alanlar: dict):
        """Video baslamadan once tanimli alanlara gore sozlukleri hazirlar."""
        for alan in alanlar:
            self.hand_state.alan_sureleri.setdefault(alan, 0.0)
            self.hand_state.alan_kare_sayaclari.setdefault(alan, 0)
