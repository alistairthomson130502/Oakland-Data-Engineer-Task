# ------------------ IMPORT PYTHON MODULES ------------------
import yfinance as yf
import pyodbc
import sys
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
from datetime import timedelta, time, datetime

SERVER = "localhost\\SQLEXPRESS" # -- Update with your actual server name if different
DATABASE = "StockDB" # -- Update with your actual database name if different

# ------------------ DB CONNECTION ------------------
def get_connection():
    try:
        return pyodbc.connect(
            "DRIVER={ODBC Driver 18 for SQL Server};"
            f"SERVER={SERVER};"
            f"DATABASE={DATABASE};"
            "Trusted_Connection=yes;"
            "Encrypt=no;"
        )
    except Exception as e:
        print("DB connection failed:", e)
        return None

# ------------------ FETCH DATA ------------------
def fetch_apple_data(days=7, interval="1m"):
    df = yf.Ticker("AAPL").history(period=f"{days}d", interval=interval)
    df.index = df.index.tz_localize(None)
    return df.sort_index()

# ------------------ USD → GBP ------------------ REMOVE THIS FUNCTION IF YOU WANT TO KEEP PRICES IN USD. 
# Note: The conversion uses the latest GBP/USD exchange rate, so the prices will reflect the most recent rate at the time you run the script. Currently, there is no historical exchange rate conversion for each row.
def convert_usd_to_gbp(df):
    fx = yf.Ticker("GBPUSD=X").history(period="7d")
    fx.index = fx.index.tz_localize(None)
    rate = fx["Close"].iloc[-1] if not fx.empty else 0.75
    df[["Open","High","Low","Close"]] = df[["Open","High","Low","Close"]] / rate
    return df

# ------------------ GET LAST TIMESTAMP ------------------
def get_last_trade_date():
    conn = get_connection()
    if not conn:
        return None
    cursor = conn.cursor()
    cursor.execute(f"SELECT MAX(TradeDate) FROM dbo.Stocks WHERE Symbol='AAPL'")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row[0] is not None else None

# ------------------ SQL INSERT (only new data) ------------------
def insert_stock_data(df):
    last_date = get_last_trade_date()
    if last_date is not None:
        last_date = pd.to_datetime(last_date)
        df = df[df.index > last_date]
    if df.empty:
        print("No new data to insert.")
        return
    conn = get_connection()
    if not conn:
        sys.exit()
    cursor = conn.cursor()
    for idx, row in df.iterrows():
        cursor.execute(
            "EXEC dbo.InsertStock ?, ?, ?, ?, ?, ?, ?",
            ("AAPL", idx.to_pydatetime(), float(row["Open"]), float(row["High"]),
             float(row["Low"]), float(row["Close"]), int(row["Volume"]))
        )
    conn.commit()
    conn.close()
    print(f"Inserted {len(df)} new rows.")

# ------------------ GET LAST 24H ------------------
def get_stock_data_last_24h():
    conn = get_connection()
    if not conn:
        sys.exit()
    cursor = conn.cursor()
    cursor.execute("EXEC dbo.GetLatestStocks")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame({
        "TradeDate": [r.TradeDate for r in rows],
        "Open": [r.OpenPrice for r in rows],
        "High": [r.HighPrice for r in rows],
        "Low": [r.LowPrice for r in rows],
        "Close": [r.ClosePrice for r in rows],
        "Volume": [r.Volume for r in rows]
    })
    df["TradeDate"] = pd.to_datetime(df["TradeDate"], errors="coerce")
    df = df.dropna().set_index("TradeDate")
    df.index = pd.to_datetime(df.index)
    df = df.astype({"Open": float, "High": float, "Low": float, "Close": float, "Volume": int})
    return df.sort_index()

# ------------------ GET LAST 7 DAYS (STRICT RANGE) ------------------
def get_stock_data_last_7days():
    conn = get_connection()
    if not conn:
        sys.exit()
    cursor = conn.cursor()
    cursor.execute("EXEC dbo.GetLatestStocks")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame({
        "TradeDate": [r.TradeDate for r in rows],
        "Open": [r.OpenPrice for r in rows],
        "High": [r.HighPrice for r in rows],
        "Low": [r.LowPrice for r in rows],
        "Close": [r.ClosePrice for r in rows],
        "Volume": [r.Volume for r in rows]
    })
    df["TradeDate"] = pd.to_datetime(df["TradeDate"], errors="coerce")
    df = df.dropna().set_index("TradeDate")
    df.index = pd.to_datetime(df.index)
    df = df.astype({"Open": float, "High": float, "Low": float, "Close": float, "Volume": int})

    now = df.index.max()
    start = now - timedelta(days=7)
    df = df[(df.index >= start) & (df.index <= now)]
    return df.sort_index()

