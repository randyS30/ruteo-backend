import numpy as np
from sklearn.cluster import KMeans
def kmeans_por_cluster(pdvs, n_clusters):
    if len(pdvs) <= n_clusters:
        return [[p] for p in pdvs]

    coords = np.array([[p["lat"], p["lng"]] for p in pdvs])

    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=42,
        n_init=10
    )

    labels = kmeans.fit_predict(coords)

    rutas = {}
    for label, pdv in zip(labels, pdvs):
        rutas.setdefault(label, []).append(pdv)

    return list(rutas.values())
