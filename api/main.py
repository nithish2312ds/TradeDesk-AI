import os
import time
import logging
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import APIKeyHeader
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from api.routes import market, research, rag, macro

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("tradedesk")

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="TradeDesk AI",
    description="AI-powered ASX trading research assistant",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENV") != "production" else None,
    redoc_url=None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
async def verify_api_key(api_key: str = Depends(api_key_header)):
    expected = os.getenv("TRADEDESK_API_KEY", "")
    if not expected: return
    if api_key != expected:
        log.warning(f"Invalid API key: {api_key[:8] if api_key else 'none'}...")
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start    = time.time()
    response = await call_next(request)
    ms       = round((time.time()-start)*1000)
    log.info(f"{request.method} {request.url.path} → {response.status_code} ({ms}ms) [{request.client.host}]")
    return response

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"]  = "nosniff"
    response.headers["X-Frame-Options"]         = "DENY"
    response.headers["X-XSS-Protection"]        = "1; mode=block"
    response.headers["Referrer-Policy"]         = "strict-origin-when-cross-origin"
    return response

app.include_router(market.router,   prefix="/market",   tags=["Market"],   dependencies=[Depends(verify_api_key)])
app.include_router(research.router, prefix="/research", tags=["Research"], dependencies=[Depends(verify_api_key)])
app.include_router(rag.router,      prefix="/rag",      tags=["RAG"],      dependencies=[Depends(verify_api_key)])
app.include_router(macro.router,    prefix="/macro",    tags=["Macro"],    dependencies=[Depends(verify_api_key)])

if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/app", include_in_schema=False)
def serve_app():
    return FileResponse("frontend/index.html")

@app.get("/")
@limiter.limit("30/minute")
def root(request: Request):
    return {"status": "running", "app": "TradeDesk AI", "version": "1.0.0"}

@app.get("/health")
@limiter.limit("60/minute")
def health(request: Request):
    return {"status": "healthy", "timestamp": time.time()}
