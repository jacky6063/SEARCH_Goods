# Copilot Instructions for SEARCH_Goods

## Project Overview
SEARCH_Goods is a lightweight product search system with natural language support. Users can search for products using text or voice input, with optional ChatGPT integration for query expansion and content generation.

## Architecture & Service Boundaries

### Backend Services (`backend/`)
- **`app.py`**: FastAPI main application with API endpoints, session management, and SPA routing
- **`goods_search_service.py`**: Core CSV-based product search with scoring algorithm and result formatting
- **`llm_service.py`**: Optional OpenAI GPT integration for query expansion, content generation, and chat functionality
- **`config_store.py`**: Dynamic branding configuration management

### Data Layer (`data/`)
- **Primary data source**: `VIEW_GOODS_enhanced.csv` - product catalog with Chinese column headers
- **ETL tool**: `backend/etl/update_csv.py` for atomic CSV updates via file replacement or URL downloads
- **Column mapping**: `backend/column_definitions.json` maps localized columns to canonical names

### Frontend (`frontend/`)
- **Single-page application**: `index.html` with embedded CSS/JS, responsive design
- **API integration**: Calls `/api/search` and `/api/chat` endpoints
- **Features**: Voice input (Web Speech API), real-time search, chat interface

## Key Development Patterns

### Environment-Based Feature Toggling
LLM features are controlled via environment variables - always check these before implementing AI features:
```bash
USE_LLM_EXPAND=True      # Query expansion
USE_LLM_SHORTDESC=True   # Generate 20-char descriptions
USE_LLM_RERANK=False     # AI-powered result reranking
USE_LLM_INTENT=True      # Intent parsing for required/excluded terms
USE_LLM_PROMO=False      # Marketing content generation
```

### CSV Data Handling Convention
- **Global cache**: `_df_cache` in `app.py` - clear via `/api/admin/clear-cache` after data updates
- **Atomic updates**: Always use `os.replace()` for CSV file operations (see `etl/update_csv.py`)
- **Column flexibility**: Support both English and Chinese column names via `COLUMN_NAME_MAP`

### Search Score Algorithm (`goods_search_service.py`)
```python
# Scoring weights (critical for search relevance):
# Name matches: +2 points
# Description matches: +1 point  
# Category/remarks: +1 point
# Special offer bonus: +0.2 points
# Minimum threshold: 1.5 points
```

### Session Management Pattern
Chat functionality uses in-memory session caches with TTL:
- `SESSION_ALIGN_CACHE`: Product alignment for confirmations
- `SUGGEST_CACHE`: Recommendation state
- Cleanup via `_cleanup_session_cache()` to prevent memory leaks

## Testing Conventions

### Test Structure (`backend/tests/`)
- **API tests**: Use `FastAPI.testclient` with real app instance
- **Service tests**: Test search logic with sample data
- **Admin tests**: Cover file upload and cache management endpoints
- **LLM tests**: Mock OpenAI calls, test intent parsing

### Running Tests
```bash
cd backend
pip install pytest
pytest -q  # Quick run, or pytest -v for verbose
```

## Development Workflows

### Local Development
```bash
# Backend setup
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Configure OPENAI_API_KEY if using LLM features
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend
python -m http.server 5173
```

### Docker Development
Use `docker-compose.dev.yml` for development with live code reloading:
```bash
docker compose -f docker-compose.dev.yml up --build
```

### Admin Operations
System includes admin endpoints protected by `ADMIN_TOKEN`:
- `POST /api/admin/upload-csv`: Atomic CSV replacement
- `POST /api/admin/clear-cache`: Clear in-memory data cache
- Set `ALLOW_DEV_ADMIN=1` to bypass token checks in development

## Integration Points

### Frontend ↔ Backend API
- **Search**: `POST /api/search` with query expansion and intent parsing
- **Chat**: `POST /api/chat` with conversation history and product alignment
- **Suggestions**: `POST /api/suggest` for recommendation variations

### LLM Integration Points
All LLM calls are optional and fail gracefully:
1. **Query time**: `llm_expand_query()` and `llm_analyze_query()` for better search
2. **Response time**: `llm_rerank_products()` and content generation functions
3. **Chat mode**: `chat_reply()` for conversational product discovery

### External Dependencies
- **OpenAI API**: For LLM features (configurable model via `OPENAI_MODEL`)
- **CSV data source**: Can be local file or loaded via ETL from URLs
- **Static assets**: Product images and shopping URLs from external sources

## Deployment Considerations

### Multi-Platform CI/CD
- **GitHub Actions**: `.github/workflows/ci.yml` runs pytest on push/PR
- **Auto-deploy**: `.github/workflows/deploy.yml` triggers Render (backend) and Netlify (frontend)
- **Required secrets**: `RENDER_SERVICE_ID`, `RENDER_API_KEY`, `NETLIFY_SITE_ID`, `NETLIFY_AUTH_TOKEN`

### Production Configuration
- Use `gunicorn` with uvicorn workers (see `gunicorn_conf.py`)
- Set strong `ADMIN_TOKEN` for CSV management endpoints
- Configure `DATA_PATH` environment variable for CSV location
- Health check endpoint: `GET /health` for load balancers

## Critical File Dependencies
- **`column_definitions.json`**: Maps Chinese column names to English keys
- **`branding_config.json`**: Stores dynamic UI configuration (logo, YouTube, prompts)
- **`requirements.txt`**: Pinned dependencies including FastAPI 0.104.1, OpenAI 1.3.5
- **Frontend assets**: Single HTML file with embedded CSS/JS for zero-dependency deployment