CREATE DATABASE StockDB;

USE StockDB;

CREATE TABLE dbo.Stocks (
    Id INT IDENTITY PRIMARY KEY,
    Symbol NVARCHAR(10),
    TradeDate DATETIME,
    OpenPrice FLOAT,
    HighPrice FLOAT,
    LowPrice FLOAT,
    ClosePrice FLOAT,
    Volume BIGINT
);
