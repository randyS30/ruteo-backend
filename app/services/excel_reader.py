import pandas as pd
from fastapi import UploadFile, HTTPException
import io

def leer_maestro_pdv(file: UploadFile) -> pd.DataFrame:
    try:
        # Leer el archivo en memoria
        content = file.file.read()
        df = pd.read_excel(io.BytesIO(content))

        # 1. Normalizar nombres de columnas (Mayúsculas y sin espacios)
        df.columns = [str(c).strip().upper() for c in df.columns]

        # 2. Mapeo de columnas (Diccionario de Sinónimos)
        rename_map = {
            # Campos Principales
            "ID": "COD_LIVE_TRA",
            "CODIGO": "COD_LIVE_TRA",
            "NOMBRE": "RAZON_SOCIAL",
            "CLIENTE": "RAZON_SOCIAL",
            
            # Ubicación
            "DEPARTAMENTO": "DEPARTAMENTO",
            "LAT": "LATITUD", "LATITUD": "LATITUD",
            "LON": "LONGITUD", "LNG": "LONGITUD", "LONGITUD": "LONGITUD",
            
            # --- NUEVO: CAMPO GOLPEO ---
            "GOLPEO": "GOLPEO",
            "FRECUENCIA": "GOLPEO", # Por si en el Excel le ponen Frecuencia
            "VISITAS": "GOLPEO",
            
            # Campos opcionales
            "VENDEDOR": "NOMBRE_VENDEDOR"
        }
        
        df = df.rename(columns=rename_map)

        # 3. VALIDACIÓN MÍNIMA
        required = ["LATITUD", "LONGITUD", "COD_LIVE_TRA"]
        missing = [c for c in required if c not in df.columns]
        
        if missing:
            raise HTTPException(status_code=400, detail=f"Faltan columnas obligatorias: {missing}")

        # 4. LIMPIEZA DE COORDENADAS
        df = df.dropna(subset=["LATITUD", "LONGITUD"])
        try:
            df["LATITUD"] = df["LATITUD"].astype(float)
            df["LONGITUD"] = df["LONGITUD"].astype(float)
        except ValueError:
            raise HTTPException(status_code=400, detail="Las coordenadas deben ser numéricas.")

        # 5. LÓGICA DE GOLPEO (MULTIFRECUENCIA)
        if "GOLPEO" in df.columns:
            # Convertir a numérico, los errores (texto) se vuelven NaN, luego NaN se vuelve 1
            df["GOLPEO"] = pd.to_numeric(df["GOLPEO"], errors='coerce').fillna(1).astype(int)
            # Asegurar que mínimo sea 1 (no pueden ser 0 o negativos)
            df["GOLPEO"] = df["GOLPEO"].apply(lambda x: x if x > 0 else 1)
        else:
            # Si no existe la columna, asumimos 1 visita para todos
            df["GOLPEO"] = 1

        # 6. RELLENO DE CAMPOS FALTANTES
        if "DISTRITO" not in df.columns: df["DISTRITO"] = "SIN_DISTRITO"
        if "SUBCANAL" not in df.columns: df["SUBCANAL"] = "GENERAL"

        # 7. AGRUPACIÓN (VENDEDOR vs DEPARTAMENTO)
        if "NOMBRE_VENDEDOR" not in df.columns:
            if "DEPARTAMENTO" in df.columns:
                df["NOMBRE_VENDEDOR"] = df["DEPARTAMENTO"]
            else:
                df["NOMBRE_VENDEDOR"] = "TERRITORIO_GENERAL"

        # Compatibilidad con formato antiguo
        if "FRECUENCIA" not in df.columns:
            df["FRECUENCIA"] = "SEMANAL"

        return df

    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=400, detail=f"Error leyendo Excel: {str(e)}")