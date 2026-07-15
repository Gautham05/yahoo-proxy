from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
}

@app.route('/quote')
def quote():
    tickers = request.args.get('tickers', '').split(',')
    tickers = [t.strip().upper() for t in tickers if t.strip()]

    symbols = ','.join(tickers)
    url = f'https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols}&fields=regularMarketPrice,previousClose,preMarketPrice,preMarketChange,preMarketChangePercent,postMarketPrice,postMarketChange,postMarketChangePercent,marketState'

    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        data = res.json()
        quotes = data.get('quoteResponse', {}).get('result', [])

        result = {}
        for q in quotes:
            ticker = q.get('symbol')
            result[ticker] = {
                'regularMarketPrice':    q.get('regularMarketPrice'),
                'previousClose':         q.get('regularMarketPreviousClose'),
                'preMarketPrice':        q.get('preMarketPrice'),
                'preMarketChange':       q.get('preMarketChange'),
                'preMarketChangePct':    q.get('preMarketChangePercent'),
                'postMarketPrice':       q.get('postMarketPrice'),
                'postMarketChange':      q.get('postMarketChange'),
                'postMarketChangePct':   q.get('postMarketChangePercent'),
                'marketState':           q.get('marketState'),
            }

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
