import os
import google.generativeai as genai

# Google Gemini API anahtarını ortam değişkenlerinden yükle
# Kullanıcının bu anahtarı .env dosyasına veya dağıtım ortamına eklemesi gerekecek.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY ortam değişkeni ayarlanmamış.")

genai.configure(api_key=GEMINI_API_KEY)

# Gemini modelini başlat (ücretsiz ve en iyi versiyonu kullanmak için)
# Model seçimi, mevcut ücretsiz modeller arasında en uygun olanı hedefleyecektir.
# Şu an için 'gemini-pro' en yaygın ve güçlü ücretsiz modeldir.
model = genai.GenerativeModel('gemini-pro')

def supervise_analysis_output(analysis_output: str) -> dict:
    """
    Analiz botunun çıktılarını denetler ve hatalı/riskli analizleri işaretler.
    """
    prompt = f"""Aşağıdaki analiz çıktısını denetle. Çıktıda herhangi bir hata, yanlış bilgi, tutarsızlık veya potansiyel risk (örneğin, yanıltıcı yatırım tavsiyesi, aşırı iyimser/kötümser tahminler) olup olmadığını belirle. 
    Eğer çıktı güvenliyse ve doğru görünüyorsa 'OK' olarak işaretle. 
    Eğer potansiyel riskler veya küçük hatalar içeriyorsa 'RISKY' olarak işaretle ve nedenlerini açıkla. 
    Eğer bariz hatalar veya ciddi yanlış bilgiler içeriyorsa 'ERROR' olarak işaretle ve düzeltilmesi gereken yerleri belirt.

    Analiz Çıktısı:
    {analysis_output}

    Yanıt formatı:
    {{"status": "OK"|"RISKY"|"ERROR", "explanation": "Açıklama"}}
    """
    
    try:
        response = model.generate_content(prompt)
        # Gemini'nin yanıtını JSON olarak ayrıştırmaya çalış
        # Bazen doğrudan JSON döndürmeyebilir, bu durumda manuel ayrıştırma veya hata işleme gerekir.
        # Basitlik adına, doğrudan metin yanıtını döndürüyoruz ve daha sonra ayrıştırılmasını bekliyoruz.
        return {"raw_response": response.text}
    except Exception as e:
        return {"status": "ERROR", "explanation": f"Gemini ile iletişim hatası: {e}"}

def generate_supervision_report(past_supervision_results: list[dict]) -> dict:
    """
    Periyodik denetim raporu oluşturur.
    """
    if not past_supervision_results:
        return {"report": "Henüz denetlenecek sonuç yok.", "summary": ""}

    # Geçmiş denetim sonuçlarını özetlemek için bir prompt oluştur
    results_summary = "\n".join([f"- Status: {res.get('status', 'N/A')}, Explanation: {res.get('explanation', res.get('raw_response', 'N/A'))}" for res in past_supervision_results])

    prompt = f"""Aşağıdaki geçmiş analiz denetim sonuçlarını özetle. 
    Genel eğilimleri, sık karşılaşılan hata veya risk türlerini, botun performansını ve iyileştirme alanlarını belirten kapsamlı bir rapor hazırla.

    Geçmiş Denetim Sonuçları:
    {results_summary}

    Yanıt formatı:
    {{"report": "Detaylı rapor metni", "summary": "Kısa özet"}}
    """

    try:
        response = model.generate_content(prompt)
        return {"raw_response": response.text}
    except Exception as e:
        return {"report": f"Gemini ile iletişim hatası: {e}", "summary": ""}

if __name__ == "__main__":
    # Örnek kullanım
    print("Gemini Supervisor Agent başlatılıyor...")

    # Örnek analiz çıktısı
    sample_analysis_output_ok = "Şirket X'in son çeyrek finansal raporları beklentilerin üzerinde geldi. Gelirler %15 arttı ve net kar %20 yükseldi. Hisse senedi için 'AL' tavsiyesi verilebilir."
    sample_analysis_output_risky = "Şirket Y'nin hisse senedi fiyatı son zamanlarda düşüş eğiliminde. Ancak, yeni bir ürün lansmanı beklentisiyle kısa vadede büyük bir sıçrama yapabilir. Yüksek riskli olmasına rağmen 'AL' düşünülebilir."
    sample_analysis_output_error = "Şirket Z'nin 2023 yılı geliri 100 milyon dolar olarak açıklandı, ancak aslında 10 milyon dolardı. Bu durumda hisse senedi fiyatı hızla yükselecektir."

    print("\n--- Denetim Örneği (OK) ---")
    result_ok = supervise_analysis_output(sample_analysis_output_ok)
    print(result_ok)

    print("\n--- Denetim Örneği (RISKY) ---")
    result_risky = supervise_analysis_output(sample_analysis_output_risky)
    print(result_risky)

    print("\n--- Denetim Örneği (ERROR) ---")
    result_error = supervise_analysis_output(sample_analysis_output_error)
    print(result_error)

    # Örnek rapor oluşturma
    print("\n--- Denetim Raporu Örneği ---")
    past_results = [
        {"status": "OK", "explanation": "Analiz doğru ve risksiz.", "raw_response": "{\"status\": \"OK\", \"explanation\": \"Analiz doğru ve risksiz.\"}"},
        {"status": "RISKY", "explanation": "Yüksek riskli yatırım tavsiyesi içeriyor.", "raw_response": "{\"status\": \"RISKY\", \"explanation\": \"Yüksek riskli yatırım tavsiyesi içeriyor.\"}"},
        {"status": "ERROR", "explanation": "Yanlış finansal veri kullanılmış.", "raw_response": "{\"status\": \"ERROR\", \"explanation\": \"Yanlış finansal veri kullanılmış.\"}"}
    ]
    report = generate_supervision_report(past_results)
    print(report)
