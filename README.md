# 📦 CJ DARCL — Logistics Intelligence System

A full-stack **Decision Intelligence System** for logistics operations, built with **Django REST Framework** and **React + Vite**. Upload real shipment data (Excel/CSV), get instant KPIs, smart insights, root-cause analysis, risk predictions, and data quality scoring — all on a polished dark-themed dashboard.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.x-092E20?logo=django&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

### 📊 Dashboard
- **KPI Cards** — Total shipments, on-time %, delayed count, total revenue (click any card to drill down)
- **Revenue Trends** — Interactive daily/weekly/monthly line charts
- **Top Routes** — Stacked bar chart showing on-time vs delayed per route
- **Delivery Performance** — Pie chart of on-time vs delayed proportions
- **Period Comparison** — Automatic current vs prior period comparison with trend arrows
- **Smart Insights** — Context-aware AI-generated observations from the data

### 🔍 Analytics
- **Root Cause Analysis** — Delays broken down by route, vehicle type, and month
- **Route Risk Matrix** — Every route scored as high / medium / low risk with delay rates, penalties, and shortage data
- **Shortage Analysis** — Affected shipments, total shortage in metric tons
- **Monthly Delay Patterns** — Seasonal trends visualized as bar charts

### 📁 Data Upload
- **Drag & drop** Excel (.xlsx, .xls) or CSV files
- Processes **42 DARCL logistics columns** automatically
- Intelligent column mapping, data cleaning, and deduplication
- **Data Quality Scoring** (0–100) with detailed issue reporting
- Full upload audit trail with processing time and error logs

### 🎛️ Filters
- Date range, origin, destination, vehicle/material type
- All endpoints support filtering — dashboard and analytics stay in sync

---

## 🗂️ Project Structure

```
cjDarcl_project/
└── logistics_project/
    ├── manage.py
    ├── requirements.txt
    ├── sample_shipments.xlsx          # Sample data for testing
    ├── logistics_project/             # Django project settings
    │   ├── settings.py
    │   ├── urls.py
    │   └── wsgi.py
    ├── shipments/                     # Django app
    │   ├── models.py                  # Route, UploadLog, Shipment
    │   ├── views.py                   # All API endpoints
    │   ├── serializers.py
    │   ├── urls.py
    │   ├── admin.py
    │   ├── migrations/
    │   └── utils/
    │       ├── data_cleaner.py        # Excel/CSV parsing & cleaning
    │       ├── kpi_engine.py          # Summary KPIs, revenue trends, top routes
    │       ├── analysis_engine.py     # Root cause, risk, shortage, smart insights
    │       └── quality_engine.py      # Data quality scoring
    └── frontend/                      # React + Vite app
        ├── package.json
        ├── vite.config.js
        ├── index.html
        └── src/
            ├── App.jsx                # Main application (all views)
            ├── api.js                 # API client functions
            ├── index.css              # Dark-themed styling
            └── main.jsx               # React entry point
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** and **npm**
- **Git**

### 1. Clone the Repository

```bash
git clone https://github.com/SourabhSingh683/cjdarcl.git
cd cjdarcl
```

### 2. Backend Setup (Django)

```bash
# Navigate to the project
cd logistics_project

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate          # Windows

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start the backend server
python manage.py runserver
```

The API will be available at **http://127.0.0.1:8000/api/**

### 3. Frontend Setup (React)

Open a **new terminal**:

```bash
cd logistics_project/frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

The frontend will be available at **http://localhost:5173**

### 4. Upload Data

1. Open the frontend at `http://localhost:5173`
2. Go to the **📁 Upload** tab
3. Drag & drop the included `sample_shipments.xlsx` (or your own DARCL data file)
4. The dashboard will auto-populate with KPIs and charts

---

## 📡 API Endpoints

All endpoints are prefixed with `/api/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload/` | Upload Excel/CSV file |
| `GET` | `/api/kpis/summary/` | Summary KPIs (total, on-time %, revenue, etc.) |
| `GET` | `/api/kpis/revenue-trends/` | Revenue over time (`?group_by=day\|week\|month`) |
| `GET` | `/api/kpis/top-routes/` | Top routes by volume (`?limit=10`) |
| `GET` | `/api/kpis/delayed-shipments/` | Paginated delayed shipments |
| `GET` | `/api/kpis/drilldown/` | Drill-down (`?filter=delayed\|on_time\|shortage\|penalty`) |
| `GET` | `/api/kpis/comparison/` | Period-over-period comparison (`?days=30`) |
| `GET` | `/api/analysis/root-cause/` | Root cause analysis (by route, vehicle, month) |
| `GET` | `/api/analysis/risk/` | Route risk scoring (high/medium/low) |
| `GET` | `/api/analysis/shortage/` | Shortage analysis |
| `GET` | `/api/quality/` | Overall data quality score |
| `GET` | `/api/insights/smart/` | AI-generated smart insights |
| `GET` | `/api/uploads/` | Upload history with audit trail |
| `GET` | `/api/shipments/` | Paginated shipment list |

### Common Query Parameters

All `GET` endpoints support these filters:

| Parameter | Example | Description |
|-----------|---------|-------------|
| `date_from` | `2024-01-01` | Filter from dispatch date |
| `date_to` | `2024-12-31` | Filter to dispatch date |
| `origin` | `Delhi` | Filter by origin (partial match) |
| `destination` | `Mumbai` | Filter by destination (partial match) |
| `vehicle_type` | `sheet` | Filter by vehicle/material type |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Django 5.x, Django REST Framework |
| **Frontend** | React 19, Vite 8 |
| **Charts** | Recharts |
| **Data Processing** | Pandas, OpenPyXL |
| **Database** | SQLite (default) — swap to PostgreSQL for production |
| **Styling** | Custom CSS (dark glassmorphism theme) |

---

## 📋 Data Model

The system uses three normalized models:

- **`Route`** — Unique origin → destination pairs  
- **`UploadLog`** — Audit trail for each file upload (status, quality score, processing stats)  
- **`Shipment`** — Core records with:
  - *Identity*: shipment ID, route, vehicle info
  - *Dates*: dispatch, delivery, expected delivery
  - *Financial*: revenue, rate/MT, freight deduction, penalty, amount receivable
  - *Weight*: net, gross, charge weight, shortage
  - *Transit*: permissible days, actual days, delay, on-time flag

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

<p align="center">Built with ❤️ by <a href="https://github.com/SourabhSingh683">Sourabh Singh</a></p>
