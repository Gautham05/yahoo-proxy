from flask import Flask, request, jsonify
from flask_cors import CORS
from curl_cffi import requests as cffi_requests
from concurrent.futures import ThreadPoolExecutor
import time

app = Flask(__name__)
CORS(app)

def fetch_ticker(ticker):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d&includePrePost=true'
    try:
        res = cffi_requests.get(url, impersonate='chrome120', timeout=8)
        data = res.json()
        result = data['chart']['result'][0]
        meta = result['meta']

        pre_start  = meta['currentTradingPeriod']['pre']['start']
        pre_end    = meta['currentTradingPeriod']['pre']['end']
        reg_start  = meta['currentTradingPeriod']['regular']['start']
        reg_end    = meta['currentTradingPeriod']['regular']['end']
        post_start = meta['currentTradingPeriod']['post']['start']
        post_end   = meta['currentTradingPeriod']['post']['end']

        now = int(time.time())
        if pre_start <= now < pre_end:
            marketState = 'PRE'
        elif reg_start <= now < reg_end:
            marketState = 'REGULAR'
        elif post_start <= now < post_end:
            marketState = 'POST'
        else:
            marketState = 'CLOSED'

        timestamps = result.get('timestamp', [])
        closes = result.get('indicators', {}).get('quote', [{}])[0].get('close', [])
        candles = [(t, c) for t, c in zip(timestamps, closes) if c is not None]

        pre_candles  = [c for c in candles if pre_start  <= c[0] < pre_end]
        post_candles = [c for c in candles if post_start <= c[0] < post_end]
        reg_candles  = [c for c in candles if reg_start  <= c[0] < reg_end]

        preMarketPrice     = pre_candles[-1][1]  if pre_candles  else None
        postMarketPrice    = post_candles[-1][1] if post_candles else None
        regularMarketPrice = reg_candles[-1][1]  if reg_candles  else meta.get('regularMarketPrice')
        previousClose      = meta.get('chartPreviousClose') or meta.get('previousClose')

        return ticker, {
            'regularMarketPrice':  regularMarketPrice,
            'previousClose':       previousClose,
            'preMarketPrice':      preMarketPrice,
            'preMarketChangePct':  round((preMarketPrice - previousClose) / previousClose * 100, 4) if preMarketPrice and previousClose else None,
            'postMarketPrice':     postMarketPrice,
            'postMarketChangePct': round((postMarketPrice - regularMarketPrice) / regularMarketPrice * 100, 4) if postMarketPrice and regularMarketPrice else None,
            'marketState':         marketState,
        }
    except Exception as e:
        return ticker, {'error': str(e)}

@app.route('/quote')
def quote():
    tickers = [t.strip().upper() for t in request.args.get('tickers', '').split(',') if t.strip()]
    with ThreadPoolExecutor(max_workers=20) as ex:
        results = dict(ex.map(fetch_ticker, tickers))
    return jsonify(results)

# Keep-alive endpoint — pinged every 14 min by the React app
# to prevent Render free tier from sleeping
@app.route('/ping')
def ping():
    return 'ok', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
