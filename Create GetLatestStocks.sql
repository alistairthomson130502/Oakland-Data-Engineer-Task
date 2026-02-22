use [StockDB]
GO

CREATE PROCEDURE dbo.GetLatestStocks
AS
BEGIN
    SET NOCOUNT ON;
    
            SELECT *
              FROM dbo.Stocks
          ORDER BY TradeDate DESC;

END;
GO

