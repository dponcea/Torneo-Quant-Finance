"""Estimación del logit núcleo: walk-forward anual con dos ventanas y Platt anual."""
# Última actualización: 2026-10-21 21:54 (hora de Chile) — comentario sobre el embargo (auditoría A8); sin cambios de lógica
import numpy as np
import pandas as pd
import statsmodels.api as sm

from . import config as C

EPS = 1e-6


def _diseno(df, cols, media, desv):
    """Estandariza con estadísticos de la ventana de estimación y agrega la interacción."""
    z = (df[[c for c in cols if c != "carry_x_riesgo"]] - media) / desv
    if "carry_x_riesgo" in cols:
        z["carry_x_riesgo"] = z["carry"] * z["riesgo"]
    return sm.add_constant(z[cols], has_constant="add")


def ajustar(train, cols, cov=None):
    """Ajusta el logit en `train`. Devuelve (resultado, media, desv)."""
    base = [c for c in cols if c != "carry_x_riesgo"]
    media, desv = train[base].mean(), train[base].std()
    X = _diseno(train, cols, media, desv)
    kw = {"cov_type": "HAC", "cov_kwds": {"maxlags": 5}} if cov == "HAC" else {}
    res = sm.Logit(train["y"], X).fit(disp=0, **kw)
    return res, media, desv


def _filas_validas(tabla, cols):
    req = ["y"] + [c for c in cols if c != "carry_x_riesgo"]
    return tabla.dropna(subset=req)


def walk_forward(tabla, cols, ventana, anios, embargo=5):
    """Predicciones fuera de muestra año a año.

    ventana: 'expansiva' (desde 2004) o 'movil' (últimas C.VENTANA_MOVIL jornadas).
    Para predecir el año a se estima con filas anteriores al 1-ene de a, menos un
    embargo de `embargo` jornadas (la etiqueta de la última fila mira el día siguiente).
    Nota (auditoría A8): bastaría 1 jornada, porque la etiqueta de la última fila de
    entrenamiento solo usa el cierre del primer día del año, que ya se conoce cuando se
    decide ese día. Las 5 jornadas son conservadoras y quedan como se prerregistraron.
    """
    datos = _filas_validas(tabla, cols)
    salida = []
    for a in anios:
        train = datos[datos.index < f"{a}-01-01"].iloc[:-embargo]
        if ventana == "movil":
            train = train.iloc[-C.VENTANA_MOVIL:]
        test = datos[(datos.index >= f"{a}-01-01") & (datos.index <= f"{a}-12-31")]
        if not cols:  # M0: frecuencia histórica de alzas
            p = pd.Series(train["y"].mean(), index=test.index)
        else:
            res, media, desv = ajustar(train, cols)
            p = pd.Series(res.predict(_diseno(test, cols, media, desv)), index=test.index)
        salida.append(p)
    return pd.concat(salida).clip(EPS, 1 - EPS)


def platt_anual(p, y, anios):
    """Calibra p del año a con una sigmoide ajustada en las predicciones fuera de
    muestra de años anteriores (desde C.INICIO_OOS). El primer año queda sin calibrar."""
    logit = np.log(p / (1 - p))
    out, params = [], {}
    for a in anios:
        m_hist = (p.index < f"{a}-01-01") & y.notna()
        m_a = (p.index >= f"{a}-01-01") & (p.index <= f"{a}-12-31")
        if m_hist.sum() < 200 or logit[m_hist].std() < 1e-6:   # M0 no tiene nada que calibrar
            out.append(p[m_a])
            continue
        X = sm.add_constant(logit[m_hist], has_constant="add")
        res = sm.Logit(y[m_hist], X).fit(disp=0)
        params[a] = res.params.values
        out.append(pd.Series(res.predict(sm.add_constant(logit[m_a], has_constant="add")), index=p.index[m_a]))
    return pd.concat(out).clip(EPS, 1 - EPS), params


def correr_escalera(tabla, anios):
    """Corre M0, M1, M2 con ambas ventanas, el promedio y su calibración.

    Devuelve un DataFrame con y, rex y una columna por (modelo, versión)."""
    res = pd.DataFrame(index=tabla.index)
    res["y"], res["rex"] = tabla["y"], tabla["rex_sig"]
    platt = {}
    for nombre, cols in C.MODELOS.items():
        pe = walk_forward(tabla, cols, "expansiva", anios)
        pm = walk_forward(tabla, cols, "movil", anios)
        res[f"{nombre}_exp"], res[f"{nombre}_mov"] = pe, pm
        prom = (pe + pm.reindex(pe.index)) / 2
        res[f"{nombre}_prom"] = prom
        if not cols:                       # M0 es una constante: no hay nada que calibrar
            res[f"{nombre}_cal"], platt[nombre] = prom, {}
            continue
        cal, platt[nombre] = platt_anual(prom.dropna(), res["y"].reindex(prom.dropna().index), anios)
        res[f"{nombre}_cal"] = cal
    return res.dropna(subset=["M0_exp"]), platt
