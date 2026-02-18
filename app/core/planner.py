from app.services.rutas_builder import construir_rutas


def planificar_rutas(df, frecuencia: str, sabado: bool, flex: float):
    """
    Punto único de entrada al motor de ruteo
    """
    return construir_rutas(
        df=df,
        frecuencia=frecuencia,
        sabado=sabado,
        flex=flex
    )
