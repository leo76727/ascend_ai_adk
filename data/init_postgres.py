# generate_financial_data.py
import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import psycopg2
from sqlalchemy import create_engine, text
import random
import os

fake = Faker()

class FinancialDataGenerator:
    def __init__(self):
        self.stock_universe = [
            {'ticker': 'SPX', 'type': 'index', 'name': 'S&P 500 Index'},
            {'ticker': 'NDX', 'type': 'index', 'name': 'Nasdaq 100 Index'},
            {'ticker': 'TSLA', 'type': 'stock', 'name': 'Tesla Inc'},
            {'ticker': 'AAPL', 'type': 'stock', 'name': 'Apple Inc'},
            {'ticker': 'MSFT', 'type': 'stock', 'name': 'Microsoft Corp'},
            {'ticker': 'NVDA', 'type': 'stock', 'name': 'NVIDIA Corp'},
            {'ticker': 'BABA', 'type': 'stock', 'name': 'Alibaba Group'}
        ]
        self.payoff_types = ['autocall', 'reverse_convertible', 'capital_guaranteed', 'accumulator']
        self.sales_people = [fake.name() for _ in range(50)]
        self.traders = [fake.name() for _ in range(30)]
        self.isins = []  # Will be generated with products
        
    def recreate_database(self, engine, db_config):
        """Drop and recreate the entire database"""
        print("Recreating database...")
        
        # Connect to postgres database to drop/create our database
        conn_str = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/postgres"
        admin_engine = create_engine(conn_str)
        
        with admin_engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT")
            
            # Terminate existing connections
            conn.execute(text(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{db_config['database']}'
                AND pid <> pg_backend_pid();
            """))
            
            # Drop and recreate database
            conn.execute(text(f"DROP DATABASE IF EXISTS {db_config['database']}"))
            conn.execute(text(f"CREATE DATABASE {db_config['database']}"))
        
        print("Database recreated successfully!")
        
    def execute_sql_file(self, engine, file_path):
        """Execute SQL file to create tables"""
        print(f"Executing SQL file: {file_path}")
        
        with open(file_path, 'r') as file:
            sql_commands = file.read()
            
        # Split by semicolon and execute each command
        commands = sql_commands.split(';')
        
        with engine.connect() as conn:
            for command in commands:
                command = command.strip()
                if command:
                    try:
                        conn.execute(text(command))
                    except Exception as e:
                        print(f"Error executing command: {e}")
                        continue
        
        print("SQL file executed successfully!")
    
    def generate_underlyers(self):
        """Generate underlyer data"""
        underlyers = []
        for i, stock in enumerate(self.stock_universe):
            underlyer_id = f"UND{str(i+1).zfill(5)}"
            underlyers.append({
                'underlyer_id': underlyer_id,
                'underlyer_type': stock['type'],
                'ticker': stock['ticker']
            })
        return pd.DataFrame(underlyers)
    
    def generate_baskets(self, underlyers_df, num_baskets=100):
        """Generate basket data - each basket contains 2-3 underlyers"""
        baskets = []
        underlyer_ids = underlyers_df['underlyer_id'].tolist()
        
        for basket_num in range(num_baskets):
            basket_id = f"BASK{str(basket_num+1).zfill(5)}"
            
            # Randomly select 2-3 underlyers for this basket
            num_underlyers = random.randint(2, 3)
            selected_underlyers = random.sample(underlyer_ids, num_underlyers)
            
            # Generate weights that sum to 1.0
            weights = [random.uniform(0.2, 0.6) for _ in range(num_underlyers)]
            total_weight = sum(weights)
            normalized_weights = [w/total_weight for w in weights]
            
            for i, underlyer_id in enumerate(selected_underlyers):
                baskets.append({
                    'basket_id': basket_id,
                    'underlyer_id': underlyer_id,
                    'weight': round(normalized_weights[i], 4)
                })
                
        return pd.DataFrame(baskets)
    
    def generate_isin(self):
        """Generate a valid ISIN code"""
        country = "US"
        identifier = ''.join([str(random.randint(0, 9)) for _ in range(9)])
        check_digit = str(random.randint(0, 9))
        return f"{country}{identifier}{check_digit}"
    
    def generate_products(self, underlyers_df, baskets_df, num_products=500):
        """Generate product data - 80% stock, 20% basket"""
        products = []
        underlyer_ids = underlyers_df['underlyer_id'].tolist()
        basket_ids = list(baskets_df['basket_id'].unique())
        
        # Ensure we have enough basket IDs for 20% of products
        num_basket_products = int(num_products * 0.2)
        num_stock_products = num_products - num_basket_products
        
        used_isins = set()
        
        # Generate stock products (80%)
        for i in range(num_stock_products):
            product_id = f"PROD{str(i+1).zfill(6)}"
            
            # Generate unique ISIN
            while True:
                isin = self.generate_isin()
                if isin not in used_isins:
                    used_isins.add(isin)
                    break
            
            underlyer_id = random.choice(underlyer_ids)
            underlyer_type = 'stock'
            basket_id = None
            
            # Product dates
            issue_date = fake.date_between(start_date='-5y', end_date='today')
            expiration_date = issue_date + timedelta(days=random.randint(180, 1825))  # 6 months to 5 years
            
            payoff_type = random.choice(self.payoff_types)
            
            # Generate product-specific parameters
            knock_in_level = round(random.uniform(0.6, 0.8), 4) if random.random() < 0.7 else None
            knock_out_level = round(random.uniform(1.1, 1.3), 4) if random.random() < 0.5 else None
            principal_protected = random.random() < 0.4  # 40% are principal protected
            
            products.append({
                'product_id': product_id,
                'isin': isin,
                'underlyer_id': underlyer_id,
                'underlyer_type': underlyer_type,
                'basket_id': basket_id,
                'issue_date': issue_date,
                'expiration_date': expiration_date,
                'payoff_type': payoff_type,
                'knock_in_level': knock_in_level,
                'knock_out_level': knock_out_level,
                'principal_protected': principal_protected
            })
        
        # Generate basket products (20%)
        for i in range(num_basket_products):
            product_id = f"PROD{str(num_stock_products + i + 1).zfill(6)}"
            
            # Generate unique ISIN
            while True:
                isin = self.generate_isin()
                if isin not in used_isins:
                    used_isins.add(isin)
                    break
            
            underlyer_id = None
            underlyer_type = 'basket'
            basket_id = random.choice(basket_ids)
            
            # Product dates
            issue_date = fake.date_between(start_date='-5y', end_date='today')
            expiration_date = issue_date + timedelta(days=random.randint(180, 1825))
            
            payoff_type = random.choice(self.payoff_types)
            
            # Basket products often have different parameters
            knock_in_level = round(random.uniform(0.7, 0.85), 4) if random.random() < 0.8 else None
            knock_out_level = round(random.uniform(1.05, 1.2), 4) if random.random() < 0.6 else None
            principal_protected = random.random() < 0.3  # 30% are principal protected
            
            products.append({
                'product_id': product_id,
                'isin': isin,
                'underlyer_id': underlyer_id,
                'underlyer_type': underlyer_type,
                'basket_id': basket_id,
                'issue_date': issue_date,
                'expiration_date': expiration_date,
                'payoff_type': payoff_type,
                'knock_in_level': knock_in_level,
                'knock_out_level': knock_out_level,
                'principal_protected': principal_protected
            })
            
        self.isins = [p['isin'] for p in products]  # Store ISINs for other tables
        return pd.DataFrame(products)
    
    def generate_quotes(self, underlyers_df, clients_df, num_quotes=200000):
        """Generate quote data"""
        quotes = []
        underlyer_ids = underlyers_df['underlyer_id'].tolist()
        client_ids = clients_df['client_id'].tolist()
        
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2025, 11, 1)
        
        for i in range(num_quotes):
            quote_id = f"QUOTE{str(i+1).zfill(8)}"
            underlyer_id = random.choice(underlyer_ids)
            client_id = random.choice(client_ids)
            quantity = round(random.uniform(1000, 50000), 2)
            payoff_type = random.choice(self.payoff_types)
            price = round(random.uniform(50, 500), 4)
            is_traded = random.random() < 0.3  # 30% of quotes result in trades
            quote_date = fake.date_between(start_date=start_date, end_date=end_date)
            
            quotes.append({
                'quote_id': quote_id,
                'underlyer_id': underlyer_id,
                'client_id': client_id,
                'quantity': quantity,
                'payoff_type': payoff_type,
                'price': price,
                'is_traded': is_traded,
                'quote_date': quote_date
            })
            
            if i % 10000 == 0:
                print(f"Generated {i} quotes...")
                
        return pd.DataFrame(quotes)
    
    def generate_clients(self, num_clients=10000):
        """Generate client data"""
        clients = []
        for i in range(num_clients):
            client_id = f"C{str(i+1).zfill(8)}"
            client_name = fake.company()
            client_account = f"ACC{str(i+1).zfill(8)}"
            clients.append({
                'client_id': client_id,
                'client_name': client_name,
                'client_account': client_account
            })
        return pd.DataFrame(clients)
    
    def generate_positions(self, clients_df, products_df, num_positions=10000):
        """Generate position data"""
        positions = []
        client_accounts = clients_df['client_account'].tolist()
        product_isins = products_df['isin'].tolist()
        print(f"Generating {num_positions} positions...")
        for i in range(num_positions):
            position_id = f"POS{str(i+1).zfill(8)}"
            isin = random.choice(product_isins)
            quantity = round(random.uniform(1000, 10000), 2)
            client_account = random.choice(client_accounts)
            
            # Get product expiration date to ensure position expiration is reasonable
            product_expiry = products_df[products_df['isin'] == isin]['expiration_date'].iloc[0]
            
            # 30% of positions have expiration dates (before product expiry)
            expiration_date = product_expiry
                
            positions.append({
                'position_id': position_id,
                'isin': isin,
                'quantity': quantity,
                'client_account': client_account,
                'expiration_date': expiration_date
            })
            
            if i % 10000 == 0:
                print(f"Generated {i} positions...")
                
        return pd.DataFrame(positions)
    
    def generate_trades(self, clients_df, positions_df, products_df, num_trades=10000):
        """Generate trade data"""
        trades = []
        client_accounts = clients_df['client_account'].tolist()
        positions_dict = positions_df.set_index('position_id').to_dict('index')
        position_ids = list(positions_dict.keys())
        product_isins = products_df['isin'].tolist()
        
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2025, 11, 1)
        
        for i in range(num_trades):
            trade_id = f"TRD{str(i+1).zfill(8)}"
            isin = random.choice(product_isins)
            quantity = round(random.uniform(100, 50000), 2)
            trade_type = random.choice(['BUY', 'SELL'])
            client_account = random.choice(client_accounts)
            
            # Ensure trade date is after product issue date
            product_issue_date = products_df[products_df['isin'] == isin]['issue_date'].iloc[0]
            min_trade_date = max(start_date.date(), product_issue_date)
            
            if(min_trade_date >= end_date.date()):
                min_trade_date = end_date.date() - timedelta(days=60)
                        
            trade_date = fake.date_between(start_date=min_trade_date, end_date=end_date.date())
            settlement_date = trade_date + timedelta(days=random.randint(1, 5))
            
            gross_credit = round(random.uniform(1000, 1000000), 2) if random.random() < 0.7 else None
            sales_person = random.choice(self.sales_people)
            trader = random.choice(self.traders)
            position_id = random.choice(position_ids) if random.random() < 0.8 else None
            
            trader_charge = round(random.uniform(10, 5000), 2)
            
            # Trade price based on product type and characteristics
            base_price = random.uniform(50, 500)
            trade_price = round(base_price, 4)
            
            trades.append({
                'trade_id': trade_id,
                'isin': isin,
                'quantity': quantity,
                'trade_type': trade_type,
                'client_account': client_account,
                'trade_date': trade_date,
                'settlement_date': settlement_date,
                'gross_credit': gross_credit,
                'sales_person': sales_person,
                'trader': trader,
                'position_id': position_id,
                'trader_charge': trader_charge,
                'trade_price': trade_price
            })
            
            if i % 10000 == 0:
                print(f"Generated {i} trades...")
                
        return pd.DataFrame(trades)
    
    def generate_mtm_advanced(self, products_df, trades_df, start_date='2020-01-01', end_date='2025-11-01'):
        """Generate daily MTM data with more realistic market behavior"""
        mtm_data = []
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Get all trading dates
        all_dates = pd.date_range(start=start_date, end=end_date, freq='B').date
        #all_dates = [date.date() for date in all_dates]
        
        # Group trades by ISIN
        product_first_trade = trades_df.groupby('isin')['trade_date'].min().to_dict()
        
        # Market regime simulation
        market_regimes = self.simulate_market_regimes(all_dates)
        
        print("Generating realistic daily MTM records...")
        
        for isin in products_df['isin'].unique():
            product_info = products_df[products_df['isin'] == isin].iloc[0]
            first_trade_date = product_first_trade.get(isin, product_info['issue_date'])
            product_start_date = max(first_trade_date, product_info['issue_date'])
            
            product_dates = [date for date in all_dates if date >= product_start_date and date <= end_date]
            
            if not product_dates:
                continue
                
            # Product-specific characteristics
            base_price = random.uniform(50, 500)
            volatility = random.uniform(0.1, 0.3)  # Annual volatility
            drift = random.uniform(-0.1, 0.1)  # Annual drift
            
            current_price = base_price
            price_series = []
            
            # Generate price series using geometric brownian motion
            for i, trade_date in enumerate(product_dates):
                if i == 0:
                    price = base_price
                else:
                    # Time increment (1 day = 1/252 years)
                    dt = 1/252
                    
                    # Market regime impact
                    regime = market_regimes[trade_date]
                    regime_impact = self.get_regime_impact(regime)
                    
                    # Random shock
                    shock = random.gauss(0, 1)
                    
                    # Price movement using GBM
                    price_move = (drift * dt + 
                                volatility * np.sqrt(dt) * shock + 
                                regime_impact * dt)
                    
                    price = current_price * (1 + price_move)
                    
                    # Ensure reasonable price bounds
                    price = max(10, min(1000, price))
                
                price_series.append(round(price, 4))
                current_price = price
            
            # Generate MTM records from price series
            for i, (trade_date, mtm_price) in enumerate(zip(product_dates, price_series)):
                # Trade price is previous day's MTM (except first day)
                if i == 0:
                    trade_price = round(mtm_price * random.uniform(0.98, 1.02), 4)
                else:
                    trade_price = price_series[i-1]
                
                # Calculate P&L
                # Use actual traded quantities if available, otherwise use notional
                product_trades_for_isin = trades_df[trades_df['isin'] == isin]
                if not product_trades_for_isin.empty:
                    # Use average quantity for P&L calculation
                    avg_quantity = product_trades_for_isin['quantity'].mean()
                else:
                    avg_quantity = random.uniform(1000, 10000)
                
                price_change = mtm_price - trade_price
                pnl = round(price_change * avg_quantity, 2)
                
                mtm_data.append({
                    'isin': isin,
                    'trade_date': trade_date,
                    'trade_price': trade_price,
                    'mtm_price': mtm_price,
                    'pnl': pnl
                })
            
            if len(mtm_data) % 10000 == 0:
                print(f"Generated {len(mtm_data)} MTM records...")
        
        return pd.DataFrame(mtm_data)

    def simulate_market_regimes(self, dates):
        """Simulate different market regimes (bull, bear, volatile, calm)"""
        regimes = {}
        current_regime = 'normal'
        regime_duration = 0
        
        for date in dates:
            # Change regime with some probability
            if regime_duration <= 0 or random.random() < 0.005:  # 0.5% chance to change regime daily
                current_regime = random.choice(['bull', 'bear', 'volatile', 'calm', 'normal'])
                regime_duration = random.randint(30, 180)  # 1-6 months
            
            regimes[date] = current_regime
            regime_duration -= 1
        
        return regimes

    def get_regime_impact(self, regime):
        """Get price impact multiplier for different market regimes"""
        impacts = {
            'bull': 0.001,      # Slight upward pressure
            'bear': -0.001,     # Slight downward pressure  
            'volatile': 0.0,    # No drift, but higher volatility
            'calm': 0.0002,     # Very slight upward drift
            'normal': 0.0005    # Normal slight upward drift
        }
        return impacts.get(regime, 0.0)

def main():
    # Database configuration
    db_config = {
        'host': 'localhost',
        'port': 11000,
        'database': 'financial_services',
        'user': 'postgres',  # Change to your PostgreSQL username
        'password': 'admin123'  # Change to your PostgreSQL password
    }
    
    # Initialize generator
    generator = FinancialDataGenerator()
    
    # Recreate database
    generator.recreate_database(None, db_config)
    
    # Create engine for the new database
    engine = create_engine(f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}")
    
    # Execute SQL file to create tables
    generator.execute_sql_file(engine, 'create_financial_db.sql')
    
    print("Starting data generation...")
    
    # Generate data in the correct order to respect foreign key constraints
    print("Generating underlyers...")
    underlyers_df = generator.generate_underlyers()
    underlyers_df.to_sql('underlyer', engine, if_exists='append', index=False)
    
    print("Generating clients...")
    clients_df = generator.generate_clients(10000)
    clients_df.to_sql('client', engine, if_exists='append', index=False)
    
    print("Generating baskets...")
    baskets_df = generator.generate_baskets(underlyers_df, 100)
    baskets_df.to_sql('basket', engine, if_exists='append', index=False)
    
    print("Generating products...")
    products_df = generator.generate_products(underlyers_df, baskets_df, 500)
    products_df.to_sql('product', engine, if_exists='append', index=False)
    
    print("Generating quotes...")
    quotes_df = generator.generate_quotes(underlyers_df, clients_df, 200000)  # 200K quotes
    quotes_df.to_sql('quote', engine, if_exists='append', index=False)
    
    print("Generating positions...")
    positions_df = generator.generate_positions(clients_df, products_df, 10000)
    positions_df.to_sql('position', engine, if_exists='append', index=False)
    
    print("Generating trades...")
    trades_df = generator.generate_trades(clients_df, positions_df, products_df, 10000)
    trades_df.to_sql('trade', engine, if_exists='append', index=False)
    
    print("Generating MTM data...")
    mtm_df = generator.generate_mtm_advanced(products_df, trades_df, '2020-01-01', '2024-12-31')
    mtm_df.to_sql('mtm', engine, if_exists='append', index=False)
    
    print("Data generation completed!")
    
    # Print summary statistics
    print("\n=== Data Generation Summary ===")
    print(f"Underlyers: {len(underlyers_df)}")
    print(f"Baskets: {len(baskets_df['basket_id'].unique())}")
    print(f"Products: {len(products_df)}")
    print(f"Clients: {len(clients_df)}")
    print(f"Quotes: {len(quotes_df)}")
    print(f"Positions: {len(positions_df)}")
    print(f"Trades: {len(trades_df)}")
    print(f"MTM Records: {len(mtm_df)}")
    
    # Product type distribution
    stock_products = len(products_df[products_df['underlyer_type'] == 'stock'])
    basket_products = len(products_df[products_df['underlyer_type'] == 'basket'])
    print(f"\nProduct Distribution:")
    print(f"  Stock products: {stock_products} ({stock_products/len(products_df)*100:.1f}%)")
    print(f"  Basket products: {basket_products} ({basket_products/len(products_df)*100:.1f}%)")
    
    # Quote statistics
    traded_quotes = len(quotes_df[quotes_df['is_traded'] == True])
    print(f"\nQuote Statistics:")
    print(f"  Traded quotes: {traded_quotes} ({traded_quotes/len(quotes_df)*100:.1f}%)")
    print(f"  Non-traded quotes: {len(quotes_df) - traded_quotes} ({(len(quotes_df) - traded_quotes)/len(quotes_df)*100:.1f}%)")

if __name__ == "__main__":
    main()