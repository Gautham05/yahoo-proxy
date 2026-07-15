from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf

app = Flask(__name__)
CORS(app)

@app.route('/quote')
def quote():
    tickers = request.args.get('tickers', '').split(',')
    result = {}
    for ticker in tickers:
        ticker = ticker.strip().upper()
        if not ticker:
            continue
        try:
            t = yf.Ticker(ticker)
            info = t.fast_info
            result[ticker] = {
                'regularMarketPrice': info.last_price,
                'previousClose': info.previous_close,
                'preMarketPrice': getattr(info, 'pre_market_price', None),
                'postMarketPrice': getattr(info, 'post_market_price', None),
                'marketState': t.info.get('marketState', None),
            }
        except Exception as e:
            result[ticker] = {'error': str(e)}
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)