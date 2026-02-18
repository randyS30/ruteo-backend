import h3

def clusterizar_por_h3(puntos, resolution=9):
    """
    puntos: list[dict] -> {id, lat, lon}
    return: dict[h3_index] -> list[puntos]
    """
    clusters = {}

    for p in puntos:
        h3_index = h3.geo_to_h3(p["lat"], p["lon"], resolution)

        if h3_index not in clusters:
            clusters[h3_index] = []

        clusters[h3_index].append(p)

    return clusters
