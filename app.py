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
    # quoteSummary price module has preMarketPrice, postMarketPrice, marketState
    url = f'https://query1.finance.yahoo.com/v11/finance/quoteSummary/{ticker}?modules=price'
    try:
        res = requests.get(url, headers=HEADERS, timeout=8)
        data = res.json()
        p = data['quoteSummary']['result'][0]['price']
        return ticker, {
            'regularMarketPrice':    p.get('regularMarketPrice', {}).get('raw'),
            'previousClose':         p.get('regularMarketPreviousClose', {}).get('raw'),
            'preMarketPrice':        p.get('preMarketPrice', {}).get('raw'),
            'preMarketChange':       p.get('preMarketChange', {}).get('raw'),
            'preMarketChangePct':    p.get('preMarketChangePercent', {}).get('raw'),
            'postMarketPrice':       p.get('postMarketPrice', {}).get('raw'),
            'postMarketChange':      p.get('postMarketChange', {}).get('raw'),
            'postMarketChangePct':   p.get('postMarketChangePercent', {}).get('raw'),
            'marketState':           p.get('marketState'),
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
