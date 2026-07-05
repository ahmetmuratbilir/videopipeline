# config_manager.py
import json
import os
import tempfile
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
HISTORY_LOG_PATH = os.path.join(BASE_DIR, "config_history.log")

CONFIG_DEFAULTS = {
    "EL_KAYIP_SURE": 0.25,
    "EL_GRACE_SURE": 1.5,
    "EL_CONFIDENCE_ESIGI": 0.65,
    "ERGO_RISK_YUKSEK": 150.0,
    "ERGO_RISK_DIKKAT": 120.0,
    "GOVDE_RISK_YUKSEK": 60.0,
    "GOVDE_RISK_DIKKAT": 45.0,
    "FLASH_KARE_SAYISI": 12,
    "HUD_SERIT_GENISLIK": 230,
    "GEMINI_MODEL_NAME": "gemini-2.5-flash",
    "version": 1,
    "last_modified_by": "System"
}

CONFIG_TYPES = {
    "EL_KAYIP_SURE": float,
    "EL_GRACE_SURE": float,
    "EL_CONFIDENCE_ESIGI": float,
    "ERGO_RISK_YUKSEK": float,
    "ERGO_RISK_DIKKAT": float,
    "GOVDE_RISK_YUKSEK": float,
    "GOVDE_RISK_DIKKAT": float,
    "FLASH_KARE_SAYISI": int,
    "HUD_SERIT_GENISLIK": int,
    "GEMINI_MODEL_NAME": str
}

def _read_raw_config():
    """Dosyayı doğrudan JSON olarak okur, şema tamamlama yapmaz (Sonsuz Döngü Engeli)."""
    if not os.path.exists(CONFIG_PATH):
        return CONFIG_DEFAULTS.copy()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return CONFIG_DEFAULTS.copy()

def load_config():
    """Parametreleri config.json'dan yükler. Şema eksiği varsa otomatik tamamlar."""
    if not os.path.exists(CONFIG_PATH):
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile('w', dir=BASE_DIR, delete=False, encoding='utf-8') as tf:
                json.dump(CONFIG_DEFAULTS, tf, indent=4)
                temp_name = tf.name
            os.replace(temp_name, CONFIG_PATH)
        except Exception as e:
            print(f"[CONFIG HATA] Varsayılan dosya oluşturulamadı: {e}")
            if temp_name and os.path.exists(temp_name):
                try:
                    os.remove(temp_name)
                except Exception:
                    pass
            return CONFIG_DEFAULTS.copy()
        return CONFIG_DEFAULTS.copy()
    
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            
            # Şema tamamlama (migration) kontrolü için ham halini kopyala
            raw_disk_data = data.copy()
            updated = False
            for k, v in CONFIG_DEFAULTS.items():
                if k not in data:
                    data[k] = v
                    updated = True
            
            if updated:
                save_and_log_config(data, "System", "Eksik parametreler tamamlandi.", old_config=raw_disk_data)
            return data
    except Exception as e:
        print(f"[CONFIG HATA] Okuma hatası, varsayılanlar yükleniyor: {e}")
        return CONFIG_DEFAULTS.copy()

def save_and_log_config(new_config, user_name, reason, old_config=None) -> bool:
    """Tip doğrulaması ve atomik yazma ile parametreleri günceller."""
    if old_config is None:
        old_config = _read_raw_config()
        
    changes = []
    
    # Tip Doğrulaması
    for key, expected_type in CONFIG_TYPES.items():
        if key not in new_config:
            print(f"[KALİBRASYON RED] Hata: '{key}' parametresi eksik.")
            return False
        
        val = new_config[key]
        if expected_type == float and isinstance(val, int):
            val = float(val)
            new_config[key] = val
            
        if not isinstance(val, expected_type):
            print(f"[KALİBRASYON RED] Hata: '{key}' tipi geçersiz. Beklenen: {expected_type.__name__}")
            return False
            
        if old_config.get(key) != val:
            changes.append(f"{key}: {old_config.get(key)} -> {val}")
            
    if changes:
        try:
            new_config["version"] = int(old_config.get("version", 1)) + 1
        except (ValueError, TypeError):
            new_config["version"] = 1
            
        new_config["last_modified_by"] = user_name
        
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile('w', dir=BASE_DIR, delete=False, encoding='utf-8') as tf:
                json.dump(new_config, tf, indent=4)
                temp_name = tf.name
            os.replace(temp_name, CONFIG_PATH)
            
            log_entry = (
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                f"Versiyon: {new_config['version']} | Değiştiren: {user_name} | "
                f"Gerekçe: {reason} | Değişiklikler: {', '.join(changes)}\n"
            )
            with open(HISTORY_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(log_entry)
            print(f"[KALİBRASYON LOGU] Kaydedildi: {log_entry.strip()}")
            return True
        except Exception as e:
            print(f"[CONFIG HATA] Kaydetme hatası: {e}")
            if temp_name and os.path.exists(temp_name):
                try:
                    os.remove(temp_name)
                except Exception:
                    pass
            return False
    return True

# Merkezi tek yükleme
config = load_config()
GEMINI_MODEL_NAME = config.get("GEMINI_MODEL_NAME", "gemini-2.5-flash")
