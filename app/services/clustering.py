from collections import defaultdict
import math
import numpy as np
from sklearn.cluster import KMeans

# IMPORTANTE: Importamos la fusión inteligente en lugar de usar la función "ciega" interna
from app.services.routes_merges import fusionar_rutas

def serializar_pdv(row):
    return {
        "cod_live_tra": row["COD_LIVE_TRA"],
        "razon_social": row["RAZON_SOCIAL"],
        "subcanal": row.get("SUBCANAL"),
        "latitud": row["LATITUD"],
        "longitud": row["LONGITUD"],
        "distrito": row["DISTRITO"],
        "h3": row["h3_index"]
    }

def clusterizar_rutas(df, num_rutas: int, rango: dict):
    rutas_finales = []
    ruta_id_counter = 1

    # 1. Agrupar por H3 (macro zonas)
    h3_groups = df.groupby("h3_index")

    for h3_index, grupo in h3_groups:
        total = len(grupo)
        
        # Preparamos los datos serializados para no repetir código
        puntos_grupo = [serializar_pdv(r) for _, r in grupo.iterrows()]

        # 2. Caso ideal: entra en rango (ni muy chico ni muy grande)
        if rango["min"] <= total <= rango["max"]:
            rutas_finales.append({
                "ruta_id": ruta_id_counter,
                "total_pdv": total,
                "pdvs": puntos_grupo
            })
            ruta_id_counter += 1
            continue

        # 3. Caso grande: subdividir con KMeans
        if total > rango["max"]:
            # Calculamos k particiones basado en el promedio deseado
            # Usamos np.ceil para asegurar que no queden muy apretados
            k = math.ceil(total / rango["promedio"])
            
            # Extraemos coordenadas para el algoritmo
            coords = grupo[["LATITUD", "LONGITUD"]].values

            kmeans = KMeans(
                n_clusters=k,
                random_state=42,
                n_init="auto"
            )
            labels = kmeans.fit_predict(coords)

            # Subdividimos los puntos según la etiqueta que les dio KMeans
            sub_clusters = defaultdict(list)
            for idx, label in enumerate(labels):
                sub_clusters[label].append(puntos_grupo[idx])

            # Creamos las sub-rutas
            for sub_puntos in sub_clusters.values():
                rutas_finales.append({
                    "ruta_id": ruta_id_counter,
                    "total_pdv": len(sub_puntos),
                    "pdvs": sub_puntos
                })
                ruta_id_counter += 1

        # 4. Caso chico: Lo agregamos tal cual, la fusión inteligente se encargará después
        else:
            rutas_finales.append({
                "ruta_id": ruta_id_counter,
                "total_pdv": total,
                "pdvs": puntos_grupo
            })
            ruta_id_counter += 1

    # =========================================================================
    # AQUÍ ESTÁ LA MAGIA: 
    # En lugar de llamar a la función interna que unía a ciegas,
    # llamamos a 'fusionar_rutas' del archivo routes_merges.py
    # que tiene la validación de distancia (MAX_MERGE_DISTANCE_KM).
    # =========================================================================
    
    rutas_optimizadas = fusionar_rutas(
        rutas=rutas_finales, 
        rango=rango, 
        target_n_rutas=num_rutas  # <--- Este es el dato clave para evitar las 40 rutas
    )
    
    return rutas_optimizadas