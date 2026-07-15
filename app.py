from flask import Flask, request, jsonify
from flask_cors import CORS
from curl_cffi import requests as cffi_requests
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
CORS(app)

def fetch_ticker(ticker):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d&includePrePost=true'
    try:
        res = cffi_requests.get(url, impersonate='chrome120', timeout=10)
        data = res.json()
        meta = data['chart']['result'][0]['meta']
        return ticker, {
            'regularMarketPrice': meta.get('regularMarketPrice'),
            'previousClose':      meta.get('chartPreviousClose'),
            'preMarketPrice':     meta.get('preMarketPrice'),
            'postMarketPrice':    meta.get('postMarketPrice'),
            'marketState':        meta.get('marketState'),
        }
    except Exception as e:
        return ticker, {'error': str(e)}

@app.route('/quote')
def quote():
    tickers = [t.strip().upper() for t in request.args.get('tickers', '').split(',') if t.strip()]
    with ThreadPoolExecutor(max_workers=5) as ex:
        results = dict(ex.map(lambda t: fetch_ticker(t), tickers))
    return jsonify(results)

# DEBUG — see raw meta fields Yahoo actually returns
@app.route('/debug')
def debug():
    ticker = request.args.get('ticker', 'AAPL')
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d&includePrePost=true'
    res = cffi_requests.get(url, impersonate='chrome120', timeout=10)
    data = res.json()
    meta = data['chart']['result'][0]['meta']
    return jsonify(meta)  # return ALL fields raw

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
