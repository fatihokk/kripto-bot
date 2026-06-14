import ccxt
import pandas as pd
import time
import requests
from datetime import datetime

# ==========================================
# ⚙️ KULLANICI AYARLARI VE AYARLAMALAR
# ==========================================
TELEGRAM_TOKEN = "8925901445:AAFkeg_2qMki1q8t16ICfns0a-YkpaGWPrM"
TELEGRAM_CHAT_ID = "1552779112"

WATCHLIST = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'RENDER/USDT', 'AVAX/USDT']

# 💰 SİMÜLASYON CÜZDANI
START_BUDGET = 1000.0       
TOTAL_REALIZED_PROFIT = 0.0 

virtual_wallet = {
    "USDT": 1000.0,
    "POSITIONS": {}         
}

TRADE_AMOUNT_USDT = 50.0    
PROFIT_TARGET_PCT = 0.003   # %0.3 Hızlı test kâr hedefi

# Şifresiz Canlı Binance Bağlantısı
exchange = ccxt.binance({'enableRateLimit': True})

# Günlük periyodik rapor saatleri (Sabah, Öğle, Akşam)
REPORT_HOURS = ["09:00", "14:00", "21:00"]
last_reported_time = "" # Aynı dakika içinde üst üste mesaj atmasın diye

# ==========================================
# 💵 CANLI DOLAR/TL KURU ÇEKME FONKSİYONU
# ==========================================
def get_usdt_try_price():
    try:
        ticker = exchange.fetch_ticker('USDT/TRY')
        return float(ticker['close'])
    except:
        return 36.50 

# ==========================================
# 📢 TELEGRAM BİLDİRİM FONKSİYONU
# ==========================================
def send_telegram(message):
    print(f"[TELEGRAM]: {message}")
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Telegram gönderme hatası: {e}")

# ==========================================
# 📊 TOPLAM BAKİYE VE KÂR/ZARAR HESAPLAMA
# ==========================================
def get_wallet_report():
    current_crypto_value = 0.0
    positions_text = ""
    usdt_try = get_usdt_try_price()
    
    for symbol, pos in virtual_wallet["POSITIONS"].items():
        try:
            ticker = exchange.fetch_ticker(symbol)
            live_price = ticker['close']
            current_value = pos["amount"] * live_price
            current_crypto_value += current_value
            
            coin_pnl = ((live_price - pos["buy_price"]) / pos["buy_price"]) * 100
            positions_text += f"• {symbol}: {pos['amount']:.4f} adet (Maliyet: {pos['buy_price']:.2f}, Canlı Fiyat: {live_price:.2f}, PNL: %{coin_pnl:+.2f})\n"
        except:
            current_crypto_value += pos["amount"] * pos["buy_price"]
            positions_text += f"• {symbol}: Değer okunamadı, maliyetten hesaplandı.\n"

    total_balance = virtual_wallet["USDT"] + current_crypto_value
    total_pnl_usd = total_balance - START_BUDGET
    total_pnl_pct = (total_pnl_usd / START_BUDGET) * 100

    # TL Çevrimleri
    cash_tl = virtual_wallet["USDT"] * usdt_try
    crypto_tl = current_crypto_value * usdt_try
    total_tl = total_balance * usdt_try
    realized_profit_tl = TOTAL_REALIZED_PROFIT * usdt_try
    total_pnl_tl = total_pnl_usd * usdt_try

    if positions_text == "":
        positions_text = "• Şu an açık pozisyon yok.\n"

    report = (
        f"💳 *GÜNCEL CÜZDAN RAPORU* (Kur: {usdt_try:.2f} TL)\n"
        f"-----------------------------------------\n"
        f"💵 Boştaki Nakit: {virtual_wallet['USDT']:.2f} USDT *(~{cash_tl:,.2f} TL)*\n"
        f"🪙 Coinlerin Canlı Değeri: {current_crypto_value:.2f} USDT *(~{crypto_tl:,.2f} TL)*\n"
        f"💰 *Toplam Portföy Değeri:* {total_balance:.2f} USDT *(~{total_tl:,.2f} TL)*\n"
        f"💵 *Net Gerçekleşen Toplam Kâr:* {TOTAL_REALIZED_PROFIT:+.2f} USDT *(~{realized_profit_tl:,.2f} TL)*\n"
        f"📈 *Toplam PNL Durumu:* {total_pnl_usd:+.2f} USDT (%{total_pnl_pct:+.2f}) *(~{total_pnl_tl:,.2f} TL)*\n\n"
        f"📋 *Açık Pozisyonlar:*\n{positions_text}"
    )
    return report

