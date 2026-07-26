"""
Pruebas del Agente de Acción (lógica de negocio, sin LLM).
Ejecutar desde la raíz del proyecto con: python tests/test_accion_agent.py
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.accion_agent import registrar_solicitud, RUTA_REGISTRO

DATOS_VACACIONES_COMPLETOS = {
    "nombre_colaborador": "Ana Torres",
    "fecha_inicio": "2026-09-01",
    "fecha_fin": "2026-09-05",
    "numero_dias": "5",
    "jefe_aprueba": "Carlos Ruiz",
}

DATOS_VACACIONES_INCOMPLETOS = {
    "nombre_colaborador": "Ana Torres",
    "fecha_inicio": "2026-09-01",
}

DATOS_DEPENDIENTE_COMPLETOS = {
    "nombre_dependiente": "Sofía Torres",
    "vinculo": "hija",
    "documentos_respaldo": "partida de nacimiento",
}


def _limpiar_archivo_de_prueba():
    if os.path.exists(RUTA_REGISTRO):
        os.remove(RUTA_REGISTRO)


def probar_tipo_no_reconocido():
    resultado = registrar_solicitud("permiso_medico", {}, confirmado=True)
    assert resultado["estado"] == "error"
    print("OK - tipo no reconocido:", resultado["mensaje"])


def probar_datos_faltantes():
    resultado = registrar_solicitud("vacaciones", DATOS_VACACIONES_INCOMPLETOS, confirmado=True)
    assert resultado["estado"] == "faltan_datos"
    assert "numero_dias" in resultado["mensaje"]
    print("OK - datos faltantes:", resultado["mensaje"])


def probar_pendiente_confirmacion():
    resultado = registrar_solicitud("vacaciones", DATOS_VACACIONES_COMPLETOS, confirmado=False)
    assert resultado["estado"] == "pendiente_confirmacion"
    print("OK - pendiente de confirmación:", resultado["mensaje"])


def probar_registro_exitoso_vacaciones():
    resultado = registrar_solicitud("vacaciones", DATOS_VACACIONES_COMPLETOS, confirmado=True)
    assert resultado["estado"] == "registrado"
    assert "id" in resultado and len(resultado["id"]) == 8
    assert os.path.exists(RUTA_REGISTRO)
    print("OK - registro exitoso (vacaciones):", resultado["mensaje"])


def probar_registro_exitoso_dependiente():
    resultado = registrar_solicitud("dependiente", DATOS_DEPENDIENTE_COMPLETOS, confirmado=True)
    assert resultado["estado"] == "registrado"
    print("OK - registro exitoso (dependiente):", resultado["mensaje"])


def probar_duplicado():
    # Ya se registró antes en probar_registro_exitoso_vacaciones()
    resultado = registrar_solicitud("vacaciones", DATOS_VACACIONES_COMPLETOS, confirmado=True)
    assert resultado["estado"] == "duplicado"
    print("OK - duplicado detectado:", resultado["mensaje"])


def probar_advertencia_anticipacion():
    datos_sin_anticipacion = dict(DATOS_VACACIONES_COMPLETOS)
    datos_sin_anticipacion["fecha_inicio"] = "2026-07-22"  
    datos_sin_anticipacion["fecha_fin"] = "2026-07-25"
    resultado = registrar_solicitud("vacaciones", datos_sin_anticipacion, confirmado=False)
    assert resultado["estado"] == "pendiente_confirmacion"
    assert "Advertencia" in resultado["mensaje"]
    print("OK - advertencia de anticipación:", resultado["mensaje"])


if __name__ == "__main__":
    _limpiar_archivo_de_prueba()

    probar_tipo_no_reconocido()
    probar_datos_faltantes()
    probar_pendiente_confirmacion()
    probar_registro_exitoso_vacaciones()
    probar_registro_exitoso_dependiente()
    probar_duplicado()
    probar_advertencia_anticipacion()

    print("\nTodas las pruebas del Agente de Acción pasaron correctamente.")
    print(f"Revisa el archivo generado en: {RUTA_REGISTRO}")
