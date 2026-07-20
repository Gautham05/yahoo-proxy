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


@app.route('/groww')
def groww():
    scheme_code = request.args.get('code')
    if not scheme_code:
        return jsonify({'error': 'code required'}), 400
    try:
        # Step 1 — find search_id
        search_id = None
        fund_house = None
        page = 0
        while page <= 40:
            r = session.get(
                f'https://groww.in/v1/api/search/v3/query/filter_derived_data/st_filter?available_for_investment=true&doc_type=scheme&index=false&page={page}&plan_type=Direct&size=100&sort_by=3',
                timeout=10
            )
            if r.text.startswith('<!DOCTYPE'):
                return jsonify({'error': 'Groww blocked', 'code': 'FILTER_BLOCKED'}), 503
            data = r.json()
            funds = data.get('content', [])
            if not funds: break
            match = next((f for f in funds if str(f.get('scheme_code')) == str(scheme_code)), None)
            if match:
                search_id = match['search_id']
                fund_house = match['fund_house']
                break
            page += 1

        if not search_id:
            return jsonify({'error': 'fund not found', 'code': 'NOT_FOUND'}), 404

        # Step 2 — fetch scheme data + stats in parallel
        import concurrent.futures
        def fetch_scheme():
            return session.get(f'https://groww.in/v1/api/data/mf/web/v6/scheme/search/{search_id}', timeout=10)
        def fetch_stats():
            return session.get(f'https://groww.in/v1/api/data/mf/web/v1/scheme/portfolio/{scheme_code}/stats', timeout=10)

        with concurrent.futures.ThreadPoolExecutor() as ex:
            f2, f3 = ex.submit(fetch_scheme), ex.submit(fetch_stats)
            r2, r3 = f2.result(), f3.result()

        if r2.text.startswith('<!DOCTYPE') or r3.text.startswith('<!DOCTYPE'):
            return jsonify({'error': 'Groww scheme blocked', 'code': 'SCHEME_BLOCKED'}), 503

        d  = r2.json()
        ps = r3.json()
        rs = d.get('return_stats', [{}])
        rs = rs[0] if isinstance(rs, list) else rs

        all_holdings   = d.get('holdings', [])
        equity_holdings = [{'company': h['company_name'], 'sector': h['sector_name'], 'corpus_per': h['corpus_per'], 'market_value': h['market_value']} for h in all_holdings if h.get('nature_name') == 'EQUITY']
        debt_holdings   = [{'company': h['company_name'], 'nature': h['nature_name'], 'sector': h['sector_name'], 'corpus_per': h['corpus_per'], 'rating': h.get('rating')} for h in all_holdings if h.get('nature_name') != 'EQUITY']

        return jsonify({
            'scheme_code': scheme_code, 'search_id': search_id, 'fund_house': fund_house,
            'equity_holdings': equity_holdings, 'debt_holdings': debt_holdings,
            'total_holdings_count': len(all_holdings),
            'sector': ps.get('equity_sector_per'), 'asset_allocation': ps.get('asset_allocation'),
            'large_cap': ps.get('large_cap'), 'mid_cap': ps.get('mid_cap'), 'small_cap': ps.get('small_cap'),
            'pe': ps.get('pe'), 'pb': ps.get('pb'), 'aum': ps.get('aum'),
            'portfolio_turnover': ps.get('portfolio_turnover'), 'total_holdings': ps.get('total_holdings'),
            'debt_per': ps.get('debt_per'), 'equity_per': ps.get('equity_per'), 'cash_per': ps.get('cash_per'),
            'return1y': rs.get('return1y'), 'return3y': rs.get('return3y'),
            'return5y': rs.get('return5y'), 'return10y': rs.get('return10y'),
            'cat_return1y': rs.get('cat_return1y'), 'cat_return3y': rs.get('cat_return3y'),
            'rank1y': rs.get('rank1yr'), 'rank3y': rs.get('rank3yr'), 'rank5y': rs.get('rank5yr'),
            'sharpe': rs.get('sharpe_ratio'), 'beta': rs.get('beta'),
            'alpha': rs.get('alpha'), 'std_dev': rs.get('standard_deviation'),
            'risk': rs.get('risk'), 'expense_ratio': d.get('expense_ratio'),
            'groww_rating': d.get('groww_rating'), 'exit_load': d.get('exit_load'),
            'benchmark': d.get('benchmark_name'), 'fund_manager': d.get('fund_manager'),
            'pros': [a['analysis_desc'] for a in d.get('analysis', []) if a.get('analysis_type') == 'PROS'],
            'cons': [a['analysis_desc'] for a in d.get('analysis', []) if a.get('analysis_type') == 'CONS'],
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
