import uuid

# En prod esto sería Redis o DB
PLANES = {}

def crear_plan(data: dict):
    plan_id = str(uuid.uuid4())
    PLANES[plan_id] = {
        "plan_id": plan_id,
        "estado": "GENERADO",
        "data": data
    }
    return PLANES[plan_id]

def obtener_plan(plan_id: str):
    if plan_id not in PLANES:
        raise ValueError("Plan no encontrado")
    return PLANES[plan_id]

def actualizar_plan(plan_id: str, data: dict):
    if plan_id not in PLANES:
        raise ValueError("Plan no encontrado")
    PLANES[plan_id]["data"] = data
    return PLANES[plan_id]
