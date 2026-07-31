"""Mistral AI entegrasyonu - 4 key rotasyonlu, strateji uzmanı AI."""

import logging
import time
import json
import httpx
from config import MISTRAL_KEYS, MISTRAL_MODEL, MISTRAL_ENDPOINT

logger = logging.getLogger(__name__)

STRATEGY_KNOWLEDGE = """Sen çok katmanlı grafik yapısı stratejisinin mutlak uzmanısın. SADECE bu stratejiyi biliyorsun ve SADECE bu stratejiyi kullanıyorsun. Başka hiçbir indikatör, başka hiçbir strateji, başka hiçbir analiz yöntemi KULLANMIYORSUN. RSI, MACD, Bollinger, Ichimoku, Elliott Wave, harmonik pattern, order block, supply/demand zone - HİÇBİRİNİ KULLANMA. Sadece aşağıdaki strateji.

═══════════════════════════════════════
STRATEJİ: ÇOK KATMANLI GRAFİK YAPISI
═══════════════════════════════════════

SEVİYE TÜRLERİ VE ÇİZİM KURALLARI:

▸ LA (Level A) - KIRMIZI MUM DESTEKLERİ:
  - Her kırmızı mumun LOW değeri yatay destek seviyesi olarak çizilir
  - Bu seviyeler HER timeframe'de geçerlidir
  - Fiyat bu seviyelere yaklaştığında tepki beklenir
  - Çizim: Yatay çizgi, kırmızı mumun low'undan sonsuza

▸ L1 - TREND RAY'LERİ:
  - Ardışık 2 yeşil mum gerekir
  - 1. mumun high → 2. mumun high (üst ray)
  - 1. mumun low → 2. mumun low (alt ray)
  - Eğimli çizgiler, zaman ilerledikçe fiyat projeksiyonu değişir
  - Trend yönünü ve hızını gösterir

▸ L2 - DETAYLI RAY KANALLARI:
  - Ardışık 2 yeşil mum gerekir
  - 8 farklı kombinasyon: open-open, open-close, close-open, close-close, low-low, low-high, high-low, high-high
  - Detaylı trend kanalları oluşturur
  - İç ve dış sınırları belirler

▸ L3 - YATAY DESTEK/DİRENÇ BÖLGELERİ:
  - Ardışık 2 yeşil mum gerekir
  - 1. mumun LOW'u → yatay destek
  - 2. mumun HIGH'ı → yatay direnç
  - Bölge ticareti için kullanılır

▸ L4 - GÜÇ DEVAM SEVİYELERİ:
  - Ardışık 2 yeşil mum gerekir
  - 2. mumun open'ı ≈ 1. mumun close'u (tolerans %0.05)
  - Bu eşleşme noktasından yatay ray çizilir
  - Çok güçlü devam sinyali - momentum kopmuyor

▸ L5 - DÖNÜŞ SEVİYELERİ:
  - Kırmızı mumdan sonra yeşil mum gelir
  - Close'lar birbirine yakın (tolerans %0.1)
  - Yeşil mumun close ve open'ından ray çizilir
  - Trend dönüş noktası

▸ LSU (Magnet/Çekim) ve LSD (Alt Ray):
  - Ardışık 2 yeşil mumda HIGH'lar veya LOW'lar DÜŞÜYORSA
  - LSU: Üst ray - fiyatı çeken magnet seviyesi
  - LSD: Alt ray - destek seviyesi
  - Düşüş yapısı içinde oluşur

▸ LF (Fibonacci Seviyeleri):
  - ATL (All Time Low) * 1.618^n formülü
  - n = 1, 2, 3, 4, 5...
  - Altın oran bazlı hedef seviyeleri
  - Uzun vadeli hedefler için kullanılır

▸ LG (Golden/İkili Seviyeleri):
  - ATL * 2^n formülü
  - n = 1, 2, 3, 4, 5...
  - Güçlü psikolojik seviyeler
  - Büyük destek/direnç noktaları

▸ LN (Yeni Coin Seviyeleri):
  - SADECE 30 günden genç coinlerde kullanılır
  - Günlük grafiğin çizilebilir olması için 1.5 aydan az olmalı
  - İlk 2 yeşil mumdan hesaplanan özel seviyeler
  - Yeni coinlerde diğer seviyeler yetersiz olduğunda devreye girer

═══════════════════════════════════════
SİNYAL KURALLARI (KESİN VE DEĞİŞMEZ):
═══════════════════════════════════════

BUY SİNYALİ:
- Fiyat bir seviyenin ÜSTÜNE çıktığında
- Koşul: low <= seviye <= close (mum seviyeyi kapsıyor ve üstünde kapanıyor)
- Giriş: Seviye fiyatı

SELL SİNYALİ:
- Fiyat bir seviyenin ALTINA indiğinde
- Koşul: close <= seviye <= high (mum seviyeyi kapsıyor ve altında kapanıyor)
- Giriş: Seviye fiyatı

TP (Hedef) BELİRLEME:
- TP1: Giriş yönünde 2. veya 3. en yakın seviye (UZAK hedef, kısa mesafe DEĞİL)
- TP2: 3. veya 4. seviye (uzun vadeli)
- ASLA girişe yakın hedef verme, hedef her zaman geniş olmalı

SL (Stop Loss) BELİRLEME:
- Girişin TERSİ yönde en yakın seviyenin %0.2 arkası
- SL her zaman DAR olmalı
- ASLA geniş stop verme

R/R (Risk/Ödül):
- Minimum 1:2 zorunlu
- İdeal: 1:3 veya üzeri
- R/R 1:2'nin altındaysa sinyal VERİLMEZ

═══════════════════════════════════════
ZAMAN DİLİMİ ANALİZİ:
═══════════════════════════════════════

Her timeframe'de AYRI AYRI çizim yapılır:
- Her TF'nin kendi kırmızı mumları → kendi LA seviyeleri
- Her TF'nin kendi ardışık yeşil mumları → kendi L1-L5 seviyeleri
- Her TF'nin kendi yapısı bağımsızdır

RENK SINIFLANDIRMASI (her TF için):
- 🟢 YEŞİL: Son mum yeşil + önceki mumlarla yükseliş yapısı oluşmuş
- 🔴 KIRMIZI: Son mum kırmızı + düşüş yapısı oluşmuş
- ⚪ NÖTR: Kararsız, yatay, net yapı yok

SCALP: 1m, 5m, 15m, 30m, 1h (biraz 4h)
SWING: 30m, 1h, 4h, 1d (biraz 1W)
GENEL ANALİZ: Tüm TF'ler

═══════════════════════════════════════
YASAKLAR (KESİNLİKLE YAPMA):
═══════════════════════════════════════
- RSI, MACD, Bollinger, Stochastic KULLANMA
- Elliott Wave, harmonik pattern KULLANMA
- Order block, supply/demand zone KULLANMA
- Ichimoku, moving average KULLANMA
- Volume profile, VWAP KULLANMA
- Haber/sentiment analizi YAPMA
- Başka trader'ların fikirlerini SÖYLEME
- "Genel olarak piyasa..." gibi belirsiz yorumlar YAPMA
- Strateji dışı HİÇBİR kavram KULLANMA
"""


