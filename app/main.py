import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.config.settings import settings
from app.api import health, repos
from app.database.db import init_db

logging.basicConfig(level=settings.log_level)
app = FastAPI(title="Codebase GPS API", version="0.1.0")
frontend_origins = sorted({
    *settings.cors_origins,
    "https://codebase-gps-backend-v2.vercel.app",
})


@app.get("/", tags=["health"])
def service_info():
    return {
        "service": "Codebase GPS API",
        "status": "ok",
        "health": "/health",
        "docs": "/docs",
    }

@app.on_event("startup")
def on_startup():
    init_db()

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": "ERROR", "message": str(exc.detail)}})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": {"code": "VALIDATION_ERROR", "message": str(exc)}})

app.include_router(health.router)
app.include_router(repos.router)

# Keep CORS outside FastAPI's server-error middleware. Otherwise an unhandled
# issue-analysis error loses CORS headers and the frontend only sees
# the misleading "Failed to fetch" message.
app = CORSMiddleware(
    app=app,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)   
