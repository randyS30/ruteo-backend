from app.services.metrics import centroide, haversine
import math

# Distancia máxima para considerar fusión de bloques enteros
MAX_MERGE_DISTANCE_KM = 5.0 

# Aumentamos el radio de transferencia para permitir movimientos más agresivos entre vecinos
MAX_TRANSFER_DISTANCE_KM = 6.0 

def fusionar_rutas(rutas, rango, target_n_rutas):
    """
    1. Fusión Espacial
    2. Reducción Forzada
    3. Balanceo Agresivo (Desbordamiento)
    """
    
    # --- FASE 1: Fusión Espacial (Idéntica a antes) ---
    SAFE_MAX = rango["max"]
    rutas_ok = []
    rutas_chicas = []

    for r in rutas:
        if len(r["pdvs"]) >= rango["min"]:
            rutas_ok.append(r)
        else:
            rutas_chicas.append(r)

    rutas_chicas.sort(key=lambda x: len(x["pdvs"]), reverse=True)
    rutas_pendientes = []

    while rutas_chicas:
        actual = rutas_chicas.pop(0)
        lat_c, lon_c = centroide(actual["pdvs"])
        mejor_match = None
        mejor_dist = float("inf")

        for r in rutas_ok:
            lat_r, lon_r = centroide(r["pdvs"])
            dist = haversine(lat_c, lon_c, lat_r, lon_r)
            if dist < mejor_dist and dist <= MAX_MERGE_DISTANCE_KM:
                if len(r["pdvs"]) + len(actual["pdvs"]) <= SAFE_MAX:
                    mejor_dist = dist
                    mejor_match = r
        
        if mejor_match:
            mejor_match["pdvs"].extend(actual["pdvs"])
            mejor_match["total_pdv"] = len(mejor_match["pdvs"])
        else:
            rutas_pendientes.append(actual)

    rutas_totales = rutas_ok + rutas_pendientes

    # --- FASE 2: Reducción Forzada (Idéntica a antes) ---
    LIMITE_ACEPTABLE = target_n_rutas + 1
    
    # Tolerancia extendida para casos de reducción forzada
    HARD_MAX = rango["promedio"] * 1.5 

    while len(rutas_totales) > LIMITE_ACEPTABLE:
        rutas_totales.sort(key=lambda x: len(x["pdvs"]))
        pequena = rutas_totales.pop(0)
        lat_p, lon_p = centroide(pequena["pdvs"])
        candidato_elegido = None
        candidatos = []
        
        for r in rutas_totales:
            lat_r, lon_r = centroide(r["pdvs"])
            dist = haversine(lat_p, lon_p, lat_r, lon_r)
            nuevo_total = len(r["pdvs"]) + len(pequena["pdvs"])
            candidatos.append({"ruta": r, "dist": dist, "nuevo_total": nuevo_total})

        candidatos.sort(key=lambda x: x["dist"])

        for c in candidatos:
            if c["nuevo_total"] <= SAFE_MAX:
                candidato_elegido = c["ruta"]; break
        
        if not candidato_elegido:
            for c in candidatos:
                if c["nuevo_total"] <= HARD_MAX:
                    candidato_elegido = c["ruta"]; break
        
        # Fallback: Unir al más cercano aunque se pase un poco, es mejor que dejar una ruta sola
        if not candidato_elegido and candidatos:
            candidato_elegido = candidatos[0]["ruta"]

        if candidato_elegido:
            candidato_elegido["pdvs"].extend(pequena["pdvs"])
            candidato_elegido["total_pdv"] = len(candidato_elegido["pdvs"])
        else:
            rutas_totales.append(pequena)
            break

    # --- FASE 3: BALANCEO AGRESIVO (Modificado) ---
    # Aquí es donde arreglamos el problema 44 vs 21
    rutas_totales = balancear_cargas_agresivo(rutas_totales, rango)

    # Reordenar IDs
    rutas_totales.sort(key=lambda x: len(x["pdvs"]), reverse=True)
    for i, r in enumerate(rutas_totales, start=1):
        r["ruta_id"] = i

    return rutas_totales


