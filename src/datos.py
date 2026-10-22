"""Carga de la base y construcción de la tabla de modelamiento.

Regla de oro: cada variable de la fila t usa solo información disponible al
cierre de la jornada t. La variable objetivo es lo único que mira t+1.
"""
# Última actualización: 2026-10-21 21:54 (hora de Chile) — E13: rex_ap_ap paga el carry de t+1 a t+2 (antes desfasado un día) y excluye huecos de t+1 a t+2
import numpy as np
import pandas as pd

from . import config as C


def cargar_base(ruta=C.ARCHIVO_BASE):
    """Lee la hoja 'datos' del Excel del laboratorio (formato ancho)."""
    x = pd.read_excel(ruta, sheet_name="datos").set_index("fecha").sort_index()
    return x


def _px(x, ticker, campo="PX_LAST"):
    return x[f"{ticker}|{campo}"].dropna()


def _alinear(serie, fechas, limite=3):
    """Último valor disponible de `serie` en cada fecha (ffill acotado, sin mirar adelante)."""
    return serie.reindex(serie.index.union(fechas)).ffill(limit=limite).reindex(fechas)


def calendario(x):
    """Jornadas válidas del USD/CLP desde 2004, sin cotizaciones rancias de feriados."""
    c = _px(x, "USDCLP Curncy")
    h = _px(x, "USDCLP Curncy", "PX_HIGH").reindex(c.index)
    l = _px(x, "USDCLP Curncy", "PX_LOW").reindex(c.index)
    rancio = (h == l) & (c == c.shift())
    c = c[~rancio]
    return c[c.index >= C.INICIO]


def tasas(x, fechas):
    """Tasa overnight CLP (desde el índice de cámara) y USD (Fed Funds rezagado 1 día), en %."""
    icp = _px(x, "CLICP Index")
    dias = icp.index.to_series().diff().dt.days
    camara = ((icp / icp.shift()) ** (1 / dias) - 1) * 360 * 100
    # El ICP tiene dos retrocesos de la fuente (2004) y saltos de fin de año: si la cámara
    # se aleja más de 2 pp de la TPM vigente, se usa la TPM (documentado en la auditoría).
    tpm = _alinear(_px(x, "CHOVCHOV Index"), camara.index, limite=None)
    camara = camara.where((camara - tpm).abs() <= 2, tpm)
    i_clp = _alinear(camara.dropna(), fechas, limite=None)
    i_usd = _alinear(_px(x, "FEDL01 Index").shift(1), fechas, limite=None)  # se publica al día siguiente
    return i_clp, i_usd


