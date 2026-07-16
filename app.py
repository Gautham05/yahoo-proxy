from flask import Flask, request, jsonify
from flask_cors import CORS
from curl_cffi import requests as cffi_requests

app = Flask(__name__)
CORS(app)

session = cffi_requests.Session(impersonate='chrome120')
CRUMB = None

FIELDS = ','.join([
    'regularMarketPrice','regularMarketChange','regularMarketChangePercent',
    'regularMarketPreviousClose',
    'preMarketPrice','preMarketChange','preMarketChangePercent','preMarketTime',
    'postMarketPrice','postMarketChange','postMarketChangePercent','postMarketTime',
    'overnightMarketPrice','overnightMarketChange','overnightMarketChangePercent','overnightMarketTime',
    'marketState'
])

def get_crumb():
    session.get('https://finance.yahoo.com', timeout=10)
    r = session.get('https://query1.finance.yahoo.com/v1/test/getcrumb', timeout=10)
    return r.text.strip()

def fetch_quotes(symbols):
    global CRUMB
    if not CRUMB:
        CRUMB = get_crumb()

    url = f'https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols}&fields={FIELDS}&crumb={CRUMB}&formatted=false&region=US&lang=en-US'
    r = session.get(url, timeout=10)
    data = r.json()

    # Crumb expired — refresh and retry once
    error = data.get('finance', {}).get('error') or data.get('quoteResponse', {}).get('error')
    if error:
        CRUMB = get_crumb()
        url = f'https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols}&fields={FIELDS}&crumb={CRUMB}&formatted=false&region=US&lang=en-US'
        r = session.get(url, timeout=10)
        data = r.json()

    return data.get('quoteResponse', {}).get('result', [])

@app.route('/quote')
def quote():
    tickers = [t.strip().upper() for t in request.args.get('tickers', '').split(',') if t.strip()]
    symbols = ','.join(tickers)

    try:
        quotes = fetch_quotes(symbols)
        result = {}
        for q in quotes:
            ticker = q.get('symbol')
            result[ticker] = {
                'marketState':              q.get('marketState'),
                'regularMarketPrice':       q.get('regularMarketPrice'),
                'previousClose':            q.get('regularMarketPreviousClose'),
                'preMarketPrice':           q.get('preMarketPrice'),
                'preMarketChange':          q.get('preMarketChange'),
                'preMarketChangePct':       q.get('preMarketChangePercent'),
                'postMarketPrice':          q.get('postMarketPrice'),
                'postMarketChange':         q.get('postMarketChange'),
                'postMarketChangePct':      q.get('postMarketChangePercent'),
                'overnightMarketPrice':     q.get('overnightMarketPrice'),
                'overnightMarketChange':    q.get('overnightMarketChange'),
                'overnightMarketChangePct': q.get('overnightMarketChangePercent'),
                'overnightMarketTime':      q.get('overnightMarketTime'),
            }
        return jsonify(result)

    except Exception as e:
        CRUMB = None  # reset crumb on error
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
