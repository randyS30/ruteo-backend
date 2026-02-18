from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router


app = FastAPI(title="Motor de Ruteo Inteligente")

# CORS (habilitado para pruebas)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # mañana puedes restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health():
    return {"status": "ok"}

app.include_router(router)
