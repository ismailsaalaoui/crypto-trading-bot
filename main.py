#main.py
# كود 1: استيراد المكتبات
import ccxt
import pandas as pd
import requests
import time
from datetime import datetime
import numpy as np
import ta
# كود 2: إعداد الإتصال وتحميل البيانات
class Settings:
    def __init__(self):
        self.api_key = "6fcd6a6e-25b2-4a27-a630-65814717bc9c"
        self.api_secret = "62CC999AFE0826DF17566683274882DC"
        self.passphrase = "Saalaoui_1997"

class DataFetcher:
    def __init__(self, settings):
        self.settings = settings
        self.exchange = ccxt.okx({
            'apiKey': self.settings.api_key,
            'secret': self.settings.api_secret,
            'password': self.settings.passphrase,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'},
        })

    def fetch_ohlcv(self, symbol, timeframe="15m", limit=150):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"فشل تحميل بيانات {symbol}: {e}")
            return pd.DataFrame()
# كود 3 : المحلل الفني TechnicalAnalyzer (بدون talib)
class TechnicalAnalyzer:
    def analyze(self, df):
        df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
        df['ema_20'] = ta.trend.EMAIndicator(df['close'], window=20).ema_indicator()
        df['ema_50'] = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator()
        df['macd'] = ta.trend.MACD(df['close']).macd()
        df['macd_signal'] = ta.trend.MACD(df['close']).macd_signal()
        
        bb = ta.volatility.BollingerBands(df['close'])
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()
        
        df['adx'] = ta.trend.ADXIndicator(df['high'], df['low'], df['close']).adx()
        df['stoch_rsi'] = ta.momentum.StochRSIIndicator(df['close']).stochrsi_k()
        
        return df
# كود 4: استراتيجية اتخاذ القرار (شراء أو بيع)
class StrategyEngine:
    def evaluate(self, df):
        latest = df.iloc[-1]
        previous = df.iloc[-2]

        signal = None
        reasons = []

        # تقاطع EMA
        if previous['ema_20'] < previous['ema_50'] and latest['ema_20'] > latest['ema_50']:
            signal = "شراء"
            reasons.append("تقاطع EMA20 فوق EMA50")
        elif previous['ema_20'] > previous['ema_50'] and latest['ema_20'] < latest['ema_50']:
            signal = "بيع"
            reasons.append("تقاطع EMA20 تحت EMA50")

        # تأكيد RSI
        if signal == "شراء" and latest['rsi'] < 35:
            reasons.append("RSI أقل من 35 (فرصة شراء)")
        elif signal == "بيع" and latest['rsi'] > 65:
            reasons.append("RSI أكبر من 65 (فرصة بيع)")
        else:
            signal = None

        # تأكيد MACD
        if signal == "شراء" and latest['macd'] > latest['macd_signal']:
            reasons.append("MACD صاعد")
        elif signal == "بيع" and latest['macd'] < latest['macd_signal']:
            reasons.append("MACD هابط")
        else:
            signal = None

        # تأكيد Bollinger Bands
        if signal == "شراء" and latest['close'] < latest['bb_lower']:
            reasons.append("السعر قريب من الحد السفلي لـ Bollinger Bands")
        elif signal == "بيع" and latest['close'] > latest['bb_upper']:
            reasons.append("السعر قريب من الحد العلوي لـ Bollinger Bands")
        else:
            signal = None

        # تأكيد ADX
        if latest['adx'] < 20:
            signal = None
            reasons.append("الاتجاه ضعيف (ADX تحت 20)")

        return {"signal": signal, "reasons": reasons}
