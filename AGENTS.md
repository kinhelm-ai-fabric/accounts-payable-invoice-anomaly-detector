# Accounts Payable Invoice Anomaly Detector -- AGENTS.md

## Project Structure

```
accounts-payable-invoice-anomaly-detector/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── models.py                # SQLAlchemy models (User, Vendor, Invoice, Anomaly)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── main.py              # Dashboard, Getting Started, health, theme API
│   │   ├── auth.py              # Login, register, logout
│   │   ├── invoices.py          # Invoice CRUD, CSV upload
│   │   └── analysis.py          # Anomaly analysis, resolve
│   ├── services/
│   │   ├── __init__.py
│   │   └── anomaly_service.py   # Kindo AI agent + rule-based detection
│   ├── templates/
│   │   ├── layouts/base.html    # Base template with sidebar, help panel, theme toggle
│   │   ├── main/                # Dashboard, Getting Started
│   │   ├── auth/                # Login, Register
│   │   ├── invoices/            # List, Form, Detail, Upload
│   │   ├── analysis/            # Overview
│   │   └── errors/              # 500
│   └── static/
│       ├── css/style.css        # Full stylesheet with light/dark themes
│       └── js/app.js            # Theme toggle, help panel, flash auto-dismiss
├── agent/
│   ├── agent-config.yaml        # Agent index
│   └── agents/
│       └── invoice-anomaly-detector.yaml  # Agent config
├── wsgi.py                      # WSGI entry point with stable SECRET_KEY
├── gunicorn.conf.py             # Gunicorn config with preload_app = True
├── Dockerfile                   # Production Docker image
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template
├── .gitignore                   # Git ignore rules
└── README.md                    # Project documentation
```

## Blueprints

| Blueprint    | Prefix      | File                    |
|-------------|-------------|-------------------------|
| main_bp     | (none)      | app/routes/main.py      |
| auth_bp     | (none)      | app/routes/auth.py      |
| invoices_bp | /invoices   | app/routes/invoices.py  |
| analysis_bp | /analysis   | app/routes/analysis.py  |

## Routes

| Method | Route                             | Auth     | Description                    |
|--------|-----------------------------------|----------|--------------------------------|
| GET    | /                                 | required | Dashboard                      |
| GET    | /getting-started                  | required | Getting Started guide          |
| GET    | /health                           | public   | Health check                   |
| POST   | /api/theme                        | required | Set light/dark theme           |
| GET    | /login                            | public   | Login page                     |
| POST   | /login                            | public   | Login action                   |
| GET    | /register                         | public   | Register page                  |
| POST   | /register                         | public   | Register action                |
| GET    | /logout                           | required | Logout                         |
| GET    | /invoices/                        | required | Invoice list                   |
| GET    | /invoices/new                     | required | New invoice form               |
| POST   | /invoices/new                     | required | Create invoice                 |
| GET    | /invoices/<id>                    | required | Invoice detail                 |
| POST   | /invoices/<id>/status             | required | Update invoice status (JSON)   |
| GET    | /invoices/upload                  | required | CSV upload form                |
| POST   | /invoices/upload                  | required | CSV upload action              |
| GET    | /analysis/                        | required | Anomaly overview               |
| POST   | /analysis/run/<id>                | required | Run analysis on one invoice    |
| POST   | /analysis/resolve/<id>            | required | Resolve an anomaly             |
| POST   | /analysis/run-all                 | required | Analyze all pending invoices   |

## Kindo Agents

| Agent                          | Env Var                           | Config File                                    |
|-------------------------------|-----------------------------------|------------------------------------------------|
| Invoice Anomaly Detector Agent | KINDO_INVOICE_ANOMALY_AGENT_ID   | agent/agents/invoice-anomaly-detector.yaml     |
