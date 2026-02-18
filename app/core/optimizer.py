import numpy as np
from sklearn.cluster import KMeans


def optimizar_rutas_custom(puntos, num_rutas, rango):
    coords = np.array([[p["lat"], p["lon"]] for p in puntos])

    if len(coords) <= num_rutas:
        return [[p] for p in puntos]

    kmeans = KMeans(n_clusters=num_rutas, random_state=42)
    labels = kmeans.fit_predict(coords)

    rutas = {i: [] for i in range(num_rutas)}

    for idx, label in enumerate(labels):
        rutas[label].append(puntos[idx])

    rutas_balanceadas = []
    sobrantes = []

    for ruta in rutas.values():
        if len(ruta) > rango["max"]:
            rutas_balanceadas.append(ruta[:rango["max"]])
            sobrantes.extend(ruta[rango["max"]:])
        else:
            rutas_balanceadas.append(ruta)

    for p in sobrantes:
        for ruta in rutas_balanceadas:
            if len(ruta) < rango["min"]:
                ruta.append(p)
                break

    return rutas_balanceadas
