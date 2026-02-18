import math
from typing import List


# =========================
# DISTANCIA (HAVERSINE)
# =========================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# =========================
# CENTROIDE
# =========================
def centroide(pdvs: List[dict]):
    lat = sum(p["latitud"] for p in pdvs) / len(pdvs)
    lon = sum(p["longitud"] for p in pdvs) / len(pdvs)
    return lat, lon


# =========================
# DISTANCIA TOTAL ORDENADA
# =========================
def distancia_total(pdvs: List[dict]):
    total = 0.0
    for i in range(len(pdvs) - 1):
        total += haversine(
            pdvs[i]["latitud"], pdvs[i]["longitud"],
            pdvs[i + 1]["latitud"], pdvs[i + 1]["longitud"]
        )
    return round(total, 2)


# =========================
# TIEMPO ESTIMADO
# =========================
def tiempo_estimado(distancia_km: float, total_pdv: int):
    """
    Supuestos realistas mercaderista:
    - 20 km/h promedio
    - 10 min por PDV
    """
    VELOCIDAD_KMH = 20
    TIEMPO_PDV_MIN = 10

    tiempo_ruta = (distancia_km / VELOCIDAD_KMH) * 60
    tiempo_visitas = total_pdv * TIEMPO_PDV_MIN

    return round(tiempo_ruta + tiempo_visitas)


# =========================
# MÉTRICA FINAL DE RUTA
# =========================
def evaluar_ruta(ruta: dict, rango: dict):
    """
    Retorna métricas + warnings sin romper flujo
    """
    pdvs = ruta["pdvs"]
    total = len(pdvs)

    # Centroide + radio
    lat_c, lon_c = centroide(pdvs)
    distancias = [
        haversine(lat_c, lon_c, p["latitud"], p["longitud"])
        for p in pdvs
    ]
    radio = max(distancias) if distancias else 0

    # Distancia y tiempo
    dist_total = distancia_total(pdvs)
    tiempo = tiempo_estimado(dist_total, total)

    # Estado simple (legacy + útil)
    estado = "OK"
    if total < rango["min"]:
        estado = "SUBUTILIZADA"
    elif total > rango["max"]:
        estado = "SOBRECARGADA"

    # Warnings operativos
    warnings = []

    if total < rango["min"]:
        warnings.append("PDVs por debajo del mínimo")

    if total > rango["max"]:
        warnings.append("PDVs por encima del máximo")

    if radio > 5:
        warnings.append("Ruta muy dispersa")

    if dist_total > 25:
        warnings.append("Ruta demasiado larga")

    if tiempo > 480:
        warnings.append("Tiempo estimado excede jornada")

    return {
        "total_pdv": total,
        "radio_km": round(radio, 2),
        "distancia_total_km": dist_total,
        "tiempo_estimado_min": tiempo,
        "estado": estado,
        "warnings": warnings
    }
