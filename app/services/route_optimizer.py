import math

# Mantenemos tu función Haversine tal cual
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1 = math.radians(lat1), math.radians(lon1)
    lat2, lon2 = math.radians(lat2), math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def optimizar_orden_pdvs(pdvs):
    """
    Optimiza la ruta usando 'Nearest Neighbor' (Vecino más cercano).
    Esto evita el 'bucle de retorno' de OR-Tools y crea un camino 
    de serpiente mucho más natural para caminar.
    """
    
    # 1. Validaciones básicas
    if not pdvs:
        return []
    if len(pdvs) <= 2:
        for i, p in enumerate(pdvs, 1):
            p["orden"] = i
        return pdvs

    # 2. ESTRATEGIA DE INICIO:
    # Para evitar que empiece en el medio y haga espirales, forzamos
    # el inicio en el punto más al NORTE (Mayor Latitud).
    # En Perú (Hemisferio Sur), mayor latitud (más cercano a 0) es más al Norte.
    # Esto garantiza un "barrido" ordenado de arriba a abajo.
    start_node = max(pdvs, key=lambda p: p['latitud'])
    
    ruta_ordenada = [start_node]
    
    # Creamos una lista de pendientes (excluyendo el inicial)
    pendientes = [p for p in pdvs if p != start_node]

    current_node = start_node

    # 3. ALGORITMO VORAZ (GREEDY)
    while pendientes:
        # Buscamos el punto más cercano al actual
        # Usamos tu función haversine para calcular la distancia real
        siguiente_mas_cercano = min(
            pendientes,
            key=lambda p: haversine(
                current_node['latitud'], current_node['longitud'], 
                p['latitud'], p['longitud']
            )
        )
        
        # Lo agregamos a la ruta y lo sacamos de pendientes
        ruta_ordenada.append(siguiente_mas_cercano)
        pendientes.remove(siguiente_mas_cercano)
        
        # Avanzamos
        current_node = siguiente_mas_cercano

    # 4. ASIGNAR ORDEN FINAL
    for i, pdv in enumerate(ruta_ordenada, 1):
        pdv["orden"] = i

    return ruta_ordenada

def ordenar_y_marcar(pdvs):
    """
    Wrapper estable para el sistema
    """
    return optimizar_orden_pdvs(pdvs)