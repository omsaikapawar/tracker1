from flask import Flask, render_template, jsonify, request, send_from_directory, Response
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import io
from datetime import datetime

app = Flask(__name__)

# CSV file paths
stock_categories = {
    "nifty50": "data/ind_nifty50list.csv",
    "nifty500": "data/ind_nifty500list.csv",
    "niftybank": "data/ind_niftybanklist.csv",
    "niftyit": "data/ind_niftyitlist.csv",
    "niftynext50": "data/ind_niftynext50list.csv"
}

def load_stock_symbols(category):
    df = pd.read_csv(stock_categories[category])
    return df["Symbol"].tolist()

# New helper: Load stock symbols with their Industry information
def load_stock_symbols_with_industry(category):
    df = pd.read_csv(stock_categories[category])
    return df[['Symbol', 'Industry']].to_dict(orient='records')

def fetch_stock_data(symbol):
    """
    Fetch stock details: Last Traded Price (LTP), Previous Close,
    All-Time High (ATH), All-Time Low (ATL), and the month (YYYY-MM)
    when ATH occurred.
    """
    try:
        formatted_symbol = symbol.strip().upper() + ".NS"
        stock = yf.Ticker(formatted_symbol)
        data = stock.history(period="5y")  # Use last 5 years for processing

        if not data.empty:
            ltp = round(data["Close"].iloc[-1], 2)
            prev_close = round(data["Close"].iloc[-2], 2)  # Previous closing price
            percent_change = round(((ltp - prev_close) / prev_close) * 100, 2)
            all_time_high = round(data["High"].max(), 2)
            all_time_low = round(data["Low"].min(), 2)
            high_date = data["High"].idxmax().strftime("%Y-%m")
            return {
                "symbol": symbol,
                "ltp": ltp,
                "prev_close": prev_close,
                "change": percent_change,
                "all_time_high": all_time_high,
                "all_time_low": all_time_low,
                "high_date": high_date
            }
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
    return None

# New helper: Fetch trading volume for the current day
def fetch_trading_volume(symbol):
    """
    Fetch the total trading volume of a stock for the current day.
    """
    try:
        formatted_symbol = symbol.strip().upper() + ".NS"
        stock = yf.Ticker(formatted_symbol)
        data = stock.history(period="1d")  # Fetch today's data
        if not data.empty:
            return data["Volume"].iloc[-1]
    except Exception as e:
        print(f"Error fetching trading volume for {symbol}: {e}")
    return 0

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/<category>')
def stock_page(category):
    if category in stock_categories:
        return render_template(f"{category}.html")
    return "404 Not Found", 404

@app.route('/stocks', methods=['GET'])
def get_stocks():
    category = request.args.get("category", "nifty500")
    user_date = request.args.get("date", "2024-01")

    if category in stock_categories:
        stock_list = load_stock_symbols(category)
    else:
        return jsonify({"error": "Invalid category"}), 400

    primary_results = []
    fallback_results = []

    for symbol in stock_list:
        result = fetch_stock_data(symbol)
        if result:
            if result["high_date"] >= user_date:
                primary_results.append(result)
            else:
                fallback_results.append(result)

    stock_data = primary_results if primary_results else fallback_results
    return jsonify(stock_data)

# Updated /sector-data route to show most traded stock sectors of the current day.
# If market is closed (i.e. no trading volume available for any stock), it returns a message.
@app.route('/sector-data')
def sector_data():
    sector_volumes = {}
    for category in stock_categories:
        stocks = load_stock_symbols_with_industry(category)
        for stock in stocks:
            industry = stock.get("Industry", "Unknown").strip()
            volume = fetch_trading_volume(stock["Symbol"])
            if industry in sector_volumes:
                sector_volumes[industry] += volume
            else:
                sector_volumes[industry] = volume
    # If total trading volume is zero, assume market is closed
    if sum(sector_volumes.values()) == 0:
        return jsonify({"market_closed": True})
    return jsonify(sector_volumes)

@app.route('/top-stocks')
def top_stocks():
    stocks = [fetch_stock_data(symbol) for symbol in load_stock_symbols("nifty50")]
    stocks = [s for s in stocks if s]

    gainers = [s for s in stocks if s["change"] > 0]
    losers = [s for s in stocks if s["change"] < 0]

    gainers.sort(key=lambda x: x["change"], reverse=True)
    losers.sort(key=lambda x: x["change"])

    return jsonify({"gainers": gainers, "losers": losers})

# New Route: Generate a normal graph using Matplotlib for stock price chart
@app.route('/stock-chart/<string:symbol>')
def stock_chart(symbol):
    symbol = symbol.strip().upper() + ".NS"
    ticker = yf.Ticker(symbol)
    # Fetch 6 months of history for the graph
    data = ticker.history(period="6mo")
    if data.empty:
        return "No data available", 404

    plt.figure(figsize=(8, 4))
    plt.plot(data.index, data["Close"], color="blue", label=f"{symbol} Price")
    plt.xlabel("Date")
    plt.ylabel("Price (INR)")
    plt.title(f"{symbol} Stock Price Chart")
    plt.legend()
    plt.grid(True)

    img = io.BytesIO()
    plt.savefig(img, format="png")
    img.seek(0)
    plt.close()
    return Response(img.getvalue(), mimetype="image/png")

@app.route('/stock-details/<string:symbol>')
def stock_details(symbol):
    """
    Advanced stock details route.
    Fetches basic stock data plus intraday (1-day, 15-minute interval) data for charting.
    Also retrieves additional info: Open, Market Cap, P/E Ratio, Dividend Yield,
    52-Week High, and 52-Week Low.
    """
    symbol = symbol.strip().upper()
    stock_info = fetch_stock_data(symbol)
    if not stock_info:
        return "Stock not found or no data available", 404

    full_symbol = symbol + ".NS"
    ticker = yf.Ticker(full_symbol)
    
    # Fetch intraday data for charting (not used for our normal graph)
    intraday = ticker.history(period="1d", interval="15m")
    if not intraday.empty:
        chart_time = intraday.index.strftime("%H:%M").tolist()
        chart_prices = [round(p, 2) for p in intraday["Close"].tolist()]
    else:
        chart_time, chart_prices = [], []

    # Retrieve additional info from ticker.info
    info = ticker.info
    open_price = info.get("open", "N/A")
    market_cap = info.get("marketCap", "N/A")
    if market_cap != "N/A":
        market_cap = round(market_cap / 1e7, 2)
    pe_ratio = info.get("trailingPE", "N/A")
    div_yield = info.get("dividendYield", "N/A")
    wk52_high = info.get("fiftyTwoWeekHigh", "N/A")
    wk52_low = info.get("fiftyTwoWeekLow", "N/A")

    return render_template("stock_details.html",
                           stock=stock_info,
                           prev_close=stock_info.get("prev_close", "N/A"),
                           chart_time=chart_time,
                           chart_prices=chart_prices,
                           open_price=open_price,
                           market_cap=market_cap,
                           pe_ratio=pe_ratio,
                           div_yield=div_yield,
                           wk52_high=wk52_high,
                           wk52_low=wk52_low)

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True)
