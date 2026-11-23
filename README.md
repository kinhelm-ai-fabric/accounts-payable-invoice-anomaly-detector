# Accounts Payable Invoice Anomaly Detector

AI-powered invoice analysis tool for accounts payable teams. Detects anomalies such as amount outliers, potential duplicates, date irregularities, and other suspicious patterns in invoice data.

## Features

- **Invoice Management**: Create, upload (CSV), and manage invoices
- **AI-Powered Analysis**: Kindo AI agent integration for intelligent anomaly detection
- **Rule-Based Fallback**: Built-in statistical analysis when AI is unavailable
- **Dashboard**: At-a-glance overview of invoice health and anomaly metrics
- **Anomaly Tracking**: Review, prioritize, and resolve detected anomalies
- **Light/Dark Theme**: User-preference-based theme switching

## Quick Start

1. **Clone and configure:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

2. **Run with Docker:**
   ```bash
   docker build -t ap-anomaly-detector .
   docker run -p 5000:5000 -v ap-data:/app/data ap-anomaly-detector
   ```

3. **Login:** Navigate to `http://localhost:5000` and sign in with `admin` / `admin`.

## CSV Import Format

```csv
invoice_number,vendor_code,vendor_name,amount,invoice_date,due_date,currency,description
INV-2024-001,ACME-001,Acme Corp,5250.00,2024-01-15,2024-02-15,USD,Office supplies Q1
```

## Kindo AI Agent

For AI-powered anomaly detection, set `KINDO_API_KEY` and `KINDO_INVOICE_ANOMALY_AGENT_ID` in your environment. See `agent/agent-config.yaml` for agent configuration details.

## Tech Stack

- **Backend**: Python / Flask / SQLAlchemy / SQLite
- **Server**: Gunicorn (multi-worker)
- **AI**: Kindo Agents API
- **Deployment**: Docker
