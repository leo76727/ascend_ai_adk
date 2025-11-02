-- create_financial_db.sql
DROP DATABASE IF EXISTS financial_services;
CREATE DATABASE financial_services;

\c financial_services;

-- Client table
CREATE TABLE Client (
    client_id VARCHAR(20) PRIMARY KEY,
    client_name VARCHAR(100) NOT NULL,
    client_account VARCHAR(20) UNIQUE NOT NULL
);

-- Underlyer table (single stock underliers)
CREATE TABLE Underlyer (
    underlyer_id VARCHAR(20) PRIMARY KEY,
    underlyer_type VARCHAR(10) NOT NULL CHECK (underlyer_type IN ('stock', 'index')),
    ticker VARCHAR(10) NOT NULL
);

-- Basket table (composed of multiple underliers)
CREATE TABLE Basket (
    basket_id VARCHAR(20),
    underlyer_id VARCHAR(20) NOT NULL,
    weight DECIMAL(5,4) NOT NULL CHECK (weight > 0 AND weight <= 1),
    PRIMARY KEY (basket_id, underlyer_id),
    FOREIGN KEY (underlyer_id) REFERENCES Underlyer(underlyer_id)
);

-- Product table
CREATE TABLE Product (
    product_id VARCHAR(20) PRIMARY KEY,
    isin VARCHAR(12) UNIQUE NOT NULL,
    underlyer_id VARCHAR(20),
    underlyer_type VARCHAR(10) NOT NULL CHECK (underlyer_type IN ('stock', 'basket')),
    basket_id VARCHAR(20),
    issue_date DATE NOT NULL,
    expiration_date DATE NOT NULL,
    payoff_type VARCHAR(20) NOT NULL CHECK (payoff_type IN ('autocall', 'reverse_convertible', 'capital_guaranteed', 'accumulator')),
    knock_in_level DECIMAL(8,4),
    knock_out_level DECIMAL(8,4),
    principal_protected BOOLEAN NOT NULL,
    FOREIGN KEY (underlyer_id) REFERENCES Underlyer(underlyer_id),
    CHECK (
        (underlyer_type = 'stock' AND underlyer_id IS NOT NULL AND basket_id IS NULL) OR
        (underlyer_type = 'basket' AND underlyer_id IS NULL AND basket_id IS NOT NULL)
    )
);

-- Quote table
CREATE TABLE Quote (
    quote_id VARCHAR(20) PRIMARY KEY,
    underlyer_id VARCHAR(20) NOT NULL,
    client_id VARCHAR(20) NOT NULL,
    quantity DECIMAL(15,2) NOT NULL,
    payoff_type VARCHAR(20) NOT NULL CHECK (payoff_type IN ('autocall', 'reverse_convertible', 'capital_guaranteed', 'accumulator')),
    price DECIMAL(10,4) NOT NULL,
    is_traded BOOLEAN NOT NULL DEFAULT FALSE,
    quote_date DATE NOT NULL,
    FOREIGN KEY (underlyer_id) REFERENCES Underlyer(underlyer_id),
    FOREIGN KEY (client_id) REFERENCES Client(client_id)
);

-- Position table
CREATE TABLE Position (
    position_id VARCHAR(20) PRIMARY KEY,
    isin VARCHAR(12) NOT NULL,
    quantity DECIMAL(15,2) NOT NULL,
    client_account VARCHAR(20) NOT NULL,
    expiration_date DATE,
    FOREIGN KEY (client_account) REFERENCES Client(client_account),
    FOREIGN KEY (isin) REFERENCES Product(isin)
);

-- Trade table
CREATE TABLE Trade (
    trade_id VARCHAR(20) PRIMARY KEY,
    isin VARCHAR(12) NOT NULL,
    quantity DECIMAL(15,2) NOT NULL,
    trade_type VARCHAR(4) NOT NULL CHECK (trade_type IN ('BUY', 'SELL')),
    client_account VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    settlement_date DATE NOT NULL,
    gross_credit DECIMAL(15,2),
    sales_person VARCHAR(50),
    trader VARCHAR(50),
    position_id VARCHAR(20),
    trader_charge DECIMAL(10,2),
    trade_price DECIMAL(10,4) NOT NULL,
    FOREIGN KEY (client_account) REFERENCES Client(client_account),
    FOREIGN KEY (position_id) REFERENCES Position(position_id),
    FOREIGN KEY (isin) REFERENCES Product(isin)
);

-- MTM table
CREATE TABLE MTM (
    isin VARCHAR(12) NOT NULL,
    trade_date DATE NOT NULL,
    trade_price DECIMAL(10,4) NOT NULL,
    mtm_price DECIMAL(10,4) NOT NULL,
    pnl DECIMAL(15,2) NOT NULL,
    PRIMARY KEY (isin, trade_date),
    FOREIGN KEY (isin) REFERENCES Product(isin)
);

-- Create indexes for better performance
CREATE INDEX idx_trade_client_account ON Trade(client_account);
CREATE INDEX idx_trade_date ON Trade(trade_date);
CREATE INDEX idx_position_client_account ON Position(client_account);
CREATE INDEX idx_mtm_date ON MTM(trade_date);
CREATE INDEX idx_product_underlyer ON Product(underlyer_id);
CREATE INDEX idx_product_basket ON Product(basket_id);
CREATE INDEX idx_quote_client ON Quote(client_id);
CREATE INDEX idx_quote_underlyer ON Quote(underlyer_id);
CREATE INDEX idx_quote_date ON Quote(quote_date);