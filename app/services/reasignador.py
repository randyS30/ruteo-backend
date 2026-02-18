from copy import deepcopy
from app.services.metrics import evaluar_ruta
from app.services.route_optimizer import optimizar_orden_pdvs

def reasignar_pdv(payload: dict):
    
    # 1. Extraemos datos directos del payload
    mercaderista = payload["mercaderista"]
    cod_live_tra = payload["cod_live_tra"] # Puede ser int o str
    from_ruta = payload["from_ruta"]
    to_ruta = payload["to_ruta"]
    rango = payload["rango"]

    rutas = deepcopy(payload["rutas"]) 

    ruta_origen = next(r for r in rutas if r["ruta_id"] == from_ruta)
    ruta_destino = next(r for r in rutas if r["ruta_id"] == to_ruta)

    pdv = next(
        p for p in ruta_origen["pdvs"]
        if str(p["cod_live_tra"]) == str(cod_live_tra)
    )

    ruta_origen["pdvs"].remove(pdv)
    ruta_destino["pdvs"].append(pdv)

    ruta_origen["pdvs"] = optimizar_orden_pdvs(ruta_origen["pdvs"])
    ruta_destino["pdvs"] = optimizar_orden_pdvs(ruta_destino["pdvs"])

    for ruta in (ruta_origen, ruta_destino):
        metricas = evaluar_ruta(ruta, rango)
        ruta.update(metricas)
        ruta["total_pdv"] = len(ruta["pdvs"])
        ruta["editado_manualmente"] = True

    return {
        "mercaderista": mercaderista,
        "rutas": rutas, # Lista completa con las 2 rutas modificadas y las demás intactas
        "mensaje": "Reasignación exitosa"
    }