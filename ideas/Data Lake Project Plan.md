# Project Plan: Financial Data Harmonization & Agentic MCP Layer (Hybrid Strategy)

**Objective**:  
Harmonize Trading, Risk, and Market Data from legacy (Sybase) and modern (Postgres) sources into Snowflake using a **Daily Batch (T-1)** foundation for deep analytics, augmented by **Direct-to-API** tools for real-time intraday visibility.

**Timeline**: 12 Weeks  
**Owner**: Senior Tech Lead

---

## Phase 1: Ingestion & Architecture (Weeks 1–3)

**Goal**: Establish reliable "Nightly Dump" pipes from source to Snowflake "Bronze" layer.

### 1.1 Ingestion Strategy (Batch ELT)

- Use Snowflake’s efficient `COPY INTO` command for bulk loading (5–10x cheaper than streaming).

#### The "Landing Zone"

- **1.a.** Data Engineering to provision an S3/Azure Blob container.  
- **1.b.** Folder Structure: `/raw/{source}/{entity}/YYYY-MM-DD/file.parquet`

#### Sybase ASE (Legacy)

- **1.a.** Method: Scheduled Cron job triggers `bcp` (Bulk Copy Program) or SQL export to the Landing Zone every night at 01:00 UTC.  
- **1.b.** Content: Full snapshot of Trades (incremental since last run) and Positions (full dump).

#### PostgreSQL (Modern)

- **1.a.** Method: Scheduled export script to Landing Zone.  
- **1.b.** Content: Daily dump of `Market_Data_History` and `Client_Static`.

### 1.2 Snowflake Layering (The Medallion Architecture)

#### Bronze Layer (Raw)

- **1.a.** Tables partitioned by `load_date`.  
- **1.b.** Data is "Appended" daily—no overwrites; full history retained for auditability.

#### Silver Layer (Cleaned)

- **1.a.** Deduplicated via `QUALIFY` window functions.  
- **1.b.** Normalization: Map Sybase `1/0` booleans to Postgres `True/False`.

#### Gold Layer (The Agent's Truth)

- **1.a.** Star Schema optimized for read-heavy Agent queries.

---

## Phase 2: The Unified Data Model & History (Weeks 4–7)

**Goal**: Handle the "Time Travel" aspect of financial data using dbt and ensure Logic Parity.

### 2.1 Strategy A: Slowly Changing Dimensions (Client & Product)

- For data that changes rarely (**SCD Type 2**).  
  - **Mechanism**: `dbt snapshots`  
  - **Table Structure**: `dim_client_history` with `valid_from` and `valid_to` columns.

### 2.2 Strategy B: Periodic Snapshots (Positions & Risk)

- For data that changes every day.  
  - **Mechanism**: Daily Partitioning  
  - **Table Structure**: `fact_positions_daily` with `snapshot_date` column.

### 2.3 The Serving Layer (Critical for Agents)

To prevent agents from querying expired data:

- `v_dim_client_current`:  

  ```sql
  SELECT * FROM dim_client_history WHERE valid_to IS NULL
  ```

- `v_fact_risk_latest`:  

  ```sql
  SELECT * FROM fact_risk_daily WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM fact_risk_daily)
  ```

### 2.4 Logic Parity & Validation (The "Trust" Phase)

> **CTO Probe Addressed**: *"How do we know the math matches Sybase?"*

- **Parallel Run**: Weeks 6–7—run legacy Sybase Risk Report and new Snowflake dbt model side-by-side.  
- **Automated Reconciliation**:
  - **2.4.1.a.** Python script (`check_parity.py`) compares Sybase output CSV vs. Snowflake Gold tables.  
  - **2.4.1.b.** Tolerance: Flag any PnL discrepancy > **$0.01** or Risk > **0.1%**.  
  - **2.4.1.c.** Sign-off required from Risk Desk Head before Phase 3 begins.

---

## Phase 3: The Hybrid MCP Server Build (Weeks 8–10)

**Goal**: Build an Agent that is smart about History (Snowflake) and aware of the Now (API).

### 3.1 Architecture: The "Hybrid" Bridge

> **CTO Probe Addressed**: *"Traders need real-time data."*

The MCP Server routes queries based on **Temporal Intent**:

- **Deep Analysis/History** → Snowflake (T-1 Data)  
- **Live Checks** → Direct API (OMS/Bloomberg) for current price/position

### 3.2 Tool Definitions

The Agent has access to these Python functions:

#### Tool A: `get_client_profile` (Snowflake)

- **Target**: `v_dim_client_current`  
- **Logic**: Fast lookup of static data.

#### Tool B: `analyze_historical_risk` (Snowflake)

- **Target**: `fact_risk_daily`  
- **Logic**: "How did exposure change last week?"

#### Tool C: `get_live_market_data` (Direct API)

- **Source**: Direct HTTP call to Market Data Provider (e.g., Refinitiv/Bloomberg) or internal OMS Cache.  
- **Usage**: Only for "What is the price of AAPL right now?"  
- **Note**: Bypasses Snowflake entirely to solve T-1 latency.

### 3.3 Governance & Guardrails

> **CTO Probe Addressed**: *"Preventing Hallucinations."*

- **Code-Level Enforcement**:
  - Agent does **not** write SQL to choose tables—it calls Python functions.
    - `get_current_risk()` is **hardcoded** to query `v_fact_risk_latest`.
    - Agent **cannot** query history table unless it explicitly calls `get_historical_risk(date)`.
- **System Prompt**:  
  *"You are a Risk Assistant. For current prices, ALWAYS use the `get_live_market_data` tool. For trend analysis, use Snowflake tools."*

---

## Phase 4: Deployment (Weeks 11–12)

- **Week 11**: UAT with Risk Managers using the Hybrid Agent.  
- **Week 12**: Production Deploy (Read-Only).

---

## Phase 5: Strategic Roadmap (The Future)

> **CTO Probe Addressed**: *"How does this retire Sybase?"*

### 5.1 The "Strangler Fig" Pattern

Decouple traders from Sybase by shifting the **Consumption Layer** (Agents/Reports) to Snowflake/MCP:

1. **Today**: Sybase feeds Snowflake → Agents read Snowflake.  
2. **Tomorrow**: New OMS feeds Snowflake → update **Silver Layer** logic to map new OMS to existing Gold Schema.  
3. **Result**: Agent/traders see no change—Sybase can be safely decommissioned.

### 5.2 Path to Real-Time Snowflake

Once batch is stable, upgrade **Phase 1.1** from "Daily Batch" to:

- Micro-batch (e.g., every 15 mins)  
- Snowpipe Streaming  

**No changes needed** to downstream Agent tools—only ingestion frequency increases.

```
