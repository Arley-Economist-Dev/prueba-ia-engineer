"""
Paquete principal de motores analíticos e IA para Grupo Casa Pellas:
- caso1_engine: Planificación e Investigación de Operaciones para Pedido de Vehículos Nuevos (Toyota).
- caso2_engine: Diagnóstico Operativo, Machine Learning P(Fuga) y Simulación de 3 Carriles para Renovaciones Capesa.
"""

from . import caso1_engine
from . import caso2_engine

__all__ = ["caso1_engine", "caso2_engine"]

