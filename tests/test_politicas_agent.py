"""
Pruebas del Agente de Políticas.
Ejecutar desde la raíz del proyecto con:
python tests/test_politicas_agent.py
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.politicas_agent import responder

PREGUNTAS_PRUEBA = [
    "¿Cuál es la jornada laboral?",
    "¿Cuántos días de vacaciones tengo?",
    "¿Cómo solicito vacaciones?",
    "¿Qué tipos de permisos existen?",
    "¿Qué dice el código de conducta?",
    "¿Qué sanciones existen?",
]


def probar_agente():
    """Envía varias preguntas al agente y valida que la estructura de la respuesta sea correcta."""
    for pregunta in PREGUNTAS_PRUEBA:
        resultado = responder(pregunta)

        print(f"\nPregunta: {pregunta}")
        print(f"Agente: {resultado['agente']}")
        print(f"Respuesta: {resultado['respuesta']}")
        print(f"Fuentes usadas: {len(resultado['fuentes'])}")

        assert resultado["agente"] == "Agente de Políticas Internas"
        assert isinstance(resultado["respuesta"], str) and resultado["respuesta"].strip()
        assert isinstance(resultado["fuentes"], list)


if __name__ == "__main__":
    probar_agente()
    print("\nTodas las pruebas pasaron correctamente.")
    