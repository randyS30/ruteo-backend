import h3
import pandas as pd

def asignar_h3(df: pd.DataFrame, resolution: int = 9) -> pd.DataFrame:
    """
    Asigna el índice H3 a cada punto del DataFrame basado en Latitud/Longitud.
    Compatible con H3 versión 4.x
    """
    def get_h3(row):
        try:
            # EN H3 v4: geo_to_h3 se llama ahora latlng_to_cell
            return h3.latlng_to_cell(row['LATITUD'], row['LONGITUD'], resolution)
        except:
            return None

    # Creamos la columna H3
    df['h3_index'] = df.apply(get_h3, axis=1)
    
    # Filtramos nulos por si acaso
    df = df.dropna(subset=['h3_index'])
    
    return df