# كود 5: إعداد كود الإرسال إلى تليجرام
class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id

    def send_signal(self, symbol, signal_type, price, reasons):
        signal_strength = "قوي جدا" if len(reasons) >= 4 else "متوسط" if len(reasons) == 3 else "ضعيف"

        target1 = price * (1.01 if signal_type == "شراء" else 0.99)
        target2 = price * (1.02 if signal_type == "شراء" else 0.98)
        stop_loss = price * (0.985 if signal_type == "شراء" else 1.015)

        reasons_text = "\n".join(f"✅ {reason}" for reason in reasons)

        message = f"""
<b>اسم العملة:</b> {symbol}
<b>نوع الإشارة:</b> {signal_type}
<b>السعر الحالي:</b> {price:.2f}
<b>قوة الإشارة:</b> {signal_strength}
<b>🎯 الأهداف:</b>
- الهدف الأول: {target1:.2f}
- الهدف الثاني: {target2:.2f}
<b>🛑 وقف الخسارة:</b> {stop_loss:.2f}
<b>📄 أسباب الإشارة:</b>
{reasons_text}

🕰️ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        try:
            response = requests.post(url, data=data)
            if response.status_code == 200:
                print(f"✅ تم إرسال توصية {symbol}")
            else:
                print(f"❌ فشل الإرسال {response.text}")
        except Exception as e:
            print(f"❌ خطأ أثناء الإرسال: {e}")
# كود 6 : التحليل والإرسال التلقائي
class MultiTimeframeAnalyzer:
    def __init__(self, settings, token, chat_id):
        self.settings = settings
        self.fetcher = DataFetcher(settings)
        self.analyzer = TechnicalAnalyzer()
        self.strategy = StrategyEngine()
        self.notifier = TelegramNotifier(token, chat_id)

    def decide_and_notify(self, symbol):
        timeframes = ['15m', '1h', '4h']
        results = {}

        for timeframe in timeframes:
            df = self.fetcher.fetch_ohlcv(symbol, timeframe)
            if df.empty or len(df) < 50:
                print(f"⚠️ تخطي {symbol} بسبب نقص البيانات في الفريم {timeframe}")
                continue
            df = self.analyzer.analyze(df)
            result = self.strategy.evaluate(df)
            results[timeframe] = result

        valid_signals = {tf: res for tf, res in results.items() if res['signal']}

        if len(valid_signals) >= 2:
            signal_types = [res['signal'] for res in valid_signals.values()]
            if all(s == "شراء" for s in signal_types):
                final_signal = "شراء"
            elif all(s == "بيع" for s in signal_types):
                final_signal = "بيع"
            else:
                final_signal = None
        else:
            final_signal = None

        if final_signal:
            price = df['close'].iloc[-1]
            reasons = []
            for tf, res in valid_signals.items():
                reasons.append(f"إشارة {res['signal']} على الفريم {tf}")
                for r in res['reasons']:
                    reasons.append(f"✅ {r} ({tf})")

            self.notifier.send_signal(
                symbol=symbol,
                signal_type=final_signal,
                price=price,
                reasons=reasons
            )
        else:
            print(f"⏳ لا توجد فرصة قوية لـ {symbol}")
# كود 7 : بدء تشغيل الفحص والإرسال كل 5 دقائق مع تجاوز العملات التي بها خطأ

# إعداد البوت
settings = Settings()
token = "توكن البوت"
chat_id = "معرف الشات"
multi_analyzer = MultiTimeframeAnalyzer(settings, token, chat_id)

# حلقة العمل الدائمة
while True:
    print(f"🔁 بدء جولة فحص جديدة: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        markets = multi_analyzer.fetcher.exchange.load_markets()
        spot_symbols = [symbol for symbol in markets if '/USDT' in symbol]
        
        for symbol in spot_symbols:
            print(f"🔎 فحص {symbol}...")
            try:
                multi_analyzer.decide_and_notify(symbol)
            except Exception as e_symbol:
                print(f"⚠️ تخطي {symbol} بسبب خطأ: {e_symbol}")

        print("✅ انتهى فحص جميع العملات!")
        print("⏳ انتظر 5 دقائق قبل الجولة التالية...")
        time.sleep(5 * 60)  # انتظر 5 دقائق

    except Exception as e_all:
        print(f"⚠️ خطأ عام أثناء الفحص: {e_all}")
        print("🔁 إعادة المحاولة بعد دقيقة...")
        time.sleep(60)  # انتظر دقيقة وأعد المحاولة