# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an A-share stock intelligent analysis system (A股自选股智能分析系统) that uses AI models to analyze selected stocks and push daily reports via multiple notification channels (WeChat Work, Feishu, Telegram, Email). It supports GitHub Actions for zero-cost deployment.

**Core Architecture:**
- `main.py` - Main entry point with `StockAnalysisPipeline` orchestrating the entire flow
- `config.py` - Singleton configuration manager loading from `.env`
- `data_provider/` - Strategy pattern for multiple data sources with automatic failover
- `analyzer.py` - AI analysis using Gemini API (with OpenAI-compatible fallback)
- `notification.py` - Multi-channel notification service
- `storage.py` - SQLite ORM with `DatabaseManager` singleton
- `search_service.py` - News search via Tavily/Bocha/SerpAPI
- `market_analyzer.py` - Market review/复盘 analysis
- `stock_analyzer.py` - Technical trend analysis with MA alignment checks

## Common Commands

### Running the Analysis

```bash
# Normal run (stocks + market review)
python main.py

# Debug mode with detailed logs
python main.py --debug

# Only fetch data, skip AI analysis
python main.py --dry-run

# Analyze specific stocks
python main.py --stocks 600519,000001

# Run without sending notifications
python main.py --no-notify

# Single-stock notification mode (push after each stock)
python main.py --single-notify

# Only run market review
python main.py --market-review

# Skip market review
python main.py --no-market-review

# Start WebUI for managing stock list
python main.py --webui
```

### Development Tools

```bash
# Install dependencies
pip install -r requirements.txt

# Code formatting (follow pyproject.toml config)
black .
isort .

# Linting
flake8 .

# Security scanning
bandit -r . -x ./test_*.py

# Module import tests
python -c "from config import get_config; print('OK')"
python -c "from data_provider import DataFetcherManager; print('OK')"
python -c "from analyzer import GeminiAnalyzer; print('OK')"
```

### Docker

```bash
# Build image
docker build -t stock-analysis .

# Run container
docker run -v $(pwd)/data:/app/data --env-file .env stock-analysis

# Using docker-compose
docker-compose up
```

## Architecture Patterns

### Configuration (Singleton Pattern)

All configuration is managed through `Config.get_instance()` in `config.py`. The config loads from `.env` file with these key behaviors:

- Environment variables are loaded once at first access
- Use `config.refresh_stock_list()` to reload stock list from `.env` during runtime
- The config supports multiple API keys with load balancing (search engines)

### Data Provider (Strategy Pattern + Failover)

The `data_provider/` package implements automatic failover across multiple sources:

**Priority order** (lower number = higher priority):
1. `EfinanceFetcher` (Priority 0) - efinance library
2. `AkshareFetcher` (Priority 1) - akshare library
3. `TushareFetcher` (Priority 2) - requires `TUSHARE_TOKEN`
4. `BaostockFetcher` (Priority 3) - baostock library
5. `YfinanceFetcher` (Priority 4) - Yahoo Finance fallback

Each fetcher implements `BaseFetcher` with:
- `_fetch_raw_data()` - Get raw data from source
- `_normalize_data()` - Standardize column names to `['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg']`
- `get_daily_data()` - Main entry point with indicator calculation

**Anti-ban strategy:**
- Random delays between requests (`random_sleep()`)
- Low concurrency (default `max_workers=3`)
- Exponential backoff retry via `tenacity` library

### Storage (ORM with Singleton)

`storage.py` uses SQLAlchemy ORM with:
- `DatabaseManager.get_db()` for singleton access
- `StockDaily` model for daily price data
- `has_today_data()` for checkpoint/resume support
- `get_analysis_context()` returns dict with 'raw_data' list and latest price info

### Analysis Pipeline

The `StockAnalysisPipeline` in `main.py` coordinates:

1. **Data fetching** - `fetch_and_save_stock_data()` with checkpoint support
2. **Enhanced analysis** - `analyze_stock()` combines:
   - Realtime quote (volume ratio, turnover rate)
   - Chip distribution data
   - Trend analysis (MA5/MA10/MA20 alignment)
   - Multi-dimensional news search
   - AI analysis via `GeminiAnalyzer`
3. **Notification** - Single-stock or batched dashboard reports

### AI Model Support

Primary: Google Gemini (`gemini-3-flash-preview`) - free tier available
Fallback: OpenAI-compatible APIs (DeepSeek, 通义千问, etc.)

The `GeminiAnalyzer` in `analyzer.py`:
- Returns `AnalysisResult` dataclass with dashboard format
- Uses tenacity for retry with exponential backoff
- `GEMINI_REQUEST_DELAY` controls rate limiting (default 2s)

### Notification Channels

`notification.py` supports multiple simultaneous channels:
- WeChat Work webhook
- Feishu webhook
- Telegram (Bot Token + Chat ID required)
- Email (auto-detects SMTP from sender address)
- Custom webhooks (DingTalk, Slack, Discord, Bark, etc.)
- Pushover (mobile push)

Key behaviors:
- WeChat has 4096 byte limit, uses simplified format
- Feishu has ~20KB limit
- `single_stock_notify` mode pushes after each stock vs batched

## Key Design Decisions

1. **Low Concurrency** - `max_workers=3` default to avoid API bans
2. **Checkpoint Support** - Database checked before fetching; skips if today's data exists
3. **Multi-source Failover** - Automatically tries next data source on failure
4. **Rate Limiting** - Random delays + exponential backoff throughout
5. **Multi-model Fallback** - Falls back from Gemini to OpenAI-compatible API if configured

## Stock Code Format

- Shanghai Exchange: `600xxx`, `601xxx`, `603xxx`
- Shenzhen Exchange: `000xxx`, `002xxx`, `300xxx` (ChiNext)
- Hong Kong: format with prefix handled by fetchers

## Trading Philosophy Built-in

The analysis incorporates these principles:
- **No chasing highs** - Deviation rate > 5% triggers "danger" warning
- **Trend trading** - Prefers MA5 > MA10 > MA20 bullish alignment
- **Buy point preference** - Volume pullback to MA5/MA10 support
- **Chip concentration** - Analyzes profit ratio and concentration

## Environment Variables

Critical variables for `.env`:
- `STOCK_LIST` - Comma-separated stock codes (required)
- `GEMINI_API_KEY` or `OPENAI_API_KEY` - At least one required
- `TAVILY_API_KEYS`/`BOCHA_API_KEYS`/`SERPAPI_API_KEYS` - For news search
- Notification channel configs (optional but recommended for alerts)

See `.env.example` for full configuration options.

## GitHub Actions

The workflow runs weekdays at 18:00 Beijing time (UTC 10:00).
Manual trigger supports three modes:
- `full` - Stocks + market review
- `market-only` - Market review only
- `stocks-only` - Stocks only

CI checks include: syntax, imports, Docker build, linting, security scan.
