from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Union, Optional


class Ruta(BaseModel):
    ruta: str
    puntos: List[int]
    conteo: int


class Vendedor(BaseModel):
    vendedor: str
    frecuencia: str
    rutas: List[Ruta]


class OptimizeRequest(BaseModel):
    data: List[Vendedor]

class PDV(BaseModel):
    cod_live_tra: Union[int, str]
    razon_social: Optional[str] = None
    latitud: float
    longitud: float
    distrito: Optional[str] = None
    h3: Optional[str] = None
    orden: Optional[int] = None
    
    # Esto permite que pasen campos extra sin dar error (como 'subcanal')
    model_config = ConfigDict(extra='allow') 

# 2. Definimos cómo se ve una Ruta
class RutaInput(BaseModel):
    ruta_id: int
    total_pdv: int
    pdvs: List[PDV]
    # Métricas opcionales para que no falle si no las envías al editar
    radio_km: Optional[float] = None
    distancia_total_km: Optional[float] = None
    tiempo_estimado_min: Optional[float] = None
    estado: Optional[str] = None
    warnings: Optional[List[str]] = None

# 3. El Payload Principal para la Reasignación
class ReasignarRequest(BaseModel):
    mercaderista: str
    cod_live_tra: Union[int, str] = Field(..., description="ID del punto a mover")
    from_ruta: int
    to_ruta: int
    rango: Dict[str, float] # Espera {min, max, promedio}
    rutas: List[RutaInput]