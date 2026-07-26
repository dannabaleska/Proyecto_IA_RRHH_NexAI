"""
Agente RAG de Beneficios y Compensaciones.
Responde consultas sobre beneficios utilizando Gemini y ChromaDB.
"""
import os

from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

load_dotenv()

NOMBRE_AGENTE = "Agente de Beneficios y Compensaciones"

# Rutas relativas al proyecto (nunca absolutas, según el estándar del equipo)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_CONOCIMIENTO = os.path.join(BASE_DIR, "knowledge", "01_Beneficios_Compensaciones.txt")
RUTA_VECTORSTORE = os.path.join(BASE_DIR, "vectorstores", "beneficios")
NOMBRE_COLECCION = "beneficios_compensaciones"

# Cache en memoria para no reconstruir el vector store ni el LLM en cada llamada
_vectorstore = None
_retriever = None
_llm = None

PROMPT_BENEFICIOS = """Eres el {agente} de Patito S.A.
Respondes preguntas sobre seguro medico, dependientes, bonos y demas beneficios.

Reglas estrictas:
- Responde UNICAMENTE con base en el CONTEXTO entregado.
- Si la informacion no esta en el contexto, responde exactamente: "No tengo esa informacion en el manual de beneficios."
- Se breve y directo. No inventes datos.

Contexto:
{{contexto}}

Pregunta: {{pregunta}}

Respuesta:""".format(agente=NOMBRE_AGENTE)


def _crear_o_cargar_vectorstore():
    """Crea el vector store la primera vez (chunking + embeddings) o lo carga si ya existe."""
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

    ya_existe = os.path.exists(RUTA_VECTORSTORE) and len(os.listdir(RUTA_VECTORSTORE)) > 0
    if ya_existe:
        return Chroma(
            persist_directory=RUTA_VECTORSTORE,
            embedding_function=embeddings,
            collection_name=NOMBRE_COLECCION,
        )

    cargador = TextLoader(RUTA_CONOCIMIENTO, encoding="utf-8")
    documentos = cargador.load()

    divisor = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    fragmentos = divisor.split_documents(documentos)

    vectorstore = Chroma.from_documents(
        documents=fragmentos,
        embedding=embeddings,
        persist_directory=RUTA_VECTORSTORE,
        collection_name=NOMBRE_COLECCION,
    )
    return vectorstore


def _obtener_retriever_y_llm():
    """Inicializa una sola vez el vector store (como retriever) y el LLM de Gemini."""
    global _vectorstore, _retriever, _llm

    if _retriever is not None and _llm is not None:
        return _retriever, _llm

    _vectorstore = _crear_o_cargar_vectorstore()
    _retriever = _vectorstore.as_retriever(search_kwargs={"k": 3})
    _llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0.2)

    return _retriever, _llm


def _resumir_fragmento(texto: str, longitud_maxima: int = 160) -> str:
    """Limpia y recorta un fragmento de texto para usarlo como fuente citada."""
    limpio = " ".join(texto.split())
    if len(limpio) > longitud_maxima:
        return limpio[:longitud_maxima].rstrip() + "..."
    return limpio


def _extraer_texto(contenido) -> str:
    """Normaliza el .content de la respuesta del LLM a un string simple.
    Algunas versiones de langchain_google_genai devuelven una lista de
    fragmentos (dicts con 'text' o strings sueltos) en vez de un string plano.
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


def responder(pregunta: str) -> dict:
    """Punto de entrada del agente. Cumple el contrato común del proyecto."""
    retriever, llm = _obtener_retriever_y_llm()

    documentos = retriever.invoke(pregunta)
    contexto = "\n\n".join(doc.page_content for doc in documentos)

    prompt_final = PROMPT_BENEFICIOS.format(contexto=contexto, pregunta=pregunta)
    respuesta = _extraer_texto(llm.invoke(prompt_final).content)

    return {
        "agente": NOMBRE_AGENTE,
        "respuesta": respuesta.strip(),
        "fuentes": [_resumir_fragmento(doc.page_content) for doc in documentos],
    }


if __name__ == "__main__":
    pregunta_prueba = "¿Cómo agrego un dependiente a mi seguro médico?"
    print(responder(pregunta_prueba))
