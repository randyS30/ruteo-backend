from collections import defaultdict
import math

from app.services.h3_utils import asignar_h3
from app.services.clustering import clusterizar_rutas
# Ya no necesitamos importar fusionar_rutas aquí porque lo usa clustering internamente
from app.services.route_optimizer import optimizar_orden_pdvs
from app.services.metrics import evaluar_ruta

def construir_rutas(df, frecuencia: str, sabado: bool, flex: float):
    """
    Construye rutas por mercaderista usando:
    H3 -> Clustering -> Fusión Espacial -> Reducción Forzada -> Balance Final
    """

    resultado = {
        "frecuencia": frecuencia.upper(),
        "sabado": sabado,
        "flex": flex,
        "mercaderistas": []
    }

    # 1. Agrupar por mercaderista
    for vendedor, df_vendedor in df.groupby("NOMBRE_VENDEDOR"):
        total_pdv = len(df_vendedor)

        # 2. Calcular número de rutas (Target)
        if frecuencia.upper() == "SEMANAL":
            num_rutas = 6 if sabado else 5
        elif frecuencia.upper() == "QUINCENAL":
            num_rutas = 12 if sabado else 10
        else: # MENSUAL
            num_rutas = 24 if sabado else 20

        # 🔐 No permitir más rutas que PDVs (caso bordes extremos)
        num_rutas = min(num_rutas, total_pdv)

        # Cálculo del Rango (Promedio, Min, Max)
        promedio = total_pdv / num_rutas if num_rutas > 0 else 0
        rango = {
            "promedio": round(promedio, 2),
            "min": max(1, math.floor(promedio * (1 - flex))),
            "max": math.ceil(promedio * (1 + flex))
        }

        # 3. Asignar H3 (Resolution 9 para mayor precisión zonal)
        df_h3 = asignar_h3(df_vendedor, resolution=9)

        # 4. Clustering Inteligente (Incluye la fusión y reducción forzada)
        # Aquí pasamos 'num_rutas' para que el algoritmo sepa cuánto debe reducir
        rutas = clusterizar_rutas(
            df=df_h3,
            num_rutas=num_rutas,
            rango=rango
        )

        # 5. Optimización final de cada ruta resultante
        for ruta in rutas:
            # A. Optimizar orden interno (Viajero Comerciante - TSP)
            ruta["pdvs"] = optimizar_orden_pdvs(ruta["pdvs"])

            # B. Calcular métricas finales (Distancia real, tiempos)
            metricas = evaluar_ruta(ruta, rango)
            ruta.update(metricas)

            # C. Asegurar totales
            ruta["total_pdv"] = len(ruta["pdvs"])

        # Agregamos al resultado final
        resultado["mercaderistas"].append({
            "mercaderista": vendedor,
            "total_pdv": total_pdv,
            "num_rutas": len(rutas),
            "rango": rango,
            "rutas": rutas
        })

    return resultado