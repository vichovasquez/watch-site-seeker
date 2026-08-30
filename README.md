# Universal Multi-Website Search & Matcher Web App

A high-performance local web application that searches inventory across 80+ luxury watch dealer websites and forums in parallel. It automatically detects search mechanisms, extracts live product cards (images, prices, stock availability, direct links), and provides an interactive dashboard with direct list management and instant search cancellation.

---

## Features

- **Parallel Search Concurrency**: Searches 80+ websites simultaneously in seconds using Python asynchronous threads.
- **Intelligent Discovery Engine**:
  - Automatically queries Shopify Predictive Search APIs & HTML catalog pages.
  - Decomposes and normalizes complex reference numbers (e.g. `126518LN-0004` $\rightarrow$ `126518LN`).
  - Supports modern Shopify 2.0 (Dawn) nested DOM structures, WooCommerce, and custom forms.
- **Instant Search Cancellation**: Click **Stop Search** at any time to immediately cancel pending network requests and re-focus the search bar for a new query.
- **On-Dashboard Website Manager**:
  - **Inline Quick-Add**: Add new website URLs directly from the dashboard.
  - **Direct Full-List Editor**: Edit or paste URLs in bulk in a multi-line text editor.
  - **Google Doc Live Sync**: One-click sync to reload the latest dealer list from Google Drive.
  - **Quick Toggle Chips**: Enable/disable individual websites or use **Select All** / **Deselect All**.
- **Modern Responsive UI**: Dark luxury theme built with Tailwind CSS, live search progress indicators, relevance scores, and CSV export.

---

## Project Structure

```
site-search-app/
├── main.py              # FastAPI server & REST API endpoints
├── search_engine.py     # Universal multi-platform searcher & card extractor
├── sites_manager.py     # Website list management, Google Doc sync & JSON store
├── sites.json           # Active list of 80 dealer websites & configurations
├── static/
│   └── index.html       # Single-page interactive web dashboard
├── requirements.txt     # Python dependencies
├── run.bat              # One-click Windows launcher
└── README.md            # Documentation
```

---

## Quick Start

### 1. Prerequisites
Ensure you have **Python 3.10+** and **Git** installed.

### 2. Installation
```bash
git clone <your-repository-url>
cd site-search-app
pip install -r requirements.txt
```

### 3. Run the Application
On Windows, double-click `run.bat` or run:
```bash
python main.py
```
Open your browser and navigate to:
```
http://localhost:8000
```

---

## Sample Queries

- **`4020T`**: *Vacheron Constantin Traditionnelle Complete Calendar Openface*
- **`126518LN-0004`**: *Rolex Daytona Paul Newman Yellow Gold Oysterflex*
- **`116500LN`**: *Rolex Daytona Ceramic (Black / White Dial)*
- **`15500ST`**: *Audemars Piguet Royal Oak*
- **`5711`**: *Patek Philippe Nautilus*

---

## License
MIT License
