# Oakland-Data-Engineer-Task
Building a project to call APPL stock data, store in SQL Server, and then deploy using a local deployment.

## Architecture
- Python script fetches Apple stock data from Yahoo Finance (`yfinance`) in 1m intervals over the past 7 days. The data is then put into 5m bins for visual clarity in the figures described below. (Python 3.12.12 was used to create this project, so ensure that your version of Python is 3.12.12 or above.)
- Converts USD to GBP using latest exchange rate.
- Inserts **only new data** into SQL Server (`StockDB`).
- Generates:
  - **Figure 1:** Candlestick chart and Log Volume chart showing the last 6.5 trading hours (5-min bins, gaps removed) of data, Close Price (£) vs Date + Time. Title shows the Eastern Time value of the final data point in the final bin. Positive changes in Close Price are green, negatives are red.
  - **Figure 2:** Colored line chart for last 7 calendar days (5-min bins, gaps removed), Close Price (£) vs Date + Time. Title shows the Eastern Time value of the final data point in the final bin. Positive changes in Close Price are green, negatives are red. Grey        dashed lines for breaks within days.

    Yahoo Finance API (yfinance)
                  ↓
    Data Cleaning & Transformation
   (timezone normalization, GBP conversion)
                  ↓
       Duplicate Filtering Logic
   (compare against MAX(TradeDate))
                  ↓
        SQL Server (StockDB)
                  ↓
      Strict Time-Window Retrieval
       (Last 24h / Last 7 Days)
                  ↓
          Visualization Layer
       (mplfinance & matplotlib)

## What Works
- SQL Server integration
- Data ingestion and storage (avoids duplicates)
- Candlestick and line chart visualization
- Strict 7-day data range for line chart
- 5min interval bins, without including 'partial' bins. i.e. running the report at 12:27 ignores 12:25-12:27, as their bin is incomplete.
- For figure 2, grey dashed lines for breaks between trading days.

## Known Limitations / Future Improvements
- No live streaming; only batch ingestion. Attempted to update every 5 minutes but mplfinance created challenges. The blank data in-between caused NaN values to be read which errored out. Attempting to remove those after  each update caused data to be removed or for the figure to crash upon an update. Therefore, for "live" data the python script needs to be manually closed if open and then run every 5 minutes. Could use task scheduler to attempt to do this but I would prefer to do it within a SQL job and/or a front-end dashboard.
- Could add a frontend dashboard (e.g., Flask or Dash).
- Automation/CI-CD not yet implemented.
- Only the past 7 days are gathered as a maximum, due to yfinance being limited with 1m intervals of data over the last 7 days.
- Figure 1 is missing the same grey dashed line, attempting to create one caused the data to be offset. From what I could find, mplfinance maps the dates to integer positions and I couldn't find a way to map it to the       correct position, causing a chasm between the data and the x-axis labels.
- Ideally, multiple graphs could be selected by the user (similarly to yahoo's stocks website) so they could observe longer-term trends.
- Add logging, error handling, and retry logic for network/API issues.

## How to Run
1. Download everything in this github page if you haven't already.
2. Move everything into one known location. e.g. C:\Users\<your-username>\Documents\Projects\APPL_Stock_Project
3. Using VS Code, File -> Open Folder, select your folder from Step 2.
  3.1. Create a virtual environment using the command terminal (hotkey CTRL + ').
  3.2. Type 'cmd' in the terminal and then python -m venv venv. Then, venv\Scripts\activate. You should see (venv) C:\...\apple-stock-project>.
  3.3. Type pip install -r requirements.txt to install all required Python modules.
4. Ensure SQL Server is installed and that you can access your workplace's server.
  4.1. In SQL Server, run 'Create StockDB and dbo.Stocks table.sql'. This will be where the APPL stock data is stored.
  4.2. In SQL Server, run 'Create InsertStock.sql'. This will create the stored procedure in the StockDB database which the Python query inserts data gathered from yfinance into the StockDB.dbo.Stocks table.
  4.3. In SQL Server, run 'Create GetLatestStocks.sql'. This will select all the data from the StockDB.dbo.Stocks table. This is then filtered in the Python query to gather the 24hr and 7 day data. This is done in this      way to potentially allow for larger data ranges to be pulled, 1 month, 1 year, etc.
5. In the VS Code console, type 'python Import_and_Display_APPL_Stock_Data.py'. The console should then display:
   Fetching data...
   Converting to GBP...
   Inserting into SQL...
   Retrieving last 24 hours...
   Plotting...
6. Figures should display in 2 separate windows, the previous 6.5hr trading data in a candlestick chart and a log volume chart (Figure 1), and then all the trading data over the previous 7 days in a line chart (Figure 2).

- Alistair
https://github.com/alistairthomson130502
