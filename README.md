# Asistente Virtual IA · RR. HH. — Patito S.A.

Proyecto final del Semillero de Inteligencia Artificial. Prototipo funcional (no productivo) de una mesa de ayuda para el Departamento de Recursos Humanos de Patito S.A., compuesta por agentes especializados construidos con **LangChain** y **Google Gemini**, coordinados por un Orquestador, expuestos vía **FastAPI** y consumidos desde una interfaz web de chat (identidad **NexAI · Patito S.A.**).

> Datos, documentos y empresa son ficticios, creados únicamente para fines de evaluación del semillero.

**Equipo de desarrollo — NexAI**
- Granados Galarraga Joel Rodolfo
- Alvarez Salazar Danna Baleska
- López Reyes Danna Julexy

---

## Tabla de contenidos

1. [Arquitectura general](#arquitectura-general)
2. [Requisitos previos](#requisitos-previos)
3. [Instalación](#instalación)
4. [Ejecución](#ejecución)
5. [Estructura del proyecto](#estructura-del-proyecto)
6. [Agentes de lectura (RAG)](#agentes-de-lectura-rag)
7. [Orquestador](#orquestador)
8. [Agente de Acción](#agente-de-acción)
9. [Backend FastAPI](#backend-fastapi)
10. [Interfaz web](#interfaz-web)
11. [Pruebas](#pruebas)
12. [Ejemplos de preguntas](#ejemplos-de-preguntas)
13. [Decisiones técnicas y trade-offs](#decisiones-técnicas-y-trade-offs)
14. [Riesgos y mejoras futuras](#riesgos-y-mejoras-futuras)

---

## Arquitectura general

```
Usuario
   │
Interfaz Web (templates/index.html + static/)
   │
FastAPI (app.py)  ──►  GET /solicitudes  (solo lectura, no pasa por el Orquestador)
   │
POST /consultar
   │
Orquestador (orchestrator.py)
 ├─ Tool → Agente de Beneficios y Compensaciones   (RAG · knowledge/01_Beneficios_Compensaciones.txt)
 ├─ Tool → Agente de Políticas Internas            (RAG · knowledge/02_Reglamento_Interno.txt)
 ├─ Tool → Agente de Reclutamiento y Onboarding    (RAG · knowledge/03_Reclutamiento_Onboarding.txt)
 └─ Tool → Agente de Acción                        (registro_solicitudes_rrhh.txt)
   │
Respuesta consolidada: { respuesta, agentes_participantes, fuentes }
```

El Orquestador es un agente de LangChain con *function calling* (`langchain.agents.create_agent`, LLM Gemini) que decide, por cada pregunta, qué combinación de herramientas invocar. Cada agente de lectura mantiene su propio índice vectorial independiente (nadie comparte vector store), y el Agente de Acción es el único con efecto secundario (escribe en disco).

---

## Requisitos previos

- Python 3.11.x
- Una API Key de Google Gemini ([Google AI Studio](https://aistudio.google.com/))
- Git

---

## Instalación

```bash
# 1. Crear y activar un entorno virtual
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

# 2. Instalar dependencias
python -m pip install -r requirements.txt
```

### Configuración

1. Copia el archivo `.env.example` y renómbralo como `.env`.
2. Abre el archivo `.env`.
3. Reemplaza el valor de `GOOGLE_API_KEY` por tu propia clave de Gemini.

---

## Ejecución

```bash
python app.py
```

Esto levanta el servidor FastAPI en `http://localhost:8000`:

- **`http://localhost:8000/`** — interfaz de chat.
- **`http://localhost:8000/docs`** — documentación interactiva (Swagger) de la API.

La primera vez que cada agente de lectura recibe una pregunta, genera su índice vectorial en `vectorstores/` (chunking + embeddings); en ejecuciones posteriores lo reutiliza sin reconstruirlo.

---

## Estructura del proyecto

```
Proyecto_IA_RRHH/
├── agents/
│   ├── beneficios_agent.py
│   ├── politicas_agent.py
│   ├── reclutamiento_agent.py
│   └── accion_agent.py
├── knowledge/
│   ├── 01_Beneficios_Compensaciones.txt
│   ├── 02_Reglamento_Interno.txt
│   └── 03_Reclutamiento_Onboarding.txt
├── vectorstores/          # generado automáticamente, uno por agente de lectura
├── tests/
│   ├── test_beneficios_agent.py
│   ├── test_politicas_agent.py
│   ├── test_reclutamiento_agent.py
│   ├── test_accion_agent.py
│   └── test_orchestrator.py
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   ├── script.js
│   ├── vendor/marked.min.js
│   └── img/
├── app.py                 # backend FastAPI
├── orchestrator.py        # agente orquestador
├── registro_solicitudes_rrhh.txt   # generado por el Agente de Acción
├── requirements.txt
├── .env.example
└── README_Proyecto_Semillero_NexAI.md
```

Cada agente de lectura importa y reutiliza únicamente su propia base de conocimiento; no hay imports cruzados entre agentes (regla de independencia de módulos).

---

## Agentes de lectura (RAG)

Los tres siguen exactamente el mismo patrón y contrato:

```python
responder(pregunta: str) -> dict
# {
#   "agente": "...",
#   "respuesta": "...",
#   "fuentes": ["fragmento usado 1", "fragmento usado 2", ...]
# }
```

**Funcionamiento común:**
1. Se lee el documento `.txt` correspondiente.
2. **Chunking:** `RecursiveCharacterTextSplitter`, `chunk_size=1000`, `chunk_overlap=200`.
3. **Embeddings + vector store:** cada fragmento se vectoriza con `models/gemini-embedding-001` y se guarda en **ChromaDB**, en un índice dedicado por agente. Este paso solo ocurre en la primera ejecución.
4. Ante cada pregunta se recuperan los 3 fragmentos más relevantes (`k=3`).
5. Se arma un prompt que obliga al modelo (`gemini-3.1-flash-lite`) a responder únicamente con ese contexto.
6. Si la información no está en el contexto, el agente responde el mensaje estándar de "sin información suficiente" (nunca inventa).

### Agente de Beneficios y Compensaciones
- Fuente: `knowledge/01_Beneficios_Compensaciones.txt`
- Vector store: `vectorstores/beneficios/` (colección `beneficios_compensaciones`)
- Temas: seguro médico corporativo, dependientes, bonos, compensación.
- Ejemplos: *"¿Cómo agrego un dependiente a mi seguro médico?"*, *"¿Qué cubre el seguro médico corporativo?"*, *"¿Cada cuánto se revisan las salariales?"*

### Agente de Políticas Internas
- Fuente: `knowledge/02_Reglamento_Interno.txt`
- Vector store: `vectorstores/politicas/` (colección `politicas_internas`)
- Temas: jornada laboral, vacaciones, permisos, código de conducta, sanciones.
- Ejemplos: *"¿Cuál es la jornada laboral?"*, *"¿Cuántos días de vacaciones tengo?"*, *"¿Cómo solicito vacaciones?"*

### Agente de Reclutamiento y Onboarding
- Fuente: `knowledge/03_Reclutamiento_Onboarding.txt`
- Vector store: `vectorstores/reclutamiento/` (colección `reclutamiento_onboarding`)
- Temas: proceso de selección, programa de referidos, onboarding.
- Ejemplos: *"¿Cómo funciona el programa de referidos?"*, *"¿Qué pasa en el primer día de onboarding?"*

Pruebas de cada agente en `tests/test_<agente>_agent.py`, ejecutables individualmente:
```bash
python tests/test_beneficios_agent.py
python tests/test_politicas_agent.py
python tests/test_reclutamiento_agent.py
```

---

## Orquestador

`orchestrator.py` — agente LangChain (`create_agent`, LLM Gemini `gemini-3.1-flash-lite`, `temperature=0`) que envuelve cada agente de lectura y al Agente de Acción como **Tools**.

**Responsabilidades:**
- Clasificar la intención de la pregunta (una sola temática, mixta, o fuera de dominio).
- Invocar una o varias tools según corresponda.
- Consolidar una respuesta final coherente a partir de los resultados parciales.
- Registrar qué agentes participaron y qué fuentes se usaron (trazabilidad).

**Contrato de salida** (distinto al de los agentes de lectura, porque puede haber más de un agente involucrado):
```python
responder(pregunta: str) -> dict
# {
#   "respuesta": "...",
#   "agentes_participantes": ["Agente de Beneficios y Compensaciones", ...],
#   "fuentes": ["fragmento 1", "fragmento 2", ...]   # deduplicadas, orden de aparición
# }
```

Si ningún agente encuentra información relevante, responde exactamente:
> "No encontré información suficiente en la base documental proporcionada."

**Aislamiento por request:** el registro interno de qué agentes/fuentes participaron en cada consulta usa `contextvars` en vez de una variable global, para que FastAPI pueda atender consultas concurrentes sin que se mezclen entre sí.

Pruebas: `tests/test_orchestrator.py` — cubre los 3 agentes por separado, las 3 combinaciones mixtas posibles, y una consulta fuera de dominio.

---

## Agente de Acción

`agents/accion_agent.py` — el único agente con efecto secundario: registra solicitudes de RR. HH. en `registro_solicitudes_rrhh.txt`.

**Tipos de solicitud soportados** (configuración extensible en `CAMPOS_REQUERIDOS`; agregar un tipo nuevo no requiere tocar el resto de la lógica):

| Tipo | Campos obligatorios |
|---|---|
| `vacaciones` | nombre_colaborador, fecha_inicio, fecha_fin, numero_dias, jefe_aprueba |
| `dependiente` | nombre_dependiente, vinculo, documentos_respaldo |

**Sistema de control (obligatorio según el caso práctico):**
- Valida que estén todos los campos obligatorios antes de registrar; si falta algo, lo indica y no registra.
- Pide confirmación explícita del usuario antes de escribir al archivo.
- Genera un identificador único (8 caracteres) y marca de fecha/hora al registrar.
- Evita registrar duplicados exactos (misma firma de tipo + datos, comparación con claves ordenadas alfabéticamente para no depender del orden en que el LLM arma el diccionario).
- Para `vacaciones`, valida además la regla de 15 días de anticipación (no bloquea el registro, se muestra como advertencia).
- Maneja errores de escritura sin interrumpir al resto del sistema.

**Consulta de solo lectura:** `listar_solicitudes()` parsea el `.txt` reutilizando el mismo formato que escribe el registro (misma función `_bloque_tipo_y_datos` para ambos), evitando que lector y escritor se desincronicen. Se expone vía `GET /solicitudes` y se muestra en el acordeón "Solicitudes registradas" del sidebar de la interfaz — es únicamente informativo, no permite editar ni eliminar registros.

Pruebas: `tests/test_accion_agent.py` — tipo inválido, datos faltantes, pendiente de confirmación, registro exitoso (ambos tipos), duplicado, advertencia de anticipación.

---

## Backend FastAPI

`app.py` expone:

| Endpoint | Método | Descripción |
|---|---|---|
| `/` | GET | Sirve la interfaz web (`templates/index.html`) |
| `/consultar` | POST | Recibe `{"pregunta": "..."}`, invoca al Orquestador, devuelve la respuesta consolidada |
| `/solicitudes` | GET | Lista de solo lectura de las solicitudes ya registradas (no pasa por el Orquestador ni por ningún LLM) |
| `/health` | GET | Chequeo simple de disponibilidad del servicio |

No contiene lógica de negocio: delega toda la decisión de qué agente(s) usar al Orquestador. Maneja errores en una capa adicional (además del manejo interno del Orquestador) para no exponer tracebacks al cliente.

---

## Interfaz web

`templates/index.html` + `static/` — chat de una página, identidad **NexAI · Patito S.A.**:

- Burbujas de conversación con avatares (placeholders circulares reemplazables por imágenes propias).
- Respuestas renderizadas en Markdown (`marked.js`, alojado localmente en `static/vendor/` para no depender de un CDN externo).
- Acordeón **"Información utilizada"** por respuesta: agentes participantes (badges) y fuentes consultadas.
- Sidebar con **"Solicitudes registradas"** (consume `GET /solicitudes`), módulos principales, estado del sistema y tarjeta de ayuda — todo informativo, sin lógica adicional.
- Historial de conversación visible en pantalla; el backend permanece *stateless* (cada pregunta se envía sin el contexto de mensajes anteriores).
- Responsive: el sidebar se oculta en pantallas angostas para priorizar el chat.

---

## Pruebas

```bash
python tests/test_beneficios_agent.py
python tests/test_politicas_agent.py
python tests/test_reclutamiento_agent.py
python tests/test_accion_agent.py
python tests/test_orchestrator.py
```

Además, se realizó un checklist manual de extremo a extremo sobre la interfaz web cubriendo: los 3 agentes por separado, las 3 combinaciones mixtas, preguntas fuera de dominio, el flujo completo del Agente de Acción (datos faltantes → confirmación → registro → duplicado), Markdown, el acordeón de fuentes, el listado de solicitudes registradas, responsive, y manejo de errores de red.

---

## Ejemplos de preguntas

- *"¿Qué cubre el seguro médico corporativo y cómo agrego a un familiar como dependiente?"*
- *"¿Cuántos días de vacaciones me corresponden al año y cómo solicito un permiso no remunerado?"*
- *"¿Cómo funciona el programa de referidos y qué pasos incluye el onboarding de un nuevo ingreso?"*
- **Consulta mixta:** *"Voy a tomar mis vacaciones y además quiero agregar a mi pareja al seguro médico. ¿Cuántos días me corresponden, cómo los solicito y qué necesito para inscribir a un dependiente en el beneficio?"*
- **Fuera de dominio:** *"¿Cuál es la capital de Francia?"* → responde el mensaje estándar de información insuficiente.
- **Registro:** *"Registra una solicitud de vacaciones del 1 al 7 de agosto (5 días hábiles), aprobada por mi jefe. Confirmo el registro."*

---

## Decisiones técnicas y trade-offs

- **Modelos Gemini:** `gemini-3.1-flash-lite` (LLM) y `models/gemini-embedding-001` (embeddings) — actualizados respecto al stack original del caso práctico (`gemini-2.0-flash` y `text-embedding-004`) por descontinuación de esos modelos por parte de Google.
- **`chunk_size=1000` / `chunk_overlap=200` / `k=3`:** valores estándar razonables para documentos cortos como los de este proyecto; suficiente solapamiento para no perder contexto entre fragmentos sin generar demasiada redundancia.
- **Orquestador con `create_agent`** (no `AgentExecutor` + `create_tool_calling_agent`): esa API quedó deprecada en LangChain 1.x a favor de `create_agent`, basada internamente en LangGraph.
- **Registro de trazabilidad con `contextvars`** en vez de una variable global simple: necesario para que el Orquestador sea seguro ante requests concurrentes de FastAPI.
- **Deduplicación de fuentes** con `dict.fromkeys` (preserva orden de aparición, O(n)) para evitar fragmentos repetidos cuando dos agentes citan el mismo contenido.
- **Firma de duplicados del Agente de Acción con claves ordenadas alfabéticamente:** el diccionario `datos` lo arma un LLM, por lo que el orden de sus claves puede variar entre llamadas; ordenar antes de comparar evita falsos negativos en la detección de duplicados.
- **`marked.js` alojado localmente** (no vía CDN): evita que el renderizado de Markdown falle si la red del usuario bloquea dominios externos.

---

## Riesgos y mejoras futuras

- **Sin memoria conversacional real:** el backend es *stateless*; el historial que ve el usuario es solo visual en el navegador. Preguntas de seguimiento que dependan de contexto previo no lo tendrán disponible en el backend. Mejora futura: pasar el historial de mensajes al Orquestador o mantener sesión por usuario.
- **Sin agente multimodal de imagen:** se optó por implementar el Agente de Acción (opción B del caso) en vez del multimodal (opción A); ambos eran válidos y solo se requería uno.
- **Sin autenticación ni control de acceso:** cualquiera con acceso a la URL puede consultar o registrar solicitudes; para una versión productiva se necesitaría autenticación e identificar al colaborador real (hoy los datos se toman de lo que el usuario escribe en el chat).
- **Vector stores no se regeneran automáticamente:** si el contenido de `knowledge/*.txt` cambia, hay que borrar manualmente la carpeta correspondiente en `vectorstores/` para forzar la reindexación.
- **Concurrencia del Orquestador:** el aislamiento con `contextvars` funciona correctamente bajo el modelo de ejecución actual (rutas síncronas de FastAPI en threadpool); si el proyecto migrara a rutas async, convendría revalidar ese mecanismo.
- **`registro_solicitudes_rrhh.txt` como base de datos:** válido para un prototipo, pero no escala ni permite consultas complejas; una versión productiva usaría una base de datos real.
- **Monitoreo:** no se implementó registro de costos (tokens de Gemini), latencia ni feedback de usuarios — quedaría como trabajo futuro para una versión productiva.
