def balancear_rutas(rutas, min_p, max_p):
    balanceadas = []

    for ruta in rutas:
        if min_p <= len(ruta) <= max_p:
            balanceadas.append(ruta)
        elif len(ruta) > max_p:
            for i in range(0, len(ruta), max_p):
                balanceadas.append(ruta[i:i + max_p])
        else:
            balanceadas.append(ruta)

    return balanceadas
