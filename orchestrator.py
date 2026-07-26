"""
Agente Orquestador - Mesa de ayuda IA de RR. HH. de Patito S.A.
Responsable de:
- Recibir la pregunta del usuario.
- Decidir qué agente(s) especializado(s) debe(n) responder (vía Tools).
- Consolidar una respuesta final única.
- Indicar agentes participantes y fuentes utilizadas.

Los agentes de lectura (Beneficios, Políticas, Reclutamiento) NO se modifican:
se reutilizan tal cual, cada uno envuelto en una Tool que llama a su responder().
El Agente de Acción (registro de solicitudes) se integra igual: se reutiliza su
función registrar_solicitud() sin modificar su lógica interna
"""

import contextvars
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

from agents.beneficios_agent import responder as responder_beneficios
from agents.politicas_agent import responder as responder_politicas
from agents.reclutamiento_agent import responder as responder_reclutamiento
from agents.accion_agent import registrar_solicitud, NOMBRE_AGENTE as NOMBRE_AGENTE_ACCION

load_dotenv()

MENSAJE_SIN_INFORMACION = "No encontré información suficiente en la base documental proporcionada."

SYSTEM_PROMPT = """Eres el Orquestador de la mesa de ayuda IA de Recursos Humanos de Patito S.A.

Tu única función es decidir qué herramienta(s) usar para responder la pregunta del colaborador
y consolidar una respuesta final clara a partir de lo que devuelvan esas herramientas.

Reglas estrictas:
- SIEMPRE debes usar al menos una herramienta antes de responder. Nunca respondas de memoria
  ni con conocimiento externo a las herramientas.
- Si la pregunta abarca varios temas (por ejemplo, vacaciones y seguro médico), invoca todas
  las herramientas necesarias antes de responder.
- Si ninguna herramienta tiene información relevante, responde exactamente:
  "No encontré información suficiente en la base documental proporcionada."
- No repitas literalmente el resultado de cada tool; redacta una respuesta final coherente
  que combine la información obtenida.
- No inventes datos que no provengan de las herramientas.

Reglas específicas para registrar_solicitud_rrhh (Agente de Acción):
- Úsala únicamente cuando el colaborador pida explícitamente REGISTRAR algo (una solicitud
  de vacaciones o la inscripción de un dependiente), no para simples preguntas informativas
  sobre esos temas (esas van a consultar_politicas o consultar_beneficios).
- Extrae de la conversación el tipo_solicitud ('vacaciones' o 'dependiente') y arma el
  diccionario `datos` con los campos que el usuario haya dado.
- El parámetro `confirmado` debe ser True ÚNICAMENTE si el usuario ya confirmó explícitamente
  el registro (por ejemplo "sí, confirmo" o "regístralo"). Si es la primera vez que se piden
  estos datos, usa confirmado=False para que la tool muestre el resumen antes de guardar nada.
- Si la tool indica que faltan datos o pide confirmación, transmite ese mensaje al usuario
  tal cual, sin inventar los datos que faltan."""


# Registro independiente por solicitud para almacenar agentes y fuentes usadas.
_registro_invocaciones_var: contextvars.ContextVar = contextvars.ContextVar(
    "registro_invocaciones", default=None
)


def _registro_actual() -> list:
    """Devuelve la lista de invocaciones de la consulta en curso (aislada por contexto)."""
    registro = _registro_invocaciones_var.get()
    if registro is None:
        registro = []
        _registro_invocaciones_var.set(registro)
    return registro


def _registrar_y_extraer_respuesta(resultado: dict) -> str:
    """Guarda agente y fuentes en el registro de la consulta actual; devuelve el texto para la tool."""
    _registro_actual().append({
        "agente": resultado["agente"],
        "fuentes": resultado["fuentes"],
    })
    return resultado["respuesta"]


@tool
def consultar_beneficios(pregunta: str) -> str:
    """Usa esta herramienta para preguntas sobre seguro médico corporativo, dependientes,
    bonos, compensación salarial y demás beneficios de Patito S.A."""
    try:
        resultado = responder_beneficios(pregunta)
    except Exception as error:
        return f"[Error] El Agente de Beneficios no pudo responder: {error}"
    return _registrar_y_extraer_respuesta(resultado)


@tool
def consultar_politicas(pregunta: str) -> str:
    """Usa esta herramienta para preguntas sobre jornada laboral, vacaciones, permisos,
    código de conducta y sanciones de Patito S.A."""
    try:
        resultado = responder_politicas(pregunta)
    except Exception as error:
        return f"[Error] El Agente de Políticas Internas no pudo responder: {error}"
    return _registrar_y_extraer_respuesta(resultado)


