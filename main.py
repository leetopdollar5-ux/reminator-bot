import os
from fastapi import FastAPI, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
import ccxt
import concurrent.futures

app = FastAPI(title="Reminator Control Panel", description="Powered by Cee Joy")

# Security layer: Prevent strangers from triggering your bot
API_KEY_NAME = "X-Reminator-Token"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)
REM_SECRET_TOKEN = os.getenv("REMINATOR_TOKEN", "change_this_to_a_secure_password")

# Data format standard for incoming signals
class TradeSignal(BaseModel):
    symbol: str
    side: str  # "buy" or "sell"
    amount: float

class ReminatorEngine:
    def __init__(self):
        # Safely loads exchange keys from your secure cloud dashboard environment variables
        self.exchange = ccxt.binance({
            'apiKey': os.getenv("EXCHANGE_API_KEY"),
            'secret': os.getenv("EXCHANGE_SECRET_KEY"),
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })

    def cee_joy_risk_engine(self, entry_price, side, sl_percent=1.0, tp_percent=2.0):
        if side.upper() == "BUY":
            stop_loss = entry_price * (1 - (sl_percent / 100))
            take_profit = entry_price * (1 + (tp_percent / 100))
        else:
            stop_loss = entry_price * (1 + (sl_percent / 100))
            take_profit = entry_price * (1 - (tp_percent / 100))
        return round(stop_loss, 4), round(take_profit, 4)

    def execute_sniper(self, signal: TradeSignal):
        try:
            # 1. Market Entry Execution
            order = self.exchange.create_order(signal.symbol, 'market', signal.side, signal.amount)
            entry_price = order['price'] if order['price'] else order['average']
            
            # 2. Risk Bracket Calculations
            sl_price, tp_price = self.cee_joy_risk_engine(entry_price, signal.side)
            opposite_side = 'sell' if signal.side.lower() == 'buy' else 'buy'
            
            # 3. Fire Protective Safe Guards
            self.exchange.create_order(signal.symbol, 'STOP_MARKET', opposite_side, signal.amount, params={'stopPrice': sl_price})
            self.exchange.create_order(signal.symbol, 'TAKE_PROFIT_MARKET', opposite_side, signal.amount, params={'stopPrice': tp_price})
            
            return {"status": "success", "entry": entry_price, "sl": sl_price, "tp": tp_price}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

# Home Screen UI Endpoint (Visible from mobile/desktop browser)
@app.get("/")
def home():
    return {
        "bot_name": "REMINATOR",
        "system_status": "ONLINE",
        "engine": "Powered by Cee Joy",
        "message": "Ready to receive multi-market triggers."
    }

# Execution Trigger Endpoint 
@app.post("/v1/sniper")
def trigger_sniper(signals: list[TradeSignal], token: str = Security(api_key_header)):
    if token != REM_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid Reminator Token")
        
    bot = ReminatorEngine()
    
    # Process multi-trade execution blocks simultaneously within milliseconds
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(bot.execute_sniper, signals))
        
    return {"engine": "Cee Joy Matrix", "results": results}