def construir_tabla(x):
    """Devuelve la tabla de modelamiento: una fila por jornada t."""
    s = calendario(x)
    f = s.index
    t = pd.DataFrame(index=f)

    # --- objetivo (mira t+1) ---
    i_clp, i_usd = tasas(x, f)
    dias_sig = pd.Series(f, index=f).diff().dt.days.shift(-1)
    t["spot"] = s                      # tipo de cambio de cierre (para costos en pesos)
    t["dias_sig"] = dias_sig
    t["carry_periodo"] = dias_sig / 360 * (i_clp - i_usd) / 100   # lo que paga un largo USD de t a t+1
    t["r_sig"] = np.log(s.shift(-1) / s)
    t["rex_sig"] = t["r_sig"] - t["carry_periodo"]
    t["y"] = (t["rex_sig"] > 0).astype(float)
    t.loc[t["rex_sig"].isna() | (dias_sig > C.MAX_DIAS_ENTRE_JORNADAS), ["y", "rex_sig"]] = np.nan

    # --- retornos con ejecución realista (análisis de robustez, no es el objetivo) ---
    # Decisión al cierre de t, ejecución a la apertura de t+1 (primer precio transable onshore).
    o = _px(x, "USDCLP Curncy", "PX_OPEN").reindex(f)
    # Se mantiene de la apertura de t+1 a la de t+2, así que paga el carry de t+1 a t+2
    # (corrección del 21-oct, E13: antes se restaba el carry de t a t+1, desfasado un día).
    t["rex_ap_ap"] = np.log(o.shift(-2) / o.shift(-1)) - t["carry_periodo"].shift(-1)
    t["rex_ap_ci"] = np.log(s.shift(-1) / o.shift(-1))                         # solo la sesión de t+1 (intradía, sin carry)
    t["rex_noche"] = np.log(o.shift(-1) / s)                                   # tramo no transable: cierre t → apertura t+1
    t.loc[dias_sig > C.MAX_DIAS_ENTRE_JORNADAS, ["rex_ap_ap", "rex_ap_ci", "rex_noche"]] = np.nan
    t.loc[dias_sig.shift(-1) > C.MAX_DIAS_ENTRE_JORNADAS, "rex_ap_ap"] = np.nan   # el tramo t+1 → t+2 cruza un hueco

    # --- regresores (solo información hasta t) ---
    comps = []
    for ticker, signo in C.PARES_NY.items():
        r = np.log(_alinear(_px(x, ticker), f)).diff() * signo
        comps.append(r / r.rolling(C.VOL_VENTANA, min_periods=60).std().shift(1))
    t["ny"] = pd.concat(comps, axis=1).mean(axis=1)

    r_clp = np.log(s).diff()
    t["r_clp"] = r_clp / r_clp.rolling(C.VOL_VENTANA, min_periods=60).std().shift(1)
    # Cobre (E10): COMEX HG1; los días de cambio de contrato se reemplazan por LME 3M.
    r_hg = np.log(_alinear(_px(x, C.COBRE_PRINCIPAL), f)).diff()
    r_lme = np.log(_alinear(_px(x, C.COBRE_LIMPIEZA), f)).diff()
    brecha = r_hg - r_lme
    sd_brecha = brecha.rolling(C.VOL_VENTANA, min_periods=60).std().shift(1)
    roll = brecha.abs() > C.COBRE_UMBRAL_ROLL * sd_brecha
    r_cu = r_hg.where(~roll, r_lme)
    t["cobre"] = r_cu / r_cu.rolling(C.VOL_VENTANA, min_periods=60).std().shift(1)
    t["cobre_roll"] = roll.astype(float)
    t["carry"] = i_clp - i_usd
    t["riesgo"] = _alinear(_px(x, "JPMVXYEM Index"), f)
    # la interacción se construye en el modelo, tras estandarizar con la ventana de estimación

    # --- insumos de la regla de decisión (solo pasado) ---
    rex_pasado = t["rex_sig"].shift(1)          # rex realizado hasta t
    t["abs_r_60"] = rex_pasado.abs().rolling(C.VENTANA_RIESGO, min_periods=40).mean()
    t["sd_r_60"] = rex_pasado.rolling(C.VENTANA_RIESGO, min_periods=40).std()
    return t


def recortar(tabla, fin=C.FIN_EXPLORACION):
    """Deja solo filas hasta `fin` y borra el objetivo de la última, cuyo retorno
    cae después de `fin`. Mientras el modelo no esté congelado, fin = 2023-12-31."""
    t = tabla[tabla.index <= fin].copy()
    t.loc[t.index[-1], ["y", "rex_sig", "r_sig", "rex_ap_ci", "rex_noche"]] = np.nan
    t.loc[t.index[-2:], "rex_ap_ap"] = np.nan   # mira la apertura de t+2
    return t


def chequear_sin_lookahead(x, tabla, fecha_corte="2015-06-30"):
    """Prueba: recalcular la tabla con datos truncados en `fecha_corte` no cambia
    ningún regresor de fechas <= corte. Si cambia, hay información futura filtrada."""
    x_trunc = x[x.index <= fecha_corte]
    t2 = construir_tabla(x_trunc)
    cols = ["ny", "r_clp", "cobre", "carry", "riesgo", "abs_r_60", "sd_r_60"]
    a = tabla.loc[tabla.index <= fecha_corte, cols].iloc[:-1]
    b = t2.loc[a.index, cols]
    dif = (a - b).abs().max().max()
    return dif