@tool
def consultar_reclutamiento(pregunta: str) -> str:
    """Usa esta herramienta para preguntas sobre proceso de selección, programa de referidos
    y onboarding de nuevos colaboradores de Patito S.A."""
    try:
        resultado = responder_reclutamiento(pregunta)
    except Exception as error:
        return f"[Error] El Agente de Reclutamiento no pudo responder: {error}"
    return _registrar_y_extraer_respuesta(resultado)


@tool
def registrar_solicitud_rrhh(tipo_solicitud: str, datos: dict, confirmado: bool = False) -> str:
    """
    Registra solicitudes de RR. HH. (vacaciones o dependientes) después de validar
    los datos requeridos y confirmar la acción con el usuario.
    tipo_solicitud: 'vacaciones' o 'dependiente'.
    Si confirmado es False, solo valida la información y muestra un resumen
    para solicitar confirmación antes de guardar.
    """
    try:
        resultado = registrar_solicitud(tipo_solicitud, datos, confirmado)
    except Exception as error:
        return f"[Error] El Agente de Acción no pudo procesar la solicitud: {error}"

# Guarda el estado de la herramienta para que responder() procese la respuesta correctamente.
    _registro_actual().append({"agente": NOMBRE_AGENTE_ACCION, "fuentes": []})
    return resultado["mensaje"]


HERRAMIENTAS = [consultar_beneficios, consultar_politicas, consultar_reclutamiento, registrar_solicitud_rrhh]

def _extraer_texto(contenido) -> str:
    """Normaliza el .content del último mensaje del agente a un string simple.
    Igual que en los agentes de lectura: a veces Gemini devuelve una lista de
    bloques (dicts con 'text') en vez de un string plano.
    """
    if isinstance(contenido, str):
        return contenido

    if isinstance(contenido, list):
        partes = []
        for fragmento in contenido:
            if isinstance(fragmento, str):
                partes.append(fragmento)
            elif isinstance(fragmento, dict) and "text" in fragmento:
                partes.append(fragmento["text"])
        return "".join(partes)

    return str(contenido)


_agente_orquestador = None


def _obtener_agente_orquestador():
    """Inicializa una sola vez el agente orquestador (LLM + tools)."""
    global _agente_orquestador

    if _agente_orquestador is not None:
        return _agente_orquestador

    llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0)
    _agente_orquestador = create_agent(model=llm, tools=HERRAMIENTAS, system_prompt=SYSTEM_PROMPT)
    return _agente_orquestador


def responder(pregunta: str) -> dict:
    """Punto de entrada del orquestador.
    A diferencia de los agentes de lectura (que devuelven agente/respuesta/fuentes),
    el orquestador devuelve respuesta/agentes_participantes/fuentes.
    """
    _registro_invocaciones_var.set([])

    try:
        agente = _obtener_agente_orquestador()
        resultado = agente.invoke({"messages": [{"role": "user", "content": pregunta}]})
        respuesta_final = _extraer_texto(resultado["messages"][-1].content)
    except Exception as error:
        return {
            "respuesta": "Ocurrió un error al procesar la consulta. Intenta de nuevo en unos minutos.",
            "agentes_participantes": [],
            "fuentes": [],
            "error": str(error),
        }

    registro_invocaciones = _registro_actual()

    if not registro_invocaciones:
        return {
            "respuesta": MENSAJE_SIN_INFORMACION,
            "agentes_participantes": [],
            "fuentes": [],
        }

    agentes_participantes = sorted({invocacion["agente"] for invocacion in registro_invocaciones})

    # dict.fromkeys deduplica preservando el orden original de aparición (Python 3.7+),
    # sin alterar la lógica de invocación de los agentes ni el resto del formato de salida.
    todas_las_fuentes = [fuente for invocacion in registro_invocaciones for fuente in invocacion["fuentes"]]
    fuentes = list(dict.fromkeys(todas_las_fuentes))

    return {
        "respuesta": respuesta_final.strip(),
        "agentes_participantes": agentes_participantes,
        "fuentes": fuentes,
    }


if __name__ == "__main__":
    pregunta_prueba = (
        "Voy a tomar mis vacaciones y además quiero agregar a mi pareja al seguro médico. "
        "¿Cuántos días me corresponden, cómo los solicito y qué necesito para inscribir "
        "a un dependiente en el beneficio?"
    )
    print(responder(pregunta_prueba))
