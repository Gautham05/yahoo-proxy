from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import time

app = Flask(__name__)
CORS(app)

@app.route('/quote')
def quote():
    tickers = request.args.get('tickers', '').split(',')
    tickers = [t.strip().upper() for t in tickers if t.strip()]
    result = {}

    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.info  # full info — has preMarketPrice, postMarketPrice
            result[ticker] = {
                'regularMarketPrice': info.get('regularMarketPrice') or info.get('currentPrice'),
                'previousClose':      info.get('regularMarketPreviousClose') or info.get('previousClose'),
                'preMarketPrice':     info.get('preMarketPrice'),
                'preMarketChange':    info.get('preMarketChange'),
                'preMarketChangePct': info.get('preMarketChangePercent'),
                'postMarketPrice':    info.get('postMarketPrice'),
                'postMarketChange':   info.get('postMarketChange'),
                'postMarketChangePct':info.get('postMarketChangePercent'),
                'marketState':        info.get('marketState'),
            }
            time.sleep(0.3)  # avoid rate limit
        except Exception as e:
            result[ticker] = {'error': str(e)}

    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
