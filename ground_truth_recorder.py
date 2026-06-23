import cv2
import json
import argparse
import os

def record_ground_truth(video_path):
    if not os.path.exists(video_path):
        print(f"Hata: Video bulunamadi: {video_path}")
        return

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        fps = 30.0

    events = []
    paused = False

    window_name = "Ground Truth Recorder - SPACE: Duraklat, G: Grasp, P: Place, Q/ESC: Cikis"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    print("--- GROUND TRUTH RECORDER ---")
    print("G tuşu: GRASP (Kavrama) anını kaydeder.")
    print("P tuşu: PLACE (Bırakma) anını kaydeder.")
    print("SPACE tuşu: Videoyu duraklatır/devam ettirir.")
    print("A veya SOL OK: 5 kare geri git (ince ayar için).")
    print("D veya SAĞ OK: 5 kare ileri git.")
    print("Q veya ESC: Kaydedip çıkar.")

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print("Videonun sonuna gelindi.")
                break
        else:
            # Duraklatılmışsa mevcut kareyi tekrar oku (geri ileri sardıysak diye)
            current_frame_idx = cap.get(cv2.CAP_PROP_POS_FRAMES)
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_idx - 1)
            ret, frame = cap.read()
            if not ret:
                break
        
        current_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
        current_time = current_frame / fps

        display_frame = frame.copy()
        
        # HUD bilgisi
        durum_metni = "DURAKLATILDI" if paused else "OYNATILIYOR"
        cv2.putText(display_frame, f"{durum_metni} | Zaman: {current_time:.2f}s", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Son eklenen eventleri goster
        y_pos = 60
        for evt in events[-5:]:
            renk = (0, 255, 255) if evt['type'] == 'GRASP' else (255, 100, 100)
            cv2.putText(display_frame, f"{evt['type']} @ {evt['timestamp']:.2f}s", (10, y_pos), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, renk, 2)
            y_pos += 25

        cv2.imshow(window_name, display_frame)

        wait_time = 30 if not paused else 100
        key = cv2.waitKey(wait_time) & 0xFF

        if key == ord('q') or key == 27: # Q veya ESC
            break
        elif key == 32: # SPACE
            paused = not paused
        elif key == ord('g'):
            events.append({"type": "GRASP", "timestamp": round(current_time, 3)})
            print(f"[KAYIT] GRASP: {current_time:.3f}s")
        elif key == ord('p'):
            events.append({"type": "PLACE", "timestamp": round(current_time, 3)})
            print(f"[KAYIT] PLACE: {current_time:.3f}s")
        elif key == ord('a'): # Geri sar
            paused = True
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, current_frame - 5))
        elif key == ord('d'): # İleri sar
            paused = True
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame + 5)

    cap.release()
    cv2.destroyAllWindows()

    if not events:
        print("Hicbir olay kaydedilmedi, dosya olusturulmuyor.")
        return

    condition = input("Bu videonun kosulunu girin (ornek: iyi_isik, occlusion_var, hizli_hareket vb.): ").strip()
    if not condition:
        condition = "belirtilmedi"

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    out_file = f"{base_name}_ground_truth.json"

    data = {
        "video_path": video_path,
        "condition": condition,
        "events": events
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print(f"\nBitti! Veriler '{out_file}' dosyasina kaydedildi.")
    print(f"Toplam GRASP: {sum(1 for e in events if e['type'] == 'GRASP')}")
    print(f"Toplam PLACE: {sum(1 for e in events if e['type'] == 'PLACE')}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str, required=True, help="Analiz edilecek video dosyasi")
    args = parser.parse_args()
    record_ground_truth(args.video)
