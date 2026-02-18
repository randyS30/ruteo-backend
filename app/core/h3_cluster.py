import h3
def agrupar_por_h3(pdvs, resolution=9):
    clusters = {}

    for p in pdvs:
        h3_index = h3.latlng_to_cell(
            p["lat"],
            p["lng"],
            resolution
        )
        clusters.setdefault(h3_index, []).append(p)

    return clusters
