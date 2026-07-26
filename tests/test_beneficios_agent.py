"""
Pruebas del Agente de Beneficios y Compensaciones.
Ejecutar desde la raíz del proyecto con: python tests/test_beneficios_agent.py
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.beneficios_agent import responder

PREGUNTAS_PRUEBA = [
    "¿Cómo agrego un dependiente a mi seguro médico?",
    "¿Qué cubre el seguro médico corporativo?",
    "¿Cada cuánto se revisan las salariales?",
    "¿Qué otros beneficios tengo aparte del seguro médico?",
    "¿Cuántos días tengo para inscribir a un dependiente tras casarme?",
]


def probar_agente():
    """Envía varias preguntas al agente y valida que la estructura de la respuesta sea correcta."""
    for pregunta in PREGUNTAS_PRUEBA:
        resultado = responder(pregunta)

        print(f"\nPregunta: {pregunta}")
        print(f"Agente: {resultado['agente']}")
        print(f"Respuesta: {resultado['respuesta']}")
        print(f"Fuentes usadas: {len(resultado['fuentes'])}")

        assert resultado["agente"] == "Agente de Beneficios y Compensaciones"
        assert isinstance(resultado["respuesta"], str) and resultado["respuesta"].strip()
        assert isinstance(resultado["fuentes"], list)


if __name__ == "__main__":
    probar_agente()
    print("\nTodas las pruebas pasaron correctamente.")