def balancear_cargas_agresivo(rutas, rango):
    """
    Busca equilibrar las cargas moviendo puntos desde las rutas más llenas
    hacia sus vecinos más vacíos, priorizando la proximidad al receptor.
    """
    PROMEDIO = rango["promedio"]
    # Umbral para considerar que una ruta está "llena" y debe donar
    UMBRAL_RICO = math.floor(PROMEDIO * 1.1) 
    # Umbral para considerar que una ruta necesita ayuda
    UMBRAL_POBRE = math.ceil(PROMEDIO * 0.9)

    # Iteramos más veces para asegurar que el flujo de puntos se propague
    for _ in range(10): 
        cambios_hechos = False
        
        # Ordenamos: Primero las rutas más cargadas
        rutas.sort(key=lambda x: len(x["pdvs"]), reverse=True)
        
        for donante in rutas:
            # Si no es "Rica", no dona
            if len(donante["pdvs"]) <= UMBRAL_RICO:
                continue
            
            lat_d, lon_d = centroide(donante["pdvs"])

            # Buscar vecinos "Pobres"
            vecinos_pobres = []
            for r in rutas:
                if r == donante: continue
                if len(r["pdvs"]) < PROMEDIO: # Si está bajo el promedio, acepta donaciones
                    lat_r, lon_r = centroide(r["pdvs"])
                    dist = haversine(lat_d, lon_d, lat_r, lon_r)
                    if dist <= MAX_MERGE_DISTANCE_KM * 1.5: # Buscamos vecinos en un radio amplio
                        vecinos_pobres.append({"ruta": r, "dist": dist, "centro": (lat_r, lon_r)})
            
            if not vecinos_pobres:
                continue

            # Ordenamos vecinos por cercanía al donante
            vecinos_pobres.sort(key=lambda x: x["dist"])
            
            # Intentamos donar al vecino más cercano que lo necesite
            mejor_vecino_info = vecinos_pobres[0]
            receptor = mejor_vecino_info["ruta"]
            lat_rec, lon_rec = mejor_vecino_info["centro"]

            # --- LÓGICA DE DESBORDAMIENTO ---
            # Ordenamos los puntos del DONANTE según su cercanía al RECEPTOR
            # Los que estén más cerca del receptor son los primeros en irse
            puntos_candidatos = sorted(
                donante["pdvs"], 
                key=lambda p: haversine(p["latitud"], p["longitud"], lat_rec, lon_rec)
            )

            puntos_a_mover = []
            
            # Cuantos puntos sobran?
            exceso = len(donante["pdvs"]) - PROMEDIO
            # Cuantos puntos faltan?
            falta = PROMEDIO - len(receptor["pdvs"])
            
            # Movemos lo que se pueda (el menor de los dos)
            cantidad_a_mover = min(exceso, falta, 5) # Movemos de 5 en 5 para ser graduales

            for pdv in puntos_candidatos:
                if len(puntos_a_mover) >= cantidad_a_mover:
                    break
                
                dist_al_receptor = haversine(pdv["latitud"], pdv["longitud"], lat_rec, lon_rec)
                
                # Solo movemos si está "alcanzable" (no mover puntos al extremo opuesto)
                if dist_al_receptor <= MAX_TRANSFER_DISTANCE_KM:
                    puntos_a_mover.append(pdv)

            # Ejecutar transferencia
            if puntos_a_mover:
                for p in puntos_a_mover:
                    if p in donante["pdvs"]:
                        donante["pdvs"].remove(p)
                        receptor["pdvs"].append(p)
                
                donante["total_pdv"] = len(donante["pdvs"])
                receptor["total_pdv"] = len(receptor["pdvs"])
                cambios_hechos = True
        
        if not cambios_hechos:
            break
            
    return rutas