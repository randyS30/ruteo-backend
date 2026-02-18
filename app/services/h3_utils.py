import h3


def asignar_h3(df, resolution=9):
    df = df.copy()
    df["h3_index"] = df.apply(
        lambda r: h3.latlng_to_cell(
            r["LATITUD"],
            r["LONGITUD"],
            resolution
        ),
        axis=1
    )
    return df
