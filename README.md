# Endüstriyel Ergonomi ve Alan Tanımlama Paneli (Video Pipeline)

Bu proje, fabrika montaj hatları ve endüstriyel iş istasyonlarındaki operatör hareketlerini analiz etmek için geliştirilmiş yapay zeka destekli bir bilgisayarlı görü ve ergonomi analiz yazılımıdır. 

**MOST (Maynard Operation Sequence Technique)** altyapısına dayanarak otonom zaman etüdü yapar ve operatörlerin dirsek açılarını takip ederek ergonomik risk raporları çıkarır.

---

## 🚀 Özellikler

1. **Çift El Takibi ve Alan Analizi (MediaPipe Hands):**
   - Videodaki operatörün ellerini gerçek zamanlı takip eder.
   - Tanımlanan poligonal alanlar ("Alet Alanı", "Çalışma Alanı") içindeki el hareketlerini saniye bazında ölçer.
   
2. **Otonom Zaman Etüdü ve FSM (Durum Makinesi):**
   - MOST altyapısına dayalı bir FSM (`MOSTTracker`) içerir.
   - Uzanma (REACH), Kavrama (GRASP), Taşıma (MOVE), Yerleştirme (PLACE) ve Boşta Bekleme (IDLE) durumlarını parmakların Pinch (Kavrama) oranlarına ve hızlarına bakarak otomatik tespit eder.
   - Döngüleri ve TMU (Time Measurement Unit) değerlerini hesaplar.
   - Yanlış kutuya uzanma gibi hatalı sekansları ("Sıra Hatası") anında tespit eder.

3. **Ergonomik Risk Analizi (MediaPipe Pose):**
   - Operatörün sağ ve sol dirsek açılarını hesaplar.
   - Açısal risk durumlarını "Trafik Işığı" (Yeşil, Sarı, Kırmızı) renk kodlarıyla canlı olarak video üzerinde (HUD) gösterir. (Örn: >150° Yüksek Risk, 120°-150° Orta Risk).

4. **Kapsamlı Raporlama:**
   - Analiz bitiminde hem `.csv` hem de `.xlsx` formatında renk kodlu, detaylı Excel raporları üretir.
   - Raporlar; hareket süreleri, alan bazlı harcanan süre, dirsek açısı risk analizleri ve FSM çevrim adımlarını içerir.

---

## 📂 Proje Yapısı

* `alan_tanim2.py`: Tkinter tabanlı ana kullanıcı arayüzü dosyası. Video yükleme, poligon alan çizimi ve analiz kontrolü buradan yapılır.
* `el_takip_analizi.py`: MediaPipe (Pose & Hands) modellerinin çalıştırıldığı, açı/zaman hesaplamalarının yapıldığı ve gelişmiş HUD panelinin (yarı saydam grafikler) çizildiği ana analiz motorudur.
* `fsm.py`: Otonom MOST durum makinesi. Ellerin koordinatları ve parmak arası mesafelerini alarak REACH, GRASP vb. eylemlere karar verir.
* `Calistir.bat`: Uygulamayı hızlıca konsol olmadan başlatmaya yarayan toplu iş dosyası.

---

## 🛠️ Kurulum ve Çalıştırma

### Gereksinimler
Uygulamanın çalışması için aşağıdaki Python kütüphaneleri yüklü olmalıdır:
```bash
pip install opencv-python mediapipe numpy openpyxl
```
*(Not: `tkinter` ve `csv` standart Python kütüphaneleridir).*

### Nasıl Çalıştırılır?
1. Klasör içerisindeki **`Calistir.bat`** dosyasına çift tıklayarak uygulamayı başlatabilirsiniz.
2. Alternatif olarak terminal/komut satırından:
   ```bash
   python alan_tanim2.py
   ```
   komutu ile arayüzü açabilirsiniz.

### Kullanım Adımları
1. **Video Seçimi:** Arayüz açıldığında sol taraftan "Video Dosyası Yükle" diyerek analiz edilecek endüstriyel videoyu seçin.
2. **Alan Tanımlama:**
   - Montaj masası için alan adını yazıp **"🟢 Çalışma Alanı Tanımla"**ya tıklayın. Videoda fare ile çokgen (poligon) çizip **ENTER** ile kapatın.
   - Vida/Malzeme kutuları için alan adını yazıp **"🔵 Alet Alanı Tanımla"**ya tıklayın ve ilgili alanı çizin. *(Kutuları, operatörün alma sırasına göre tanımlamanız FSM'in doğru çalışmasını sağlar).*
3. **Analizi Başlat:** **"▶️ Videoyu Başlat ve Analiz Et"** butonuna basarak yapay zeka sürecini başlatın.
4. **Sonuçlar:** Video oynarken anlık durumlar sol alttaki HUD'da gösterilir. Video bittiğinde Excel raporları otomatik oluşturulur.