# ------------------ HELPER: LAST N TRADING HOURS ------------------
def get_last_n_trading_hours(df, hours=6.5):
    df = df.sort_index()
    minutes_needed = int(hours * 60)
    df_rev = df.iloc[::-1]
    df_selected = []
    cum_minutes = 0
    prev_time = None
    for idx, row in df_rev.iterrows():
        if prev_time is not None:
            delta_minutes = (prev_time - idx).total_seconds() / 60
            if delta_minutes <= 60:
                cum_minutes += delta_minutes
        df_selected.append((idx, row))
        prev_time = idx
        if cum_minutes >= minutes_needed:
            break
    df_last_hours = pd.DataFrame([r for _, r in df_selected], index=[i for i, _ in df_selected])
    return df_last_hours.sort_index()

# ------------------ FIGURE 1: CANDLESTICK LAST 6.5 TRADING HOURS ------------------
def plot_candlestick_last_hours(df, hours=6.5):
    df = df.sort_index()
    minutes_per_bin = 5
    total_bins_needed = int(hours * 60 / minutes_per_bin)
    trading_days = df.index.normalize().unique()
    binned_rows = []
    cum_bins = 0

    for day in reversed(trading_days):
        day_start = pd.Timestamp.combine(day, time(9,30))
        day_end = pd.Timestamp.combine(day, time(16,0))
        df_day = df[(df.index >= day_start) & (df.index <= day_end)]
        if df_day.empty:
            continue

        last_time = df_day.index.max().replace(second=0, microsecond=0)
        remainder = last_time.minute % 5
        last_bin_end = last_time - pd.Timedelta(minutes=remainder) + pd.Timedelta(minutes=4)

        bin_starts = [last_bin_end - pd.Timedelta(minutes=minutes_per_bin-1) - pd.Timedelta(minutes=5*i)
                    for i in reversed(range(int(len(df_day)/minutes_per_bin)))]

        for bin_start in reversed(bin_starts):
            bin_end = bin_start + pd.Timedelta(minutes=minutes_per_bin-1)
            df_bin = df_day[(df_day.index >= bin_start) & (df_day.index <= bin_end)]
            if len(df_bin) == minutes_per_bin:
                binned_rows.append({
                    "Open": df_bin["Open"].iloc[0],
                    "High": df_bin["High"].max(),
                    "Low": df_bin["Low"].min(),
                    "Close": df_bin["Close"].iloc[-1],
                    "Volume": df_bin["Volume"].sum(),
                    "BinStart": bin_start
                })
                cum_bins += 1
                if cum_bins >= total_bins_needed:
                    break
        if cum_bins >= total_bins_needed:
            break

    df_binned = pd.DataFrame(binned_rows).set_index("BinStart").sort_index()
    mc = mpf.make_marketcolors(up='green', down='red', edge='inherit', wick='inherit', volume='in')
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle='-', y_on_right=False)

    fig, axes = mpf.plot(
        df_binned, type='candle', style=s, volume=True, volume_yscale='log',
        title="", ylabel="Close Price (£)", ylabel_lower="Volume (Log)", # -- Remember we converted to GBP earlier, so we update the label accordingly. If you removed the conversion function, change this back to "Close Price ($)".
        datetime_format="%d/%m %H:%M", xrotation=45,
        figscale=1.5, returnfig=True, tight_layout=False
    )

    fig.subplots_adjust(top=0.88, bottom=0.15)

    # Include the "as of" date/time in the title using end of final 5-min bin (as that is the last timestamp that reflects a complete 5-minute period)
    last_bin_end_for_title = df_binned.index.max() + pd.Timedelta(minutes=4)  # last bin covers 5 mins
    as_of = last_bin_end_for_title.strftime("%d/%m/%Y %H:%M")
    fig.suptitle(f"AAPL Candlestick + Log Volume (Last {hours} Trading Hours) as of {as_of} (ET)", # -- Eastern Time is the timezone of the NYSE where AAPL is traded, so we keep that in the title even if your local timezone is different.
             fontsize=16, fontweight='bold')

    fig.text(0.5, 0.02, "Date & Time", ha='center', fontsize=14, fontweight='bold')
    axes[0].set_ylabel("Close Price (£)", fontsize=14, fontweight='bold') # -- Remember we converted to GBP earlier, so we update the label accordingly. If you removed the conversion function, change this back to "Close Price ($)".
    axes[1].set_ylabel("Volume (Log)")
    fig.show()

