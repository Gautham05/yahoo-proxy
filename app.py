from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
CORS(app)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

def fetch_ticker(ticker):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d'
    try:
        res = requests.get(url, headers=HEADERS, timeout=8)
        data = res.json()
        meta = data['chart']['result'][0]['meta']
        return ticker, {
            'regularMarketPrice':    meta.get('regularMarketPrice'),
            'previousClose':         meta.get('chartPreviousClose'),
            'preMarketPrice':        meta.get('preMarketPrice'),
            'postMarketPrice':       meta.get('postMarketPrice'),
            'marketState':           meta.get('marketState'),
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
