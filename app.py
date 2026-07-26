"""
Backend FastAPI - Mesa de ayuda IA de RR. HH. de Patito S.A.

Responsabilidades:
- Recibir las solicitudes del chatbot (interfaz web u otro cliente REST).
- Llamar al Orquestador.
- Devolver la respuesta consolidada al cliente.

No contiene lógica de negocio: toda la decisión de qué agente(s) usar vive en
orchestrator.py, que a su vez reutiliza los agentes existentes sin modificarlos.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from orchestrator import responder
from agents.accion_agent import listar_solicitudes

app = FastAPI(
    title="Mesa de ayuda IA RR. HH. - Patito S.A.",
    description="API que consolida agentes LangChain (Beneficios, Políticas, Reclutamiento y Acción).",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Permite conexiones desde otros dominios durante el desarrollo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConsultaRequest(BaseModel):
    pregunta: str = Field(..., min_length=1, description="Pregunta del colaborador en lenguaje natural")


class ConsultaResponse(BaseModel):
    respuesta: str
    agentes_participantes: list[str]
    fuentes: list[str]
    error: str | None = None


@app.get("/health")
def salud():
    """Chequeo simple de que el servicio está arriba (no valida la API de Gemini)."""
    return {"estado": "ok"}


@app.get("/solicitudes")
def obtener_solicitudes():
    """Devuelve las solicitudes registradas (solo lectura) para la interfaz web."""
    try:
        return {"solicitudes": listar_solicitudes()}
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"No se pudieron leer las solicitudes: {error}")


@app.get("/")
def interfaz_web(request: Request):
    """Sirve la interfaz de chat (templates/index.html + static/style.css + static/script.js)."""
    return templates.TemplateResponse(request, "index.html")


@app.post("/consultar", response_model=ConsultaResponse)
def consultar(payload: ConsultaRequest):
    """Punto de entrada único del chatbot: recibe una pregunta y devuelve la respuesta consolidada del Orquestador."""
    pregunta = payload.pregunta.strip()
    if not pregunta:
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía.")

    try:
        resultado = responder(pregunta)
    except Exception as error:
        # Captura errores no controlados y devuelve una respuesta HTTP 500.
        raise HTTPException(status_code=500, detail=f"Error interno al procesar la consulta: {error}")

    return resultado


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
