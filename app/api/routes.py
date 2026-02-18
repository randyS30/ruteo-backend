from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import traceback
from app.services.reasignador import reasignar_pdv
from app.services.excel_reader import leer_maestro_pdv
from app.models.schemas import ReasignarRequest
from fastapi.responses import Response
from app.services.exporter import generar_excel_final
from app.models.schemas import OptimizeRequest
from typing import List, Union 
from pydantic import BaseModel
from app.services.route_optimizer import optimizar_orden_pdvs
from app.services.metrics import evaluar_ruta
from app.services.territory_planner import planificar_bolsa_grandes
from app.services.rutas_builder import construir_rutas as planificar_rutas_asignadas

router = APIRouter()

@router.post("/planificar")
async def planificar(
    file: UploadFile = File(...),
    # Parámetros Comunes
    flex: float = Form(0.2),
    modo: str = Form("ASIGNADO"), # "ASIGNADO" o "BOLSA"
    
    # Parámetros ASIGNADO (Poco HC)
    frecuencia: str = Form("SEMANAL"),
    sabado: bool = Form(False),
    
    # Parámetros BOLSA (Mucho HC)
    capacidad: int = Form(50) 
):
    try:
        # 1. Leer y normalizar Excel (funciona para ambos formatos)
        df = leer_maestro_pdv(file)

        # 2. Decidir qué motor usar
        if modo == "BOLSA":
            # Flujo Cuentas Grandes (Territorios)
            # PASAMOS EL PARAMETRO SABADO A LA FUNCIÓN DE BOLSA
            return planificar_bolsa_grandes(
                df=df,
                capacidad_objetivo=capacidad,
                flex=flex,
                sabado_activo=sabado  # <--- CAMBIO AQUÍ
            )
        else:
            # Flujo Cuentas Chicas (Asignado por Vendedor)
            return planificar_rutas_asignadas(
                df=df,
                frecuencia=frecuencia,
                sabado=sabado,
                flex=flex
            )

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/rutas/reasignar-pdv")
def mover_pdv(payload: ReasignarRequest):
    try:
        # 1. Convertir lo que llega de Swagger a un diccionario Python
        datos = payload.model_dump() 
        return reasignar_pdv(datos)  
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/exportar")
def exportar_excel(payload: dict):
    # Recibimos el JSON completo (dataPlanificada del frontend)
    try:
        excel_file = generar_excel_final(payload)
        
        return Response(
            content=excel_file.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=planificacion_final.xlsx"}
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    

# Definimos el esquema para la petición masiva
class ReasignarMasivoRequest(BaseModel):
    mercaderista: str
    # CORRECCIÓN: Aceptamos String O Enteros (Union)
    codigos_pdv: List[Union[str, int]]       
    to_ruta: int               
    rutas: List[dict]            
    rango: dict

@router.post("/rutas/reasignar-masivo")
def reasignar_pdv_masivo(payload: ReasignarMasivoRequest):
    try:
        ruta_destino = None

        # --- LÓGICA DE NUEVA RUTA ---
        if payload.to_ruta == -1:
            # 1. Calcular el nuevo ID (El máximo actual + 1)
            if payload.rutas:
                max_id = max(r["ruta_id"] for r in payload.rutas)
                new_id = max_id + 1
            else:
                new_id = 1
            
            # 2. Crear la estructura de la nueva ruta vacía
            ruta_destino = {
                "ruta_id": new_id,
                "pdvs": [],
                "total_pdv": 0,
                "distancia_total_km": 0,
                "tiempo_estimado_min": 0,
                "estado": "NUEVA",
                "warnings": []
            }
            # La agregamos a la lista maestra de rutas
            payload.rutas.append(ruta_destino)
            
        else:
            # --- LÓGICA EXISTENTE (Buscar ruta) ---
            ruta_destino = next((r for r in payload.rutas if r["ruta_id"] == payload.to_ruta), None)
            if not ruta_destino:
                raise HTTPException(status_code=404, detail="Ruta destino no encontrada")

        pdvs_a_mover = []

        # 3. Buscar y remover los PDVs de sus rutas originales
        for ruta in payload.rutas:
            # Si es la misma ruta destino (recién creada), saltar
            if ruta["ruta_id"] == ruta_destino["ruta_id"]:
                continue

            nuevos_pdvs = []
            for pdv in ruta["pdvs"]:
                # Comparamos IDs (str/int safe)
                if pdv["cod_live_tra"] in payload.codigos_pdv:
                    pdvs_a_mover.append(pdv)
                else:
                    nuevos_pdvs.append(pdv)
            
            # Actualizamos la ruta origen
            ruta["pdvs"] = nuevos_pdvs
            ruta["total_pdv"] = len(ruta["pdvs"])

        # Fallback de búsqueda (por si los tipos de dato difieren)
        if not pdvs_a_mover:
            codigos_str = [str(c) for c in payload.codigos_pdv]
            for ruta in payload.rutas:
                if ruta["ruta_id"] == ruta_destino["ruta_id"]: continue
                for pdv in list(ruta["pdvs"]): # Usamos list() para iterar copia segura
                     if str(pdv["cod_live_tra"]) in codigos_str:
                         pdvs_a_mover.append(pdv)
                         ruta["pdvs"].remove(pdv)
                         ruta["total_pdv"] = len(ruta["pdvs"])
            
            if not pdvs_a_mover:
                raise HTTPException(status_code=400, detail="No se encontraron los PDVs enviados")

        # 4. Agregarlos a la ruta destino
        ruta_destino["pdvs"].extend(pdvs_a_mover)
        
        # 5. Re-optimizar orden y métricas
        if ruta_destino["pdvs"]:
            ruta_destino["pdvs"] = optimizar_orden_pdvs(ruta_destino["pdvs"])
            metricas = evaluar_ruta(ruta_destino, payload.rango)
            ruta_destino.update(metricas)
        
        ruta_destino["total_pdv"] = len(ruta_destino["pdvs"])

        return {
            "mercaderista": payload.mercaderista,
            "rutas": payload.rutas 
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))