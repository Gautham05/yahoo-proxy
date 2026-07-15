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
        res = cffi_requests.get(url, impersonate='chrome120', timeout=10)
        data = res.json()
        result = data['chart']['result'][0]
        meta = result['meta']

        # Trading period boundaries
        pre_start  = meta['currentTradingPeriod']['pre']['start']
        pre_end    = meta['currentTradingPeriod']['pre']['end']
        reg_start  = meta['currentTradingPeriod']['regular']['start']
        reg_end    = meta['currentTradingPeriod']['regular']['end']
        post_start = meta['currentTradingPeriod']['post']['start']
        post_end   = meta['currentTradingPeriod']['post']['end']

        now = int(time.time())

        # Determine marketState from timestamps
        if pre_start <= now < pre_end:
            marketState = 'PRE'
        elif reg_start <= now < reg_end:
            marketState = 'REGULAR'
        elif post_start <= now < post_end:
            marketState = 'POST'
        else:
            marketState = 'CLOSED'

        # Get timestamps + closes from candle data
        timestamps = result.get('timestamp', [])
        closes = result.get('indicators', {}).get('quote', [{}])[0].get('close', [])

        # Build list of (timestamp, close) — filter nulls
        candles = [(t, c) for t, c in zip(timestamps, closes) if c is not None]

        # Find last candle in pre period
        pre_candles = [c for c in candles if pre_start <= c[0] < pre_end]
        preMarketPrice = pre_candles[-1][1] if pre_candles else None

        # Find last candle in post period
        post_candles = [c for c in candles if post_start <= c[0] < post_end]
        postMarketPrice = post_candles[-1][1] if post_candles else None

        # Last regular candle = regularMarketPrice
        reg_candles = [c for c in candles if reg_start <= c[0] < reg_end]
        regularMarketPrice = reg_candles[-1][1] if reg_candles else meta.get('regularMarketPrice')

        previousClose = meta.get('chartPreviousClose') or meta.get('previousClose')

        return ticker, {
            'regularMarketPrice': regularMarketPrice,
            'previousClose':      previousClose,
            'preMarketPrice':     preMarketPrice,
            'preMarketChangePct': round((preMarketPrice - previousClose) / previousClose * 100, 4) if preMarketPrice and previousClose else None,
            'postMarketPrice':    postMarketPrice,
            'postMarketChangePct': round((postMarketPrice - regularMarketPrice) / regularMarketPrice * 100, 4) if postMarketPrice and regularMarketPrice else None,
            'marketState':        marketState,
        }
    except Exception as e:
        return ticker, {'error': str(e)}

@app.route('/quote')
def quote():
    tickers = [t.strip().upper() for t in request.args.get('tickers', '').split(',') if t.strip()]
    with ThreadPoolExecutor(max_workers=5) as ex:
        results = dict(ex.map(lambda t: fetch_ticker(t), tickers))
    return jsonify(results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
