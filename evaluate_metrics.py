import json
import argparse
import os
import numpy as np

def match_events(gt_events, fsm_events, tolerance):
    """
    Greedy nearest-match algoritması.
    Tolerans penceresi içindeki en yakın FSM eventini GT eventi ile eşleştirir.
    Döner: matched (list of tuples), fp (list), fn (list)
    """
    matched = []
    
    # Kullanılmış FSM eventlerini takip et
    fsm_used = set()
    fn = []

    for gt in gt_events:
        gt_time = gt['timestamp']
        best_match_idx = -1
        best_diff = float('inf')
        
        for idx, fsm in enumerate(fsm_events):
            if idx in fsm_used:
                continue
            
            fsm_time = fsm['timestamp']
            diff = abs(fsm_time - gt_time)
            
            if diff <= tolerance and diff < best_diff:
                best_diff = diff
                best_match_idx = idx
                
        if best_match_idx != -1:
            fsm_used.add(best_match_idx)
            matched.append({
                "gt_time": gt_time,
                "fsm_time": fsm_events[best_match_idx]['timestamp'],
                "diff": fsm_events[best_match_idx]['timestamp'] - gt_time
            })
        else:
            fn.append(gt)
            
    fp = [fsm_events[i] for i in range(len(fsm_events)) if i not in fsm_used]
    return matched, fp, fn

def evaluate(gt_file, fsm_file, tolerance):
    if not os.path.exists(gt_file):
        print(f"HATA: Ground Truth dosyasi bulunamadi: {gt_file}")
        return
    if not os.path.exists(fsm_file):
        print(f"HATA: FSM Events dosyasi bulunamadi: {fsm_file}")
        return

    with open(gt_file, "r", encoding="utf-8") as f:
        gt_data = json.load(f)
    with open(fsm_file, "r", encoding="utf-8") as f:
        fsm_data = json.load(f)

    condition = gt_data.get("condition", "belirtilmedi")
    gt_events = gt_data.get("events", [])
    
    # Gruplama
    types = ["GRASP", "PLACE"]
    
    print("=" * 60)
    print(f"METRİK DEĞERLENDİRME RAPORU")
    print(f"Video Koşulu: {condition}")
    print(f"Tolerans: ±{tolerance} sn")
    print("=" * 60)

    for ev_type in types:
        gt_type = [e for e in gt_events if e['type'] == ev_type]
        fsm_type = [e for e in fsm_data if e['type'] == ev_type]
        
        matched, fp, fn = match_events(gt_type, fsm_type, tolerance)
        
        tp_count = len(matched)
        fp_count = len(fp)
        fn_count = len(fn)
        
        # Precision, Recall, F1
        precision = tp_count / (tp_count + fp_count) if (tp_count + fp_count) > 0 else 0.0
        recall = tp_count / (tp_count + fn_count) if (tp_count + fn_count) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        # Zamanlama Hatası (MAE - Mean Absolute Error)
        if matched:
            mae = float(np.mean([abs(m['diff']) for m in matched]))
            avg_bias = float(np.mean([m['diff'] for m in matched])) # Pozitifse gecikmeli, negatifse erken tespit
        else:
            mae = 0.0
            avg_bias = 0.0
            
        print(f"\n--- {ev_type} ANALİZİ ---")
        print(f"Gerçek (Ground Truth) Sayısı : {len(gt_type)}")
        print(f"FSM Tespit Sayısı          : {len(fsm_type)}")
        print(f"Doğru Eşleşme (True Pos.)  : {tp_count}")
        print(f"Kaçırılan (False Neg.)     : {fn_count}")
        print(f"Yanlış Alarm (False Pos.)  : {fp_count}")
        print("-" * 30)
        print(f"Zamanlama MAE (Mutlak Hata): {mae:.3f} sn")
        print(f"Zamanlama Eğilimi (Bias)   : {avg_bias:+.3f} sn " + ("(Gecikmeli)" if avg_bias > 0 else "(Erken)"))
        print("-" * 30)
        print(f"Precision (Kesinlik)       : {precision:.2%}")
        print(f"Recall (Duyarlılık)        : {recall:.2%}")
        print(f"F1-Score                   : {f1:.2%}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gt", type=str, required=True, help="Ground truth JSON dosyasi")
    parser.add_argument("--fsm", type=str, required=True, help="FSM events JSON dosyasi")
    parser.add_argument("--tolerance", type=float, default=0.3, help="Saniye cinsinden eslestirme toleransi")
    args = parser.parse_args()
    
    evaluate(args.gt, args.fsm, args.tolerance)
