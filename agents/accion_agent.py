"""
Agente de Acción de RR. HH.

Gestiona el registro de solicitudes (vacaciones y dependientes), validando
los datos obligatorios, solicitando confirmación, evitando duplicados y
almacenando cada solicitud en el archivo de registros.

Este módulo es independiente del Orquestador y expone la herramienta
registrar_solicitud_rrhh().
"""

import os
import uuid
from datetime import datetime, date

NOMBRE_AGENTE = "Agente de Acción (Registro de Solicitudes)"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_REGISTRO = os.path.join(BASE_DIR, "registro_solicitudes_rrhh.txt")

# Configuración extensible: para agregar un nuevo tipo de solicitud, solo se
# agrega una entrada aquí con sus campos obligatorios. Nada más del archivo cambia.
CAMPOS_REQUERIDOS = {
    "vacaciones": [
        "nombre_colaborador",
        "fecha_inicio",
        "fecha_fin",
        "numero_dias",
        "jefe_aprueba",
    ],
    "dependiente": [
        "nombre_dependiente",
        "vinculo",
        "documentos_respaldo",
    ],
}

DIAS_ANTICIPACION_VACACIONES = 15
FORMATO_FECHA = "%Y-%m-%d"


def _tipos_disponibles() -> str:
    return ", ".join(CAMPOS_REQUERIDOS.keys())


def _validar_campos_presentes(tipo_solicitud: str, datos: dict) -> list:
    """Devuelve la lista de campos obligatorios que faltan o están vacíos."""
    requeridos = CAMPOS_REQUERIDOS[tipo_solicitud]
    faltantes = []
    for campo in requeridos:
        valor = datos.get(campo)
        if valor is None or str(valor).strip() == "":
            faltantes.append(campo)
    return faltantes


def _validar_anticipacion_vacaciones(datos: dict) -> str:
    """Verifica la regla de negocio de 15 días de anticipación (no bloquea el registro en este prototipo, solo agrega una advertencia informativa)."""
    fecha_inicio_str = datos.get("fecha_inicio", "")
    try:
        fecha_inicio = datetime.strptime(fecha_inicio_str, FORMATO_FECHA).date()
    except (ValueError, TypeError):
        return "No se pudo verificar la anticipación: 'fecha_inicio' debe tener formato AAAA-MM-DD."

    dias_de_anticipacion = (fecha_inicio - date.today()).days
    if dias_de_anticipacion < DIAS_ANTICIPACION_VACACIONES:
        return (
            f"Advertencia: la solicitud se está haciendo con {dias_de_anticipacion} día(s) "
            f"de anticipación; el reglamento interno pide un mínimo de "
            f"{DIAS_ANTICIPACION_VACACIONES} días."
        )
    return ""


def _generar_id() -> str:
    return uuid.uuid4().hex[:8]


def _bloque_tipo_y_datos(tipo_solicitud: str, datos: dict) -> str:
    """Genera el bloque de texto con el tipo de solicitud y sus datos.
    Se reutiliza tanto para guardar el registro como para validar duplicados.
    """
    lineas_datos = "\n".join(f"  - {campo}: {valor}" for campo, valor in sorted(datos.items()))
    return f"Tipo de solicitud: {tipo_solicitud}\nDatos:\n{lineas_datos}"


def _formatear_registro(id_solicitud: str, tipo_solicitud: str, datos: dict) -> str:
    marca_tiempo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "=" * 70 + "\n"
        f"ID: {id_solicitud}\n"
        f"Fecha y hora de registro: {marca_tiempo}\n"
        f"{_bloque_tipo_y_datos(tipo_solicitud, datos)}\n"
        + "=" * 70 + "\n"
    )


def _ya_existe_solicitud_identica(tipo_solicitud: str, datos: dict) -> bool:
    """Evita duplicados: compara tipo + valores de datos contra registros existentes."""
    if not os.path.exists(RUTA_REGISTRO):
        return False

    try:
        with open(RUTA_REGISTRO, "r", encoding="utf-8") as archivo:
            contenido = archivo.read()
    except OSError:
        # Si no se puede leer el archivo para comparar, se prefiere no bloquear
        # el registro; el error real de escritura se maneja aparte.
        return False

    firma = _bloque_tipo_y_datos(tipo_solicitud, datos)
    return firma in contenido


