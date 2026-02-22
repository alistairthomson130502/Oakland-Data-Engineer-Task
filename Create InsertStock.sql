use [StockDB]
GO

CREATE PROCEDURE dbo.InsertStock
    @Symbol VARCHAR(10),
    @TradeDate DATETIME2,
    @OpenPrice DECIMAL(18,2),
    @HighPrice DECIMAL(18,2),
    @LowPrice DECIMAL(18,2),
    @ClosePrice DECIMAL(18,2),
    @Volume BIGINT
AS
BEGIN
    SET NOCOUNT ON;

         IF NOT EXISTS (
                SELECT 1 
                  FROM [StockDB].dbo.Stocks WITH (NOLOCK)
                 WHERE Symbol = @Symbol
                   AND TradeDate = @TradeDate
                       )

                 BEGIN
           INSERT INTO dbo.Stocks (Symbol, TradeDate, OpenPrice, HighPrice, LowPrice, ClosePrice, Volume)
                VALUES (@Symbol, @TradeDate, @OpenPrice, @HighPrice, @LowPrice, @ClosePrice, @Volume);
                   END

END;
GO