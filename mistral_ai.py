"""Mistral AI entegrasyonu - 4 key rotasyonlu profesyonel trader AI."""

import logging
import time
import json
import httpx
from config import MISTRAL_KEYS, MISTRAL_MODEL, MISTRAL_ENDPOINT

logger = logging.getLogger(__name__)

STRATEGY_KNOWLEDGE = """Sen profesyonel bir kripto futures trader AI'sın. Çok katmanlı grafik yapısı stratejisini mükemmel biliyorsun.

STRATEJİ BİLGİSİ:
- LA (Level A): Kırmızı mumların low değerlerinden çizilen yatay destek seviyeleri. Her timeframe'de kırmızı mum varsa low'u destek olur.
- L1: Ardışık iki yeşil mumun high-high ve low-low noktalarından çizilen ray (eğimli çizgi). Trend yönünü gösterir.
- L2: Ardışık iki yeşil mumun 8 farklı kombinasyonundan (open, low, high, close) çizilen ray'ler. Detaylı trend kanalları oluşturur.
- L3: Ardışık iki yeşil mumda ilk mumun low'u ve ikinci mumun high'ı yatay olarak çizilir. Destek/direnç bölgeleri.
- L4: Ardışık iki yeşil mumda ikinci mumun open'ı birinci mumun close'una çok yakınsa (tolerans %0.05), o noktadan yatay ray çizilir. Güçlü devam sinyali.
- L5: Kırmızı mumdan sonra yeşil mum gelirse ve close'lar yakınsa (tolerans %0.1), yeşil mumun close ve open'ından ray çizilir. Dönüş sinyali.
- LSU/LSD: İki yeşil mumda high'lar veya low'lar düşüyorsa, üst ray (LSU - magnet/çekim) ve alt ray (LSD) çizilir. Düşüş yapısı.
- LF (Fibonacci): ATL * 1.618^n seviyeleri. Altın oran hedefleri.
- LG (Golden): ATL * 2^n seviyeleri. Güçlü psikolojik seviyeler.
- LN (New Coin): Yeni coinlerde (30 günden genç) ilk 2 yeşil mumdan hesaplanan özel seviyeler.

KURALLAR:
- Kırmızı mumun LOW'u her zaman destek olarak çizilir (LA)
- Yeşil mumlar ardışık geldiğinde L1-L5 seviyeleri oluşur
- Ray'ler eğimli çizgilerdir, zaman geçtikçe fiyat projeksiyonu değişir
- Horizontal seviyeler sabit kalır
- Bir seviyeye fiyat yaklaştığında o seviye aktif olur
- BUY sinyali: Fiyat bir seviyenin üstüne çıktığında (low <= seviye <= close)
- SELL sinyali: Fiyat bir seviyenin altına indiğinde (close <= seviye <= high)
- TP: 2. veya 3. üst/alt seviye (geniş hedef, kısa mesafe değil)
- SL: Giriş seviyesinin hemen altındaki/üstündeki en yakın seviyenin %0.2 arkası (dar stop)
- Minimum R/R oranı: 1:2 (risk küçük, ödül büyük)
- TP2 (uzun vadeli): 3. veya 4. seviye

ZAMAN DİLİMİ ANALİZİ:
- Scalp: 1m, 5m, 15m, 30m, 1h (biraz 4h) - Kısa vadeli, dakikalar-saatler
- Swing: 30m, 1h, 4h, 1d (biraz 1W) - Orta vadeli, günler-haftalar
- Genel Analiz: Tüm TF'ler - Büyük resim

HER ZAMAN DİLİMİ İÇİN RENK SINIFLANDIRMASI:
- Yeşil: Son mum yeşil + önceki mumlarla yükseliş yapısı
- Kırmızı: Son mum kırmızı + düşüş yapısı
- Nötr: Kararsız, yatay hareket
"""