def registrar_solicitud(tipo_solicitud: str, datos: dict, confirmado: bool = False) -> dict:
    """Procesa una solicitud de RR. HH.
    Retorna el estado de la operación y el mensaje correspondiente.
    """
    tipo_solicitud = (tipo_solicitud or "").strip().lower()
    datos = datos or {}

    if tipo_solicitud not in CAMPOS_REQUERIDOS:
        return {
            "estado": "error",
            "mensaje": (
                f"Tipo de solicitud '{tipo_solicitud}' no reconocido. "
                f"Tipos disponibles: {_tipos_disponibles()}."
            ),
        }

    faltantes = _validar_campos_presentes(tipo_solicitud, datos)
    if faltantes:
        return {
            "estado": "faltan_datos",
            "mensaje": (
                f"Antes de registrar la solicitud de {tipo_solicitud}, falta indicar: "
                f"{', '.join(faltantes)}."
            ),
        }

    if _ya_existe_solicitud_identica(tipo_solicitud, datos):
        return {
            "estado": "duplicado",
            "mensaje": "Ya existe una solicitud registrada con exactamente estos mismos datos.",
        }

    advertencia = ""
    if tipo_solicitud == "vacaciones":
        advertencia = _validar_anticipacion_vacaciones(datos)

    if not confirmado:
        resumen = "; ".join(f"{campo}: {valor}" for campo, valor in datos.items())
        mensaje = f"Vas a registrar una solicitud de {tipo_solicitud} con estos datos: {resumen}. "
        if advertencia:
            mensaje += advertencia + " "
        mensaje += "¿Confirmas el registro?"
        return {"estado": "pendiente_confirmacion", "mensaje": mensaje}

    id_solicitud = _generar_id()
    try:
        with open(RUTA_REGISTRO, "a", encoding="utf-8") as archivo:
            archivo.write(_formatear_registro(id_solicitud, tipo_solicitud, datos))
    except OSError as error:
        return {
            "estado": "error",
            "mensaje": f"No se pudo escribir el registro en el archivo: {error}",
        }

    mensaje = f"Solicitud de {tipo_solicitud} registrada con éxito. ID: {id_solicitud}."
    if advertencia:
        mensaje += " " + advertencia
    return {"estado": "registrado", "mensaje": mensaje, "id": id_solicitud}


def listar_solicitudes() -> list:
    """Lee y parsea registro_solicitudes_rrhh.txt .
    No modifica el archivo ni valida nada; es exclusivamente para mostrar al
    usuario lo que ya fue registrado. Reutiliza el mismo separador y formato
    de línea que escribe _formatear_registro, así que el parser no se puede
    desincronizar del escritor (mismo principio que _bloque_tipo_y_datos).

    Retorna una lista de dicts, más reciente primero:
    [{"id": "...", "fecha_hora": "...", "tipo_solicitud": "...", "datos": {...}}, ...]
    Si el archivo no existe o está vacío, retorna una lista vacía.
    """
    if not os.path.exists(RUTA_REGISTRO):
        return []

    try:
        with open(RUTA_REGISTRO, "r", encoding="utf-8") as archivo:
            contenido = archivo.read()
    except OSError:
        return []

    separador = "=" * 70
    bloques = [bloque.strip() for bloque in contenido.split(separador) if bloque.strip()]

    solicitudes = []
    for bloque in bloques:
        registro = {"id": "", "fecha_hora": "", "tipo_solicitud": "", "datos": {}}
        for linea in bloque.splitlines():
            linea = linea.strip()
            if not linea or linea == "Datos:":
                continue
            if linea.startswith("ID:"):
                registro["id"] = linea.split(":", 1)[1].strip()
            elif linea.startswith("Fecha y hora de registro:"):
                registro["fecha_hora"] = linea.split(":", 1)[1].strip()
            elif linea.startswith("Tipo de solicitud:"):
                registro["tipo_solicitud"] = linea.split(":", 1)[1].strip()
            elif linea.startswith("- ") and ":" in linea:
                campo, valor = linea[2:].split(":", 1)
                registro["datos"][campo.strip()] = valor.strip()

        if registro["id"]:
            solicitudes.append(registro)

    return list(reversed(solicitudes))


if __name__ == "__main__":
    datos_prueba = {
        "nombre_colaborador": "Juan Pérez",
        "fecha_inicio": "2026-08-01",
        "fecha_fin": "2026-08-07",
        "numero_dias": "5",
        "jefe_aprueba": "María Gómez",
    }
    print("Sin confirmar:", registrar_solicitud("vacaciones", datos_prueba, confirmado=False))
    print("Confirmando:", registrar_solicitud("vacaciones", datos_prueba, confirmado=True))
    print("Duplicado:", registrar_solicitud("vacaciones", datos_prueba, confirmado=True))