# ==========================================
# ⏱️ SAAT KONTROLÜ (GÜNDE 3 RAPOR İÇİN)
# ==========================================
def check_scheduled_reports():
    global last_reported_time
    # Şu anki saat ve dakikayı alıyoruz (Örn: "14:00")
    current_time = datetime.now().strftime("%H:%M")
    
    # Eğer şu anki saat bizim rapor saatlerimizden biriyse ve o dakika henüz rapor atılmadıysa
    if current_time in REPORT_HOURS and current_time != last_reported_time:
        print(f"[SİSTEM]: Planlı rapor saati geldi ({current_time}). Rapor gönderiliyor...")
        send_telegram(f"⏰ *Zamanlanmış Durum Raporu ({current_time})*\n\n" + get_wallet_report())
        last_reported_time = current_time

# ==========================================
# 🔄 SİMÜLASYON MOTORU
# ==========================================
def run_simulation_bot():
    global TOTAL_REALIZED_PROFIT
    print("\n🔄 Bot yeni bir tarama döngüsü başlattı...")
    
    # 1. Satış Kontrolü
    for symbol in list(virtual_wallet["POSITIONS"].keys()):
        last_data = calculate_indicators(symbol)
        if last_data is None: continue
        
        current_price = last_data['close']
        buy_price = virtual_wallet["POSITIONS"][symbol]["buy_price"]
        amount = virtual_wallet["POSITIONS"][symbol]["amount"]
        
        if current_price >= buy_price * (1 + PROFIT_TARGET_PCT):
            revenue = amount * current_price
            profit = revenue - (amount * buy_price)
            
            TOTAL_REALIZED_PROFIT += profit
            virtual_wallet["USDT"] += revenue
            del virtual_wallet["POSITIONS"][symbol]
            
            usdt_try = get_usdt_try_price()
            profit_tl = profit * usdt_try
            
            send_telegram(f"💰 *[Sanal Satış]:* {symbol} %{PROFIT_TARGET_PCT*100} kârla satıldı!\nAlış Maliyeti: {buy_price:.4f} -> Satış Fiyatı: {current_price:.4f}\n🔥 Sadece Bu İşlemden Gelen Kâr: {profit:+.2f} USDT *(~{profit_tl:,.2f} TL)*\n\n" + get_wallet_report())

    # 2. Alış Kontrolü
    for symbol in WATCHLIST:
        if symbol in virtual_wallet["POSITIONS"]: continue
        
        last_data = calculate_indicators(symbol)
        if last_data is None: continue
        
        current_price = last_data['close']
        rsi = last_data['RSI']
        
        if rsi < 60: 
            if virtual_wallet["USDT"] >= TRADE_AMOUNT_USDT:
                virtual_wallet["USDT"] -= TRADE_AMOUNT_USDT
                amount_to_buy = TRADE_AMOUNT_USDT / current_price
                
                virtual_wallet["POSITIONS"][symbol] = {
                    "amount": amount_to_buy,
                    "buy_price": current_price
                }
                send_telegram(f"🟢 *[Sanal Alım]:* {symbol} için test sinyali tetiklendi!\nAlış Fiyatı: {current_price:.2f}\nRSI: {rsi:.2f}\n\n" + get_wallet_report())
                time.sleep(1)

# ==========================================
# 📈 İNDİKATÖR HESAPLAMA
# ==========================================
def calculate_indicators(symbol, timeframe='4h', limit=100):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        return df.iloc[-1]
    except Exception as e:
        print(f"{symbol} indikatör hatası: {e}")
        return None

# ==========================================
# 🚀 ANA ÇALIŞTIRICI LOOP
# ==========================================
if __name__ == "__main__":
    send_telegram("🚀 *Otomatik Bildirim Modu Aktif!*\n\n💰 Başlangıç Bakiyesi: 1000 USDT\n🎯 Kâr Hedefi: %0.3\n⏰ Her gün 09:00, 14:00 ve 21:00'de otomatik cüzdan raporu gönderilecektir.\n⚠️ Ücretsiz bulut uyumluluğu için manuel bakiye sorgusu kaldırılmıştır.")
    
    send_telegram(get_wallet_report())
    
    loop_timer = 0
    while True:
        try:
            # Her saniye planlı rapor saati geldi mi diye kontrol et kanka ⏱️
            check_scheduled_reports()
            
            # Her 30 saniyede bir Binance'i tara
            if loop_timer >= 30:
                run_simulation_bot()
                loop_timer = 0
                
            time.sleep(1)
            loop_timer += 1
            
        except KeyboardInterrupt:
            print("\nBot durduruldu.")
            break
        except Exception as e:
            print(f"Genel döngü hatası: {e}")
            time.sleep(10)