class MistralAI:
    def __init__(self):
        self.keys = list(MISTRAL_KEYS)
        self.key_index = 0
        self.error_log = []  # Hata analizi için

    def _get_key(self) -> str:
        if not self.keys:
            return ""
        return self.keys[self.key_index % len(self.keys)]

    def _rotate_key(self):
        if len(self.keys) > 1:
            self.key_index = (self.key_index + 1) % len(self.keys)
            logger.info(f"Mistral key rotasyonu -> key {self.key_index + 1}")

    def chat(self, system_prompt: str, user_message: str, retry: int = 0) -> str:
        """Mistral AI'ya mesaj gönder."""
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
            "temperature": 0.3,
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
                lessons_text = "\n\nÖNCELİ HATALARIMIZ (Öğrenilen dersler - BUNLARI TEKRARLAMA):\n"
                for l in lessons:
                    lessons_text += f"- {l.get('content', '')[:200]}\n"
        except:
            pass
        if mode == "scalp":
            focus = "SCALP odaklı analiz yap. 1m-5m-15m-30m-1h grafiklere odaklan. Nokta atışı giriş, kısa vadeli hedef ve dar stop ver."
        elif mode == "swing":
            focus = "SWING odaklı analiz yap. 30m-1h-4h-1d grafiklere odaklan. Orta vadeli giriş, geniş hedef ve makul stop ver."
        else:
            focus = "DETAYLI analiz yap. Tüm timeframe'leri değerlendir. Kısa ve uzun vadeli hedefler ver."

        user_msg = f"""
{symbol} paritesini analiz et.

{focus}

MUM VERİLERİ:
{candles_summary}

STRATEJİ SEVİYELERİ:
{structures_summary}

LÜTFEN ŞU FORMATTA YANIT VER:
1. Her timeframe için durum (Yeşil/Kırmızı/Nötr) ve kısa açıklama
2. Genel yön değerlendirmesi
3. Giriş noktası (entry)
4. Kısa vadeli hedef (TP1)
5. Uzun vadeli hedef (TP2) - sadece analiz/swing modunda
6. Stop Loss (SL)
7. Risk/Ödül oranı
8. Güven seviyesi (%0-100)
9. Ek notlar ve uyarılar
{lessons_text}
"""
        return self.chat(STRATEGY_KNOWLEDGE, user_msg)

    def analyze_error(self, signal_data: str, result: str) -> str:
        """Stop olan sinyali analiz et - hatalardan öğren."""
        user_msg = f"""
Bir sinyal STOP oldu. Analiz et ve hatalarımızı bul:

SİNYAL BİLGİLERİ:
{signal_data}

SONUÇ: {result}

LÜTFEN:
1. Neden stop olduk? Hangi seviye/yapı gözden kaçtı?
2. Hangi timeframe'de uyarı işareti vardı?
3. Bir dahaki sefere ne yapmalıyız?
4. Strateji kurallarından hangisini ihlal ettik?
5. İyileştirme önerileri
"""
        self.error_log.append({"signal": signal_data, "result": result})
        return self.chat(STRATEGY_KNOWLEDGE, user_msg)

    def protrader_chat(self, conversation: list[dict]) -> str:
        """ProTrader AI sohbet modu."""
        if not self.keys:
            return "Mistral API key'leri ayarlanmamış."

        key = self._get_key()
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

        messages = [{"role": "system", "content": STRATEGY_KNOWLEDGE + "\n\nKullanıcıyla sohbet ediyorsun. Strateji hakkında sorularını cevapla, trade fikirleri tartış, analiz yap."}]
        messages.extend(conversation)

        payload = {
            "model": MISTRAL_MODEL,
            "messages": messages,
            "max_tokens": 1500,
            "temperature": 0.5,
        }

        try:
            resp = httpx.post(MISTRAL_ENDPOINT, headers=headers, json=payload, timeout=30)
            if resp.status_code == 429:
                self._rotate_key()
                time.sleep(1)
                resp = httpx.post(MISTRAL_ENDPOINT, headers=headers, json=payload, timeout=30)

            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            return f"API hatası: {resp.status_code}"
        except Exception as e:
            return f"Bağlantı hatası: {e}"
