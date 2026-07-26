"""
Pruebas del Agente Orquestador.
Ejecutar desde la raíz del proyecto con: python tests/test_orchestrator.py

Cubre:
- Caso 1: Beneficios
- Caso 2: Políticas
- Caso 3: Reclutamiento
- Caso 4: Beneficios + Políticas (mixta)
- Caso 5: Beneficios + Reclutamiento (mixta)
- Caso 6: Pregunta fuera de contexto (sin información suficiente)
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator import responder, MENSAJE_SIN_INFORMACION

AGENTE_BENEFICIOS = "Agente de Beneficios y Compensaciones"
AGENTE_POLITICAS = "Agente de Políticas Internas"
AGENTE_RECLUTAMIENTO = "Agente de Reclutamiento y Onboarding"

CASOS_PRUEBA = [
    {
        "nombre": "Caso 1: Beneficios",
        "pregunta": "¿Qué cubre el seguro médico corporativo?",
        "agentes_esperados": {AGENTE_BENEFICIOS},
    },
    {
        "nombre": "Caso 2: Políticas",
        "pregunta": "¿Cuántos días de vacaciones me corresponden al año?",
        "agentes_esperados": {AGENTE_POLITICAS},
    },
    {
        "nombre": "Caso 3: Reclutamiento",
        "pregunta": "¿Cómo funciona el programa de referidos?",
        "agentes_esperados": {AGENTE_RECLUTAMIENTO},
    },
    {
        "nombre": "Caso 4: Beneficios + Políticas",
        "pregunta": (
            "Voy a tomar mis vacaciones y además quiero agregar a mi pareja al seguro "
            "médico. ¿Cuántos días me corresponden y qué necesito para inscribir a un "
            "dependiente en el beneficio?"
        ),
        "agentes_esperados": {AGENTE_BENEFICIOS, AGENTE_POLITICAS},
    },
    {
        "nombre": "Caso 5: Beneficios + Reclutamiento",
        "pregunta": (
            "Si refiero a un candidato y es contratado, ¿recibo un bono? y en general, "
            "¿qué bonos ofrece la empresa aparte de ese?"
        ),
        "agentes_esperados": {AGENTE_BENEFICIOS, AGENTE_RECLUTAMIENTO},
    },
    {
        "nombre": "Caso 6: Fuera de contexto",
        "pregunta": "¿Cuál es la capital de Francia?",
        "agentes_esperados": set(),
    },
]


def probar_orquestador():
    """Envía cada caso al orquestador y valida estructura, agentes invocados y fuentes."""
    for caso in CASOS_PRUEBA:
        resultado = responder(caso["pregunta"])

        print(f"\n{caso['nombre']}")
        print(f"Pregunta: {caso['pregunta']}")
        print(f"Agentes participantes: {resultado['agentes_participantes']}")
        print(f"Respuesta: {resultado['respuesta']}")
        print(f"Fuentes usadas: {len(resultado['fuentes'])}")

        # Estructura del contrato del orquestador
        assert "respuesta" in resultado
        assert "agentes_participantes" in resultado
        assert "fuentes" in resultado
        assert isinstance(resultado["respuesta"], str) and resultado["respuesta"].strip()
        assert isinstance(resultado["agentes_participantes"], list)
        assert isinstance(resultado["fuentes"], list)

        agentes_obtenidos = set(resultado["agentes_participantes"])

        if caso["agentes_esperados"]:
            # Debe haber invocado exactamente los agentes esperados (ni de más ni de menos)
            assert agentes_obtenidos == caso["agentes_esperados"], (
                f"Se esperaban {caso['agentes_esperados']} y se obtuvieron {agentes_obtenidos}"
            )
            assert len(resultado["fuentes"]) > 0
        else:
            # Caso fuera de dominio: no debe invocar ningún agente y debe usar el
            # mensaje estándar exacto exigido por el caso práctico.
            assert agentes_obtenidos == set()
            assert resultado["respuesta"] == MENSAJE_SIN_INFORMACION
            assert resultado["fuentes"] == []


if __name__ == "__main__":
    probar_orquestador()
    print("\nTodas las pruebas del orquestador pasaron correctamente.")
    