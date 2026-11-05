"""
Punto de Entrada Principal — Casa Pellas · AI Executive Decision Suite
Servidor FastAPI + Uvicorn de alto rendimiento que expone la API REST (/api/*),
sirve los activos estáticos (/static, /branding) y renderiza la SPA ejecutiva (/).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import os
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.api import router as api_router, warmup_engines

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
BRANDING_DIR = BASE_DIR / "Branding"

TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-calentar motores de Caso 1 y Caso 2 en memoria al iniciar el contenedor
    warmup_engines()
    yield


app = FastAPI(
    title="Casa Pellas · AI Executive Decision Suite",
    description=(
        "Arquitectura Full-Stack de Alto Rendimiento (FastAPI + SPA Cliente) para "
        "Planificación S&OP Toyota (Caso 1) y Orquestación Predictiva Capesa (Caso 2)."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar directorios estáticos y de branding corporativo
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
if BRANDING_DIR.exists():
    app.mount("/branding", StaticFiles(directory=str(BRANDING_DIR)), name="branding")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Registrar endpoints de negocio (/api/*)
app.include_router(api_router)


@app.get("/healthz", tags=["Health"])
def health_check():
    return JSONResponse({"status": "ok", "service": "casa-pellas-ia-suite"})


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def serve_spa_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

