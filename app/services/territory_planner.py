import math
import pandas as pd
from app.services.h3_utils import asignar_h3
from app.services.clustering import clusterizar_rutas
from app.services.route_optimizer import optimizar_orden_pdvs
from app.services.metrics import evaluar_ruta, haversine

def resolver_colisiones_golpeo(rutas):
    # ... (Tu función resolver_colisiones_golpeo queda EXACTAMENTE IGUAL) ...
    # 1. Calcular centroides de cada ruta para saber cuáles están cerca
    centroides = {}
    for ruta in rutas:
        if ruta["pdvs"]:
            lats = [p["latitud"] for p in ruta["pdvs"]]
            lons = [p["longitud"] for p in ruta["pdvs"]]
            centroides[ruta["ruta_id"]] = {
                "lat": sum(lats) / len(lats),
                "lon": sum(lons) / len(lons)
            }
        else:
            centroides[ruta["ruta_id"]] = {"lat": 0, "lon": 0}

    # 2. Iterar para limpiar duplicados
    # Hacemos un par de pasadas para asegurar que se acomoden bien
    for _ in range(2): 
        cambio_realizado = False
        
        for ruta_origen in rutas:
            ids_vistos = set()
            pdvs_unicos = []
            pdvs_a_mover = []

            # Separar los que se quedan de los que sobran (duplicados)
            for pdv in ruta_origen["pdvs"]:
                cod = pdv["cod_live_tra"]
                if cod in ids_vistos:
                    pdvs_a_mover.append(pdv) # Ya existe en esta ruta, ¡fuera!
                    cambio_realizado = True
                else:
                    ids_vistos.add(cod)
                    pdvs_unicos.append(pdv)
            
            # Si encontramos duplicados, actualizamos la ruta y buscamos hogar a los huerfanos
            if pdvs_a_mover:
                ruta_origen["pdvs"] = pdvs_unicos
                
                for pdv_move in pdvs_a_mover:
                    mejor_ruta = None
                    menor_distancia = float('inf')
                    
                    # Buscar la mejor ruta vecina
                    for ruta_destino in rutas:
                        if ruta_destino["ruta_id"] == ruta_origen["ruta_id"]:
                            continue
                        
                        # REGLA DE ORO: La ruta destino NO debe tener ya a este cliente
                        dest_ids = {p["cod_live_tra"] for p in ruta_destino["pdvs"]}
                        if pdv_move["cod_live_tra"] in dest_ids:
                            continue 
                        
                        # Calcular cercanía entre rutas
                        c1 = centroides[ruta_origen["ruta_id"]]
                        c2 = centroides[ruta_destino["ruta_id"]]
                        dist = haversine(c1['lat'], c1['lon'], c2['lat'], c2['lon'])
                        
                        if dist < menor_distancia:
                            menor_distancia = dist
                            mejor_ruta = ruta_destino
                    
                    # Asignar a la nueva ruta o devolver (si no hay opción)
                    if mejor_ruta:
                        mejor_ruta["pdvs"].append(pdv_move)
                    else:
                        # Caso extremo: Golpeo > Cantidad total de rutas (imposible separar)
                        ruta_origen["pdvs"].append(pdv_move) 

    return rutas

def planificar_bolsa_grandes(df, capacidad_objetivo: int, flex: float, sabado_activo: bool = False):
    """
    Planifica territorios agrupando por Departamento.
    
    CAMBIO LÓGICO:
    - Si sabado_activo = True:
      Calculamos que en un ciclo de 6 personas, 5 son Full y 1 es Half.
      Esto reduce la capacidad efectiva promedio a un 91.6%.
      Esto obliga a generar MÁS RUTAS (Headcount) para cubrir los mismos puntos.
    """
    resultado = {
        "frecuencia": "TERRITORIO", 
        "sabado": False,
        "flex": flex,
        "mercaderistas": []
    }

    # AJUSTE DE CAPACIDAD POR SÁBADO (HEADCOUNT)
    capacidad_calculo = capacidad_objetivo
    if sabado_activo:
        # Factor = (5.5 jornadas efectivas) / (6 personas) = 0.916
        capacidad_calculo = int(capacidad_objetivo * 0.916)

    # Agrupamos por lo que el Parser definió como VENDEDOR (ej. "ANCASH", "AREQUIPA")
    for zona, df_zona in df.groupby("NOMBRE_VENDEDOR"):
        
        # 1. EXPANSIÓN POR GOLPEO (MULTIPLICACIÓN)
        df_expandido = df_zona.loc[df_zona.index.repeat(df_zona['GOLPEO'])].copy()
        total_visitas = len(df_expandido)
        clientes_unicos = len(df_zona)
        
        if total_visitas == 0: continue

        # 2. CÁLCULO DE RUTAS (Usando la capacidad ajustada)
        num_rutas = math.ceil(total_visitas / capacidad_calculo)
        if num_rutas < 1: num_rutas = 1
        
        rango = {
            "promedio": capacidad_calculo,
            "min": math.floor(capacidad_calculo * (1 - flex)),
            "max": math.ceil(capacidad_calculo * (1 + flex))
        }

        # 3. PROCESO DE RUTEO
        df_h3 = asignar_h3(df_expandido, resolution=9) # Resolución fina

        rutas = clusterizar_rutas(
            df=df_h3,
            num_rutas=num_rutas,
            rango=rango
        )

        # 4. RESOLUCIÓN DE COLISIONES
        if num_rutas > 1:
            rutas = resolver_colisiones_golpeo(rutas)

        # 5. OPTIMIZACIÓN FINAL (TSP)
        for ruta in rutas:
            ruta["pdvs"] = optimizar_orden_pdvs(ruta["pdvs"])
            metricas = evaluar_ruta(ruta, rango)
            ruta.update(metricas)
            ruta["total_pdv"] = len(ruta["pdvs"])

        # 6. Guardar Resultado
        resultado["mercaderistas"].append({
            "mercaderista": zona, 
            "total_pdv": total_visitas,
            "clientes_unicos": clientes_unicos,
            "num_rutas": len(rutas),
            "capacidad_objetivo_usada": capacidad_calculo, # Dato útil para ver el ajuste
            "rango": rango,
            "rutas": rutas
        })

    return resultado