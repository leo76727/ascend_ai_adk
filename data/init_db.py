import sqlite3
import random
import datetime
import os
import json


DB_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, 'positions.db')

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Drop old tables for a clean seed (ok for demo/test environments)
tables = ['positions', 'clients', 'trades', 'product', 'quote', 'market']
for t in tables:
    cur.execute(f"DROP TABLE IF EXISTS {t}")

# Create tables with the requested columns
cur.execute(
    """
    CREATE TABLE client (
        client_id TEXT PRIMARY KEY,
        client_name TEXT,
        client_account TEXT,
        client_address TEXT
    )
    """
)

cur.execute(
    """
    CREATE TABLE product (
        product_id TEXT PRIMARY KEY,
        product_description TEXT,
        payoff_type TEXT,
        issue_date TEXT,
        expiration_date TEXT,
        issuer TEXT,
        underlyer_stocks TEXT,
        co_issuers TEXT,
        issue_price REAL,
        issue_size INTEGER,
        strike REAL,
        coupon REAL,
        barrier_type TEXT,
        currency TEXT,
        notional REAL
    )
    """
)

cur.execute(
    """
    CREATE TABLE positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id TEXT,
        product_id TEXT,
        quantity INTEGER,
        original_price REAL,
        expiration_date TEXT,
        current_price REAL,
        notional REAL,
        strike REAL,
        coupon REAL,
        currency TEXT
    )
    """
)

cur.execute(
    """
    CREATE TABLE trades (
        trade_id TEXT PRIMARY KEY,
        client_account TEXT,
        product_id TEXT,
        quantity INTEGER,
        trade_type TEXT,
        trade_price REAL,
        trade_date TEXT,
        settlement_date TEXT,
        notional REAL,
        currency TEXT
    )
    """
)

cur.execute(
    """
    CREATE TABLE quote (
        quote_id TEXT PRIMARY KEY,
        client_id TEXT,
        payoff_type TEXT,
        issue_date TEXT,
        expiration_date TEXT,
        issuer TEXT,
        underlyer_stocks TEXT,
        barrier_level REAL,
        gross_credit_level REAL,
        barrier_type TEXT,
        strike REAL,
        currency TEXT
    )
    """
)

cur.execute(
    """
    CREATE TABLE market (
        product_id TEXT PRIMARY KEY,
        product_description TEXT,
        payoff_type TEXT,
        issue_date TEXT,
        expiration_date TEXT,
        issuer TEXT,
        underlyer_stocks TEXT,
        co_issuers TEXT,
        issue_price REAL,
        issue_size INTEGER,
        strike REAL,
        coupon REAL,
        barrier_type TEXT,
        currency TEXT,
        notional REAL,
        estimate_client REAL
    )
    """
)

# Seed data
issuers = ['Bank A', 'Bank B', 'Issuer X']
underlyers = ['AAPL', 'MSFT', 'GOOG', 'TSLA', 'AMZN']
payoffs = ['Barrier', 'Digital', 'Vanilla', 'Range', 'Cliquet']

# Clients
clients = []
for i in range(1, 6):
    cid = f"C{i:03d}"
    client_name = f"Client {i} Ltd"
    account = f"ACCT{i:04d}"
    address = f"{i} Market St, City {i}"
    clients.append(cid)
    cur.execute("INSERT INTO client (client_id, client_name, client_account, client_address) VALUES (?, ?, ?, ?)",
                (cid, client_name, account, address))