# ------------------ FIGURE 2: COLORED LINE LAST 7 DAYS (5-min) ------------------
def plot_colored_line_7d_trading_labels(df, interval_minutes=5):
    if df.empty:
        print("No data to plot.")
        return

    df = df.sort_index()

    # STEP 1: Build STRICT 5-minute bins
    grouped = df.resample(f"{interval_minutes}min", label='left', closed='left')

    df_5m = grouped.agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum"
    })

    # Count rows per bin
    counts = grouped.size()

    # Keep only full bins (exactly 5 one-minute rows)
    df_5m = df_5m[counts == interval_minutes]

    if df_5m.empty:
        print("No full 5-minute bins found.")
        return

    df_5m = df_5m.dropna(subset=["Close"])

    # STEP 2: Plot continuous colored line 
    df_plot = df_5m.reset_index()
    df_plot = df_plot.rename(columns={df_plot.columns[0]: "DateTime"}) #-- After re-sampling, the datetime column is unnamed, so we rename it to "DateTime"
    x_cont = list(range(len(df_plot)))

    fig, ax = plt.subplots(figsize=(12,6))

    prev_x, prev_y = None, None
    for i, row in df_plot.iterrows():
        x, y = x_cont[i], row['Close']
        if prev_x is not None:
            color = 'green' if y >= prev_y else 'red'
            ax.plot([prev_x, x], [prev_y, y], color=color)
        prev_x, prev_y = x, y

    # STEP 3: Vertical lines for new trading days
    trading_days = df_plot['DateTime'].dt.date.unique()

    for day in trading_days:
        day_start = pd.Timestamp.combine(pd.Timestamp(day), time(9,30))
        idx = df_plot.index[df_plot['DateTime'] >= day_start]
        if not idx.empty:
            ax.axvline(x=idx[0], color='grey', linestyle='--', alpha=0.5)

    # STEP 4: Hourly x-axis labels
    tick_locs, tick_labels = [], []
    bins_per_hour = 60 // interval_minutes

    for i in range(0, len(df_plot), bins_per_hour):
        tick_locs.append(i)
        tick_labels.append(df_plot.loc[i, 'DateTime'].strftime("%d/%m %H:%M"))

    ax.set_xticks(tick_locs)
    ax.set_xticklabels(tick_labels, rotation=45)

    # STEP 5: Title timestamp = end of last FULL bin (not just last timestamp in DB)
    last_bin_end = df_5m.index.max() + pd.Timedelta(minutes=interval_minutes - 1)
    as_of = last_bin_end.strftime("%d/%m/%Y %H:%M")

    ax.set_title(
        f"AAPL Price (Past 7 Days) as of {as_of} (ET)", # -- Eastern Time is the timezone of the NYSE where AAPL is traded, so we keep that in the title even if your local timezone is different.
        fontsize=16,
        fontweight='bold'
    )

    ax.set_xlabel("Date & Time", fontsize=14, fontweight='bold')
    ax.set_ylabel("Close Price (£)", fontsize=14, fontweight='bold') # -- Remember we converted to GBP earlier, so we update the label accordingly. If you removed the conversion function, change this back to "Close Price ($)".
    ax.grid(True, linestyle='--', alpha=0.5)

    fig.tight_layout()
    plt.show()


# ------------------ MAIN SELECT ------------------
if __name__ == "__main__": # -- This ensures the code only runs when this script is executed directly, not when imported as a module
    print("Fetching data...")
    df_full = fetch_apple_data(days=7, interval="1m")  # Update the past 7 days worth of data using 1-minute intervals

    print("Inserting into SQL...")
    insert_stock_data(df_full)


    # Figure 1: Last 6.5 trading hours candlestick with log volume
    print("Retrieving last 24 hours for Figure 1...")
    df_24h = get_stock_data_last_24h()

    print("Converting to GBP for display...") # -- This is optional. If you want to keep prices in USD, simply comment out both this line and the next line, and update the y-axis labels in the plotting functions accordingly.
    df_24h = convert_usd_to_gbp(df_24h)

    print("Plotting candlestick (last 6.5 trading hours)...")
    plot_candlestick_last_hours(df_24h, hours=6.5)


    # Figure 2: Colored line over last 7 days with vertical lines for new trading days
    print("Retrieving last 7 days for Figure 2...")
    df_7d = get_stock_data_last_7days() 

    print("Converting to GBP for display...") # -- This is optional. If you want to keep prices in USD, simply comment out both this line and the next line, and update the y-axis labels in the plotting functions accordingly.
    df_7d = convert_usd_to_gbp(df_7d)

    print("Plotting colored line over last 7 days...")
    plot_colored_line_7d_trading_labels(df_7d, interval_minutes=5)
