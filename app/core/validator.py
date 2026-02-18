from collections import Counter


def validar_frecuencia(num_puntos: int, num_rutas: int, rango: dict):
    promedio = num_puntos / num_rutas

    if not (rango["min"] <= promedio <= rango["max"]):
        raise ValueError(
            f"Promedio {promedio:.2f} fuera de rango {rango['min']} - {rango['max']}"
        )


def validar_asignacion_total(puntos_originales, rutas):
    asignados = []
    for r in rutas:
        asignados.extend(r["puntos"])

    if set(asignados) != set(puntos_originales):
        raise ValueError("No todos los puntos fueron asignados correctamente")


def validar_duplicados(rutas):
    todos = []
    for r in rutas:
        todos.extend(r["puntos"])

    repetidos = [p for p, c in Counter(todos).items() if c > 1]

    if repetidos:
        raise ValueError(f"Puntos duplicados detectados: {repetidos[:10]}")
