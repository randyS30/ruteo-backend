from fastapi import APIRouter
from app.core.planner import planificar
from app.models.schemas import OptimizeRequest

router = APIRouter(prefix="/optimizar", tags=["Optimización"])


@router.post("")
def optimizar(req: OptimizeRequest):
    return planificar(req.model_dump())
