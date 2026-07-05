# Endüstriyel Ergonomi, Zaman Etüdü ve Alan Analiz Paneli (Video Pipeline)

Bu proje; fabrika montaj hatları ve endüstriyel iş istasyonlarındaki operatör hareketlerini analiz etmek amacıyla geliştirilmiş yapay zeka destekli, otonom bir bilgisayarlı görü ve ergonomi analiz yazılımıdır.

**MOST (Maynard Operation Sequence Technique)** altyapısına dayanarak otonom zaman etüdü yapar, çevrim sürelerini (Cycle Time) çıkarır ve operatörlerin duruş ve dirsek açılarını takip ederek ergonomik risk analizleri üretir.

---

## 🚀 Öne Çıkan Özellikler

### 1. El Takibi & Grace Period Stabilitesi
- **Grace Period (1.5 Saniye):** Elin anlık olarak kadrajdan çıkması veya kapanması durumunda veri ve durum makinesi (FSM) sıfırlanmaz, 1.5 saniye boyunca veriler dondurulur (Örn: ekranda dondurulmuş veriyi temsil eden `~142°` işareti gösterilir).
- **Konum Eşlemeli El Kimliği:** MediaPipe'ın sol/sağ el etiketlerini karıştırma hatası, bilek koordinatlarının Öklid mesafesini takip eden konum tabanlı bir algoritmayla çözülmüştür. Eller çapraz geçse bile kimlikler korunur.
- **Dirençli Başlangıç (Startup):** Video başlangıcında henüz hiç el algılanmadıysa kullanıcı arayüzü sessizce bekler, gereksiz "El Kaybı" uyarısı verilmez.

### 2. Yenilenen Dikey HUD Tasarımı (Tek Sağ Şerit)
- **Sağ Dikey Şerit (230px):** Ekranın altını kapatan paneller kaldırılmıştır. Tüm veriler sağ tarafta dikey, yarı saydam ve şık bir şeritte listelenir.
- **Aspect Ratio Koruması:** Video sol %80'e aspect-ratio (en-boy oranı) korunarak yerleştirilir. Arayüz boyutu ne olursa olsun HUD üzerindeki yazılar ve grafikler her zaman net ve okunabilir kalır.
- **Geçiş Animasyonları:** Bitiş alanına ulaşıldığında 12 kare boyunca yeşil dolgu (flash animasyonu) gösterilir. El kaybı anında üst ortada kırmızı geri sayım banner'ı tetiklenir.

### 3. Yapay Zekalı Mühendislik Analizi (Gemini 2.5 Flash)
- **Metin Tabanlı LLM Analizi:** Video analizi bittiğinde, FSM olay geçmişi ve sayısal veriler kullanılarak Gemini API ile otomatik Türkçe mühendislik yorum raporu (`video_ismi_TARIH_ai_analiz.txt`) oluşturulur.
- **Hata Toleransı (Graceful Degradation):** API anahtarının girilmemesi veya internet kesintilerinde program çökmez; sessizce hata mesajını raporlayarak normal yerel analizi tamamlar.

### 4. Modüler Parametre Yönetimi & Kalibrasyon Logu
- **`config.json`:** Tüm analiz parametreleri (grace süresi, confidence oranı, ergonomi risk sınırları) kod dışına taşınarak tek bir JSON dosyasında toplanmıştır.
- **`kalibrasyon_guncelle.py` (CLI):** Mühendislerin kalibrasyon testleri esnasında parametreleri terminalden güvenli ve tip-doğrulamalı olarak değiştirmesini sağlar.
- **`config_history.log`:** Yapılan her parametre değişikliği; değiştiren kişi, tarih ve gerekçe bilgileriyle versiyonlanarak bu dosyaya kaydedilir.

---

## 📂 Proje Yapısı

*   `alan_tanim2.py`: Tkinter tabanlı ana kullanıcı arayüzü dosyası. Video yükleme, poligon alan çizimi ve analiz kontrolü buradan yapılır.
*   `el_takip_analizi.py`: MediaPipe (Pose & Hands) modellerinin çalıştırıldığı, açı/zaman hesaplamalarının yapıldığı ve dikey HUD panelinin çizildiği ana analiz motorudur.
*   `config_manager.py`: `config.json` dosyasını okuyan, eksik şema değerlerini tamamlayan ve atomik dosya yazma işlemlerini yürüten konfigürasyon yöneticisidir.
*   `kalibrasyon_guncelle.py`: Parametre güncelleme ve versiyonlama işlemlerini yürüten interaktif komut satırı aracıdır.
*   `fsm.py`: Otonom MOST durum makinesi. Ellerin koordinatları ve parmak arası mesafelerini alarak eylemlere karar verir.
*   `state.py`: Analiz sürecinde verilerin (el durumu, ergonomi geçmişi, çevrim süreleri vb.) saklandığı durum veri modelidir.
*   `Calistir.bat`: Uygulamayı hızlıca konsol olmadan başlatmaya yarayan Windows toplu iş dosyası.

---

## 🛠️ Kurulum ve Çalıştırma

### Kütüphane Kurulumu
Uygulamanın çalışması için gerekli kütüphaneleri terminalinizden aşağıdaki komutla kurabilirsiniz:
```bash
pip install opencv-python mediapipe numpy openpyxl pillow google-generativeai
```

### Yapay Zeka Raporunu Aktifleştirmek (İsteğe Bağlı)
Çevrim sonunda otomatik yapay zeka raporu almak için, uygulamayı başlatmadan önce komut satırına kendi Gemini API anahtarınızı tanımlamalısınız:
```bash
set GEMINI_API_KEY=kendi_api_anahtariniz
```

### Nasıl Çalıştırılır?
1.  Klasör içerisindeki **`Calistir.bat`** dosyasına çift tıklayarak uygulamayı başlatabilirsiniz.
2.  Alternatif olarak terminal/komut satırından:
    ```bash
    python alan_tanim2.py
    ```
    komutu ile arayüzü açabilirsiniz.

---

## 📖 Kullanım Adımları

1.  **Video Seçimi:** Arayüz açıldığında sol taraftan "Video Dosyası Yükle" diyerek analiz edilecek endüstriyel videoyu seçin.
2.  **Alan Tanımlama (3-Bölge):**
    - Montaj masası için alan adını yazıp **"🟢 Çalışma Alanı Tanımla"** butonuna tıklayın. Açılan OpenCV penceresinde fare ile poligonu (çokgen) çizip **ENTER** tuşuna basarak kaydedin.
    - Vida/malzeme kutuları için alan adını yazıp **"🔴 Alet Alanı Tanımla"** butonuna tıklayın ve alanları çizin. (Operatörün alma sırasına göre tanımlamanız önerilir).
    - Bitmiş ürünlerin bırakılacağı yer için **"🔵 Bitiş Alanı Tanımla"** butonuna tıklayıp bitiş poligonunu çizin (Ürün sayımı için gereklidir).
3.  **Analizi Başlat:** **"▶️ Videoyu Başlat ve Analiz Et"** butonuna basarak yapay zeka sürecini başlatın.
4.  **Sonuçlar:** Video bittiğinde Excel (`.xlsx`), CSV (`.csv`) ve Yapay Zeka Raporu (`.txt`) çıktıları video ismiyle aynı dizine otomatik olarak kaydedilecektir.