# Products and market
products = []
today = datetime.date.today()
for i in range(1, 11):
    pid = f"P{i:04d}"
    desc = f"Structured Note {i} on {random.choice(underlyers)}"
    payoff = random.choice(payoffs)
    issue_date = today - datetime.timedelta(days=random.randint(30, 365))
    expiry = issue_date + datetime.timedelta(days=random.randint(30, 720))
    issuer = random.choice(issuers)
    # create a basket of 1-3 underlyers to simulate multi-underlyer products
    num_under = random.choices([1,2,3], weights=[60,30,10])[0]
    under_list = random.sample(underlyers, k=num_under)
    under = ",".join(under_list)
    # create potential co-issuers list (0-2 extra issuers)
    co_count = random.choices([0,1,2], weights=[70,20,10])[0]
    co_list = random.sample(issuers, k=co_count) if co_count > 0 else []
    issue_price = round(random.uniform(90, 110), 2)
    issue_size = random.randint(1000, 10000)
    # realistic product attributes
    strike = round(issue_price * random.uniform(0.8, 1.2), 2)
    coupon = round(random.choice([0.0, 0.01, 0.02, 0.03, 0.05, 0.06, 0.08, 0.10]), 4)
    barrier_type = random.choice(['None', 'Up-and-Out', 'Down-and-In', 'Up-and-In', 'Down-and-Out']) if payoff == 'Barrier' else 'None'
    currency = random.choice(['USD', 'EUR', 'GBP'])
    notional = round(issue_price * issue_size, 2)
    products.append(pid)
    cur.execute("INSERT INTO product (product_id, product_description, payoff_type, issue_date, expiration_date, issuer, underlyer_stocks, co_issuers, issue_price, issue_size, strike, coupon, barrier_type, currency, notional) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (pid, desc, payoff, issue_date.isoformat(), expiry.isoformat(), issuer, under, json.dumps(co_list), issue_price, issue_size, strike, coupon, barrier_type, currency, notional))
    # market record
    estimate_client = round(random.uniform(0.0, 1.0), 4)
    cur.execute("INSERT INTO market (product_id, product_description, payoff_type, issue_date, expiration_date, issuer, underlyer_stocks, co_issuers, issue_price, issue_size, strike, coupon, barrier_type, currency, notional, estimate_client) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (pid, desc, payoff, issue_date.isoformat(), expiry.isoformat(), issuer, under, json.dumps(co_list), issue_price, issue_size, strike, coupon, barrier_type, currency, notional, estimate_client))

# Positions: link clients to products
for _ in range(80):
    cid = random.choice(clients)
    pid = random.choice(products)
    qty = random.randint(1, 500)
    # original price near issue price
    cur.execute("SELECT issue_price, expiration_date FROM product WHERE product_id = ?", (pid,))
    row = cur.fetchone()
    if row:
        orig_price = float(row[0]) if row[0] is not None else round(random.uniform(90, 110), 2)
        exp = row[1]
    else:
        orig_price = round(random.uniform(90, 110), 2)
        exp = (today + datetime.timedelta(days=random.randint(30, 365))).isoformat()
    # simulate current price with small movement
    cur_price = round(orig_price * (1 + random.uniform(-0.05, 0.05)), 2)
    # fetch product-level strike/coupon/currency if present
    cur.execute("SELECT strike, coupon, currency FROM product WHERE product_id = ?", (pid,))
    prod_meta = cur.fetchone()
    strike_val = float(prod_meta[0]) if prod_meta and prod_meta[0] is not None else None
    coupon_val = float(prod_meta[1]) if prod_meta and prod_meta[1] is not None else None
    currency_val = prod_meta[2] if prod_meta and prod_meta[2] is not None else random.choice(['USD','EUR','GBP'])
    position_notional = round(qty * cur_price, 2)
    cur.execute("INSERT INTO positions (client_id, product_id, quantity, original_price, expiration_date, current_price, notional, strike, coupon, currency) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, pid, qty, orig_price, exp, cur_price, position_notional, strike_val, coupon_val, currency_val))

# Trades
for i in range(1, 101):
    tid = f"T{i:06d}"
    acct = f"ACCT{random.randint(1,5):04d}"
    pid = random.choice(products)
    qty = random.randint(1, 1000)
    ttype = random.choice(['BUY', 'SELL'])
    trade_price = round(random.uniform(80, 120), 2)
    trade_date = today - datetime.timedelta(days=random.randint(0, 60))
    settle = trade_date + datetime.timedelta(days=2)
    # determine currency from product if available
    cur.execute("SELECT currency FROM product WHERE product_id = ?", (pid,))
    prod_row = cur.fetchone()
    trade_currency = prod_row[0] if prod_row and prod_row[0] else random.choice(['USD','EUR','GBP'])
    trade_notional = round(qty * trade_price, 2)
    cur.execute("INSERT INTO trades (trade_id, client_account, product_id, quantity, trade_type, trade_price, trade_date, settlement_date, notional, currency) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (tid, acct, pid, qty, ttype, trade_price, trade_date.isoformat(), settle.isoformat(), trade_notional, trade_currency))

# Quotes
for i in range(1, 51):
    qid = f"Q{i:05d}"
    cid = random.choice(clients)
    payoff = random.choice(payoffs)
    issue_date = today - datetime.timedelta(days=random.randint(10, 400))
    expiry = issue_date + datetime.timedelta(days=random.randint(30, 365))
    issuer = random.choice(issuers)
    under = random.choice(underlyers)
    barrier = round(random.uniform(0.5, 1.5), 4)
    gross = round(random.uniform(0.0, 0.2), 4)
    q_barrier_type = random.choice(['None', 'Up-and-Out', 'Down-and-In', 'Up-and-In', 'Down-and-Out'])
    q_strike = round(random.uniform(80, 130), 2)
    q_currency = random.choice(['USD', 'EUR', 'GBP'])
    cur.execute("INSERT INTO quote (quote_id, client_id, payoff_type, issue_date, expiration_date, issuer, underlyer_stocks, barrier_level, gross_credit_level, barrier_type, strike, currency) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (qid, cid, payoff, issue_date.isoformat(), expiry.isoformat(), issuer, under, barrier, gross, q_barrier_type, q_strike, q_currency))

conn.commit()
conn.close()
print(f"Initialized database at {DB_PATH} with clients={len(clients)}, products={len(products)}")
