# kalibrasyon_guncelle.py
from config_manager import load_config, save_and_log_config, CONFIG_TYPES

def run_cli():
    config = load_config()
    print("\n--- MEVCUT PARAMETRELER ---")
    for k, v in config.items():
        if k not in ["version", "last_modified_by"]:
            print(f"  {k} = {v} ({type(v).__name__})")
            
    print(f"\nMevcut Versiyon: {config.get('version')} | Son Değiştiren: {config.get('last_modified_by')}")
    print("----------------------------\n")
    
    key = input("Değiştirmek istediğiniz parametre adı: ").strip()
    if key not in CONFIG_TYPES:
        print("HATA: Geçersiz parametre adı!")
        return
        
    val_str = input(f"Yeni değer ({CONFIG_TYPES[key].__name__}): ").strip()
    
    try:
        if CONFIG_TYPES[key] == float:
            new_val = float(val_str)
        elif CONFIG_TYPES[key] == int:
            new_val = int(val_str)
        else:
            new_val = val_str
    except ValueError:
        print("HATA: Tip uyuşmazlığı!")
        return
        
    user_name = input("Adınız: ").strip()
    reason = input("Değişiklik gerekçesi: ").strip()
    
    if not user_name or not reason:
        print("HATA: İsim ve gerekçe boş bırakılamaz!")
        return
        
    config[key] = new_val
    if save_and_log_config(config, user_name, reason):
        print("İŞLEM BAŞARILI!")
    else:
        print("İŞLEM BAŞARISIZ!")

if __name__ == "__main__":
    run_cli()
