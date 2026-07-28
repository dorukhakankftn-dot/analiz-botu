# MEXC Futures Kripto Analiz Botu

Telegram üzerinden çalışan, Mistral AI destekli, çok katmanlı strateji motorlu kripto analiz botu.

## Özellikler

- **Çok Katmanlı Strateji**: L1-L5, LA, LF, LG, LSU, LSD, LN seviyeleri
- **MEXC Futures**: Tüm timeframe'lerde mum verisi (1m - 1M)
- **Mistral AI**: 4 key rotasyonlu, profesyonel trader analizi
- **Sinyal Takip**: Giriş bekle → Aktif → TP/SL otomatik bildirim
- **Hata Analizi**: Stop olan sinyallerde AI detaylı hata analizi yapar

## Komutlar

| Komut | Açıklama |
|-------|----------|
| /start | Botu başlat |
| /help | Yardım |
| /analiz [parite] | Detaylı analiz (tüm TF'ler) |
| /scalp [parite] | Scalp sinyal (1m-1h) |
| /swing [parite] | Swing sinyal (30m-1W) |
| /sinyaller | Aktif sinyalleri göster |
| /hata_tara | Bot sağlık kontrolü |
| /protrader_ai | AI sohbet başlat |
| /stop_chat | AI sohbet bitir |

## Render Deploy

1. Environment Variables ekle:
   - `TELEGRAM_BOT_TOKEN`
   - `MISTRAL_KEY_1` - `MISTRAL_KEY_4`
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `python main.py`
