from flask import Flask, render_template_string
import requests
import pandas as pd
from typing import List
import os

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>암호화폐 투자 전략 분석기</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 40px; 
            background-color: #f0f2f5;
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .strategy-section {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            margin-top: 20px;
        }
        .coin-list {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
        }
        .coin-tag {
            background: #e9ecef;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 14px;
        }
        .returns-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        .returns-table th, .returns-table td {
            padding: 10px;
            border: 1px solid #dee2e6;
            text-align: center;
        }
        .returns-table th {
            background: #f1f3f5;
        }
        .positive-return {
            color: #28a745;
        }
        .negative-return {
            color: #dc3545;
        }
        h1 {
            color: #2c3e50;
            margin-bottom: 30px;
        }
        h2 {
            color: #34495e;
            margin-top: 25px;
        }
        .refresh-btn {
            display: inline-block;
            padding: 10px 20px;
            background-color: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin-top: 30px;
        }
        .refresh-btn:hover {
            background-color: #0056b3;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>암호화폐 투자 전략 분석기</h1>
        
        <div class="strategy-section">
            <h2>전략 A (추세추종)</h2>
            <p>모든 기간에서 상위 50위 안에 든 빗썸 거래 가능 코인들:</p>
            <div class="coin-list">
                {% for coin in strategy_a_coins %}
                    <span class="coin-tag">{{ coin }}</span>
                {% endfor %}
            </div>
        </div>

        <div class="strategy-section">
            <h2>전략 B (시총기준)</h2>
            <p>시가총액 상위 10위 코인들:</p>
            <div class="coin-list">
                {% for coin in strategy_b_coins %}
                    <span class="coin-tag">{{ coin }}</span>
                {% endfor %}
            </div>
        </div>

        <div class="strategy-section">
            <h2>전략별 수익률 분석</h2>
            {{ returns_html | safe }}
        </div>

        <a href="/" class="refresh-btn">새로고침</a>
    </div>
</body>
</html>
'''

def get_bithumb_symbols() -> set:
    try:
        # 빗썸 티커 API
        bithumb_url = "https://api.bithumb.com/public/ticker/ALL_KRW"
        response = requests.get(bithumb_url)
        data = response.json()
        
        if data['status'] == '0000':  # 성공 상태코드
            # 'data' 키에서 'date' 키를 제외한 모든 키(심볼)를 가져옴
            symbols = {symbol.upper() for symbol in data['data'].keys() if symbol != 'date'}
            return symbols
        return set()
    except Exception as e:
        print(f"빗썸 데이터 가져오기 실패: {e}")
        return set()

def get_crypto_ranking(time_period: str) -> pd.DataFrame:
    url = 'https://api.coingecko.com/api/v3/coins/markets'
    parameters = {
        'vs_currency': 'usd',
        'order': f'price_change_percentage_{time_period}_desc',
        'per_page': 100,
        'page': 1,
        'sparkline': False,
        'price_change_percentage': time_period
    }
    
    try:
        response = requests.get(url, params=parameters)
        data = response.json()
        
        if not isinstance(data, list):
            print(f"API 응답 형식 오류: {data}")
            return pd.DataFrame()
            
        crypto_data = []
        for coin in data:
            try:
                price_change_key = f'price_change_percentage_{time_period}'
                if isinstance(coin, dict) and price_change_key in coin:
                    crypto_data.append({
                        '순위': coin.get('market_cap_rank', 'N/A'),
                        '이름': coin.get('name', 'N/A'),
                        '심볼': coin.get('symbol', 'N/A').upper(),
                        '가격': coin.get('current_price', 0),
                        f'{time_period} 변동률': coin[price_change_key]
                    })
            except Exception as e:
                print(f"코인 데이터 처리 오류: {e}")
                continue
        
        df = pd.DataFrame(crypto_data)
        if not df.empty:
            df = df.sort_values(f'{time_period} 변동률', ascending=False)
        return df
    
    except Exception as e:
        print(f"API 요청 오류: {e}")
        return pd.DataFrame()

def get_top_10_by_market_cap() -> List[str]:
    url = 'https://api.coingecko.com/api/v3/coins/markets'
    parameters = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 100,
        'page': 1,
        'sparkline': False
    }
    
    try:
        response = requests.get(url, params=parameters)
        data = response.json()
        
        # 스테이블 코인 제외 리스트
        stablecoins = ['USDT', 'USDC', 'DAI', 'BUSD', 'TUSD', 'USDP', 'USDD']
        
        filtered_coins = []
        for coin in data:
            symbol = coin['symbol'].upper()
            if symbol not in stablecoins:
                filtered_coins.append(symbol)
        
        return filtered_coins[:10]
    
    except Exception as e:
        print(f"에러 발생: {e}")
        return []

def get_top_50_symbols(df: pd.DataFrame) -> List[str]:
    if df.empty:
        return []
    return df.head(50)['심볼'].tolist()

@app.route('/')
def home():
    time_periods = ['24h', '7d', '14d', '30d']
    rankings = {}
    top_50_by_period = {}

    # 빗썸 코인 목록 가져오기
    bithumb_coins = get_bithumb_symbols()
    print(f"빗썸 거래 가능 코인: {bithumb_coins}")  # 디버깅용

    for period in time_periods:
        rankings[period] = get_crypto_ranking(period)
        if not rankings[period].empty:
            top_50_by_period[period] = get_top_50_symbols(rankings[period])

    # 전략 A: 모든 기간에서 상위 50위 안에 든 코인들
    strategy_a_coins = set(top_50_by_period.get(time_periods[0], []))
    for period in time_periods[1:]:
        strategy_a_coins = strategy_a_coins.intersection(set(top_50_by_period.get(period, [])))
    
    # 빗썸에서 거래되는 코인만 필터링
    strategy_a_coins = strategy_a_coins.intersection(bithumb_coins)
    
    # 전략 B: 시가총액 상위 10위
    strategy_b_coins = get_top_10_by_market_cap()

    # 수익률 테이블 생성
    returns_html = '''
    <table class="returns-table">
        <tr>
            <th>전략</th>
    '''
    for period in time_periods:
        returns_html += f"<th>{period}</th>"
    returns_html += "</tr>"

    for strategy_name, strategy_coins in [
        ("전략 A", strategy_a_coins),
        ("전략 B", strategy_b_coins)
    ]:
        returns_html += f"<tr><td>{strategy_name}</td>"
        for period in time_periods:
            if not rankings[period].empty:
                total_return = 0
                valid_coins = 0
                for coin in strategy_coins:
                    df = rankings[period]
                    if coin in df['심볼'].values:
                        return_value = float(df[df['심볼'] == coin][f'{period} 변동률'])
                        total_return += return_value
                        valid_coins += 1
                if valid_coins > 0:
                    avg_return = total_return / valid_coins
                    color_class = 'positive-return' if avg_return > 0 else 'negative-return'
                    returns_html += f'<td class="{color_class}">{avg_return:.2f}%</td>'
                else:
                    returns_html += "<td>N/A</td>"
            else:
                returns_html += "<td>N/A</td>"
        returns_html += "</tr>"
    returns_html += "</table>"

    return render_template_string(
        HTML_TEMPLATE, 
        strategy_a_coins=sorted(list(strategy_a_coins)),
        strategy_b_coins=strategy_b_coins,
        returns_html=returns_html
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