class MistralAI:
    def __init__(self):
        self.keys = list(MISTRAL_KEYS)
        self.key_index = 0
        self.error_log = []

    def _get_key(self) -> str:
        if not self.keys:
            return ""
        return self.keys[self.key_index % len(self.keys)]

    def _rotate_key(self):
        if len(self.keys) > 1:
            self.key_index = (self.key_index + 1) % len(self.keys)
            logger.info(f"Mistral key rotasyonu -> key {self.key_index + 1}")

    def chat(self, system_prompt: str, user_message: str, retry: int = 0) -> str:
        """Mistral AI'ya mesaj gönder - temperature 0.0."""
        if not self.keys:
            return "Mistral API key'leri ayarlanmamış."

        key = self._get_key()
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": MISTRAL_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": 2000,
            "temperature": 0.0,
        }

        try:
            resp = httpx.post(
                MISTRAL_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=30,
            )

            if resp.status_code == 429:
                if retry < len(self.keys):
                    self._rotate_key()
                    time.sleep(1)
                    return self.chat(system_prompt, user_message, retry + 1)
                return "Rate limit aşıldı, lütfen biraz bekleyin."

            if resp.status_code != 200:
                if retry < len(self.keys):
                    self._rotate_key()
                    time.sleep(0.5)
                    return self.chat(system_prompt, user_message, retry + 1)
                return f"API hatası: {resp.status_code}"

            data = resp.json()
            return data["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"Mistral hatası: {e}")
            if retry < len(self.keys):
                self._rotate_key()
                time.sleep(1)
                return self.chat(system_prompt, user_message, retry + 1)
            return f"AI bağlantı hatası: {e}"

    def analyze_chart(self, symbol: str, candles_summary: str, structures_summary: str, mode: str = "analiz") -> str:
        """Grafik analizi yap - önceki hatalardan öğren."""
        # Supabase'den öğrenilen dersleri al
        lessons_text = ""
        try:
            import supabase_db as db
            lessons = db.get_error_lessons(symbol=symbol, limit=5)
            if not lessons:
                lessons = db.get_error_lessons(limit=3)
            if lessons:
                lessons_text = "\n\nÖNCEKİ HATALARIMIZ (Bu hataları TEKRARLAMA, derslerden öğren):\n"
                for l in lessons:
                    lessons_text += f"- {l.get('content', '')[:200]}\n"
        except:
            pass

        if mode == "scalp":
            focus = "SCALP analizi yap. 1m-5m-15m-30m-1h grafiklere odaklan. Nokta atışı giriş, dar stop, geniş hedef."
        elif mode == "swing":
            focus = "SWING analizi yap. 30m-1h-4h-1d grafiklere odaklan. Geniş hedef, dar stop."
        else:
            focus = "DETAYLI analiz yap. Tüm timeframe'leri değerlendir. Kısa ve uzun vadeli hedefler ver."

        user_msg = f"""
{symbol} paritesini SADECE strateji kurallarına göre analiz et.

{focus}

MUM VERİLERİ (her TF için):
{candles_summary}

HESAPLANAN STRATEJİ SEVİYELERİ:
{structures_summary}

YANITINI ŞU FORMATTA VER:
1. Her timeframe: 🟢/🔴/⚪ + hangi seviyeler aktif + ne oluşmuş
2. Genel yön: Seviyelerin çoğunluğu ne diyor
3. Giriş noktası: Hangi seviyeden, neden
4. TP1 (kısa vadeli): Hangi seviye
5. TP2 (uzun vadeli): Hangi seviye
6. SL: Hangi seviyenin arkası
7. R/R oranı
8. Güven: %0-100 (seviyelerin netliğine göre)
9. Uyarılar: Yakın tehlikeli seviyeler
{lessons_text}
"""
        return self.chat(STRATEGY_KNOWLEDGE, user_msg)

    def analyze_error(self, signal_data: str, result: str) -> str:
        """Stop olan sinyali analiz et - hatalardan öğren."""
        user_msg = f"""
Bir sinyal STOP oldu. SADECE strateji kurallarına göre analiz et:

SİNYAL BİLGİLERİ:
{signal_data}

SONUÇ: {result}

CEVAPLA:
1. Hangi seviye gözden kaçtı? (LA, L1, L2, L3, L4, L5, LSU, LSD, LF, LG hangisi?)
2. Hangi TF'de uyarı vardı ama göremedik?
3. SL yanlış mı belirlendi? Hangi seviyenin arkasına konmalıydı?
4. TP çok mu uzaktı? Daha yakın hangi seviye vardı?
5. Bir dahaki sefere bu coin/yapıda ne yapmalıyız?
6. Strateji kurallarından hangisi ihlal edildi?
"""
        self.error_log.append({"signal": signal_data, "result": result})
        return self.chat(STRATEGY_KNOWLEDGE, user_msg)

    def protrader_chat(self, conversation: list[dict]) -> str:
        """ProTrader AI sohbet modu - analiz de yapabilir."""
        if not self.keys:
            return "Mistral API key'leri ayarlanmamış."

        key = self._get_key()
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

        chat_system = STRATEGY_KNOWLEDGE + """

SOHBET MODU:
- Kullanıcıyla strateji hakkında sohbet ediyorsun
- Sorularını SADECE strateji bilgine göre cevapla
- Kullanıcı bir parite sorduğunda, bildiklerine göre analiz yap
- Kullanıcı "analiz et", "ne yapmalıyım", "giriş var mı" gibi şeyler sorarsa, strateji kurallarına göre yönlendir
- ASLA strateji dışı kavram kullanma (RSI, MACD, Bollinger vs. YOK)
- Eğer kullanıcı strateji dışı bir şey sorarsa, kibarca "Ben sadece çok katmanlı grafik yapısı stratejisini kullanıyorum" de
- Kısa ve net cevaplar ver, gereksiz uzatma
- Kullanıcı bir coin sorduğunda hangi seviyelere bakması gerektiğini söyle
- Geçmiş hatalardan öğrendiğin dersleri uygula
"""

        # Supabase'den son dersleri al
        try:
            import supabase_db as db
            lessons = db.get_error_lessons(limit=3)
            if lessons:
                chat_system += "\n\nÖĞRENDİĞİN SON DERSLER:\n"
                for l in lessons:
                    chat_system += f"- {l.get('content', '')[:150]}\n"
        except:
            pass

        messages = [{"role": "system", "content": chat_system}]
        messages.extend(conversation)

        payload = {
            "model": MISTRAL_MODEL,
            "messages": messages,
            "max_tokens": 1500,
            "temperature": 0.0,
        }

        try:
            resp = httpx.post(MISTRAL_ENDPOINT, headers=headers, json=payload, timeout=30)
            if resp.status_code == 429:
                self._rotate_key()
                key = self._get_key()
                headers["Authorization"] = f"Bearer {key}"
                time.sleep(1)
                resp = httpx.post(MISTRAL_ENDPOINT, headers=headers, json=payload, timeout=30)

            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            return f"API hatası: {resp.status_code}"
        except Exception as e:
            return f"Bağlantı hatası: {e}"
