"""
Pruebas del Agente de Reclutamiento y Onboarding.
Ejecutar desde la raíz del proyecto con: python tests/test_reclutamiento_agent.py
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.reclutamiento_agent import responder

PREGUNTAS_PRUEBA = [
    "¿Cuáles son los pasos del proceso de selección?",
    "¿Cómo funciona el programa de referidos?",
    "¿Aplica el bono de referido para posiciones de dirección?",
    "¿Qué pasa en el primer día de onboarding?",
    "¿Qué es el plan 30-60-90 días?",
    "¿Qué documentos se piden al ingresar?",
]


def probar_agente():
    """Envía varias preguntas al agente y valida que la estructura de la respuesta sea correcta."""
    for pregunta in PREGUNTAS_PRUEBA:
        resultado = responder(pregunta)

        print(f"\nPregunta: {pregunta}")
        print(f"Agente: {resultado['agente']}")
        print(f"Respuesta: {resultado['respuesta']}")
        print(f"Fuentes usadas: {len(resultado['fuentes'])}")

        assert resultado["agente"] == "Agente de Reclutamiento y Onboarding"
        assert isinstance(resultado["respuesta"], str) and resultado["respuesta"].strip()
        assert isinstance(resultado["fuentes"], list)


if __name__ == "__main__":
    probar_agente()
    print("\nTodas las pruebas pasaron correctamente.")
    