import pandas as pd
import io
import math
from app.services.metrics import haversine 

# Constantes para el cálculo de tiempos
VELOCIDAD_PROMEDIO_KMH = 20
TIEMPO_SERVICIO_MIN = 10

def generar_excel_final(data: dict) -> io.BytesIO:
    resumen_data = []
    detalle_data = []

    # Recorremos cada mercaderista
    for merc in data["mercaderistas"]:
        nombre_merc = merc["mercaderista"]
        
        # Recorremos cada ruta del mercaderista
        for ruta in merc["rutas"]:
            # 1. DATOS PARA HOJA RESUMEN (Igual que antes)
            resumen_data.append({
                "MERCADERISTA": nombre_merc,
                "RUTA_ID": ruta["ruta_id"],
                "TOTAL_PDV": ruta["total_pdv"],
                "DISTANCIA_KM": ruta.get("distancia_total_km", 0),
                "TIEMPO_ESTIMADO_MIN": ruta.get("tiempo_estimado_min", 0),
                "ESTADO": ruta.get("estado", "OK"),
                "WARNINGS": ", ".join(ruta.get("warnings", []))
            })

            # 2. DATOS PARA HOJA BASE DE DATOS (Con cálculo de tiempo acumulado)
            
            # Ordenamos los PDVs por el campo 'orden' para simular el recorrido real
            pdvs_ordenados = sorted(ruta["pdvs"], key=lambda x: x.get("orden", 999))
            
            tiempo_acumulado = 0.0
            prev_lat = None
            prev_lon = None

            for pdv in pdvs_ordenados:
                lat_actual = pdv.get("latitud")
                lon_actual = pdv.get("longitud")
                
                # Calcular tiempo de viaje desde el punto anterior
                tiempo_viaje = 0.0
                if prev_lat is not None and prev_lon is not None:
                    dist_km = haversine(prev_lat, prev_lon, lat_actual, lon_actual)
                    # Tiempo = (Distancia / Velocidad) * 60 minutos
                    tiempo_viaje = (dist_km / VELOCIDAD_PROMEDIO_KMH) * 60
                
                # Sumamos: Tiempo acumulado previo + Viaje hasta aquí + Visita en este punto
                tiempo_acumulado += tiempo_viaje + TIEMPO_SERVICIO_MIN
                
                # Actualizamos las coordenadas previas para la siguiente vuelta
                prev_lat = lat_actual
                prev_lon = lon_actual

                # Construimos la fila
                fila = {
                    "COD_LIVE_TRA": pdv.get("cod_live_tra"),
                    "RAZON_SOCIAL": pdv.get("razon_social"),
                    "SUBCANAL": pdv.get("subcanal"),
                    "DISTRITO": pdv.get("distrito"),
                    "LATITUD": lat_actual,
                    "LONGITUD": lon_actual,
                    "MERCADERISTA_ASIGNADO": nombre_merc,
                    "NRO_RUTA": ruta["ruta_id"],
                    "ORDEN_VISITA": pdv.get("orden"),
                    # Guardamos el acumulado redondeado
                    "TIEMPO_APROX_ACUMULADO_MIN": round(tiempo_acumulado) 
                }
                detalle_data.append(fila)

    # Convertimos a DataFrames
    df_resumen = pd.DataFrame(resumen_data)
    df_detalle = pd.DataFrame(detalle_data)

    # Creamos el buffer en memoria
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_resumen.to_excel(writer, sheet_name='Resumen Rutas', index=False)
        df_detalle.to_excel(writer, sheet_name='Base de Datos', index=False)
        
        # Formato básico: Ajustar ancho de columnas
        workbook = writer.book
        worksheet_resumen = writer.sheets['Resumen Rutas']
        worksheet_detalle = writer.sheets['Base de Datos']
        
        # Formato de cabecera (negrita)
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1})
        
        for col_num, value in enumerate(df_resumen.columns.values):
            worksheet_resumen.write(0, col_num, value, header_fmt)
            worksheet_resumen.set_column(col_num, col_num, 15)

        for col_num, value in enumerate(df_detalle.columns.values):
            worksheet_detalle.write(0, col_num, value, header_fmt)
            worksheet_detalle.set_column(col_num, col_num, 18)

    output.seek(0)
    return output