"""Métricas de pronóstico, tests (Clark-West, Diebold-Mariano) y backtest económico."""
# Última actualización: 2026-10-21 21:54 (hora de Chile) — E13: perfiles_por_ejecucion; descomposicion_tramos (costos una vez); DSR con N variable; posicion_kelly obsoleta
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from . import config as C


# ---------- pronóstico ----------
def brier(p, y):
    return float(((p - y) ** 2).mean())


def logloss(p, y):
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


def _t_nw(serie, lags=5):
    res = sm.OLS(serie.values, np.ones(len(serie))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(res.params[0]), float(res.tvalues[0])


def clark_west(y, p_chico, p_grande, lags=5):
    """Clark-West (2007) con pérdida cuadrática (Brier) para modelos anidados.
    H0: igual precisión; H1 (una cola): el modelo grande es mejor. Devuelve (t, p-valor)."""
    f = (y - p_chico) ** 2 - ((y - p_grande) ** 2 - (p_chico - p_grande) ** 2)
    _, t = _t_nw(f, lags)
    return t, float(1 - stats.norm.cdf(t))


def diebold_mariano(y, p1, p2, lags=5):
    """DM sobre diferencia de Brier (p1 − p2), con corrección HLN para h=1.
    Valor positivo = p2 es mejor. Devuelve (estadístico, p-valor una cola, t de Student)."""
    d = (y - p1) ** 2 - (y - p2) ** 2
    _, t = _t_nw(d, lags)
    n = len(d)
    t_hln = t * np.sqrt((n - 1) / n)
    return t_hln, float(1 - stats.t.cdf(t_hln, df=n - 1))


def pesaran_timmermann(y, p, umbral=0.5):
    """Test de Pesaran y Timmermann (1992) de acierto direccional.

    Compara el DA observado con el que se obtendría si pronóstico y resultado fueran
    independientes, manteniendo sus frecuencias marginales (así un modelo que dice
    siempre "sube" no obtiene significancia). H1 (una cola): el DA supera al azar.
    Devuelve (DA, DA bajo independencia, estadístico, p-valor)."""
    d = pd.DataFrame({"y": y, "x": (p > umbral).astype(float)}).dropna()
    n = len(d)
    py, px = d.y.mean(), d.x.mean()
    da = float((d.x == d.y).mean())
    da_ind = py * px + (1 - py) * (1 - px)
    var_da = da_ind * (1 - da_ind) / n
    var_ind = ((2 * py - 1) ** 2 * px * (1 - px) + (2 * px - 1) ** 2 * py * (1 - py)) / n \
              + 4 * py * px * (1 - py) * (1 - px) / n ** 2
    est = (da - da_ind) / np.sqrt(var_da - var_ind)
    return da, float(da_ind), float(est), float(1 - stats.norm.cdf(est))


def tabla_pronostico(res, cols, desde, hasta):
    d = res[desde:hasta].dropna(subset=["y"] + cols)
    return pd.DataFrame({c: {"Brier": brier(d[c], d.y), "Log-loss": logloss(d[c], d.y),
                             "Acierto": float(((d[c] > .5) == (d.y == 1)).mean()),
                             "p media": float(d[c].mean()), "p desv.": float(d[c].std())}
                         for c in cols}).T


# ---------- decisión y backtest ----------
def posicion_kelly(p, abs_r, sd_r, c=C.KELLY_C, costo=C.COSTO_POR_UNIDAD):
    """OBSOLETA: no es la regla oficial. Kelly fraccional redondeado a {0, ±1, ±3} con filtro de costo.

    Era la regla prerregistrada el 13-oct; tenía un defecto de diseño (el redondeo ignora la
    varianza; registro E04) y fue reemplazada por `posicion_kelly_utilidad`. Se conserva solo
    porque cuenta como ensayo en el Deflated Sharpe Ratio (sección 10 del notebook)."""
    mu = (2 * p - 1) * abs_r
    k = c * mu / sd_r ** 2
    lo, hi = C.CORTES
    k_obj = np.sign(k) * np.where(k.abs() >= hi, 3, np.where(k.abs() >= lo, 1, 0))
    pos, prev = [], 0.0
    for kt, mt in zip(k_obj, mu):
        if np.isnan(kt) or np.isnan(mt):
            pos.append(0.0); prev = 0.0; continue
        delta = kt - prev
        if delta != 0 and delta * mt - costo * abs(delta) <= 0:
            kt = prev                       # el cambio no paga su costo
        pos.append(float(kt)); prev = kt
    return pd.Series(pos, index=p.index)


def posicion_kelly_utilidad(p, abs_r, sd_r, c=C.KELLY_C, costo=C.COSTO_POR_UNIDAD):
    """Kelly fraccional discreto (regla vigente desde 13-oct, corrige `posicion_kelly`).

    Cada día elige k en {-3,-1,0,1,3} que maximiza la aproximación de Kelly fraccional
    al crecimiento esperado neto de costos:
        U(k) = k·mu − k²·sigma²/(2c) − costo·|k − k_anterior|
    con mu = (2p−1)·E|r|. Así el riesgo (varianza) y el costo entran en la misma
    decisión, y la abstención (k=0) aparece cuando la ventaja no paga el riesgo.

    Limitación conocida (auditoría del 21-oct, A5; se declara, no se corrige porque la regla
    está congelada): la decisión es miope. Cobra el costo completo de un cambio contra la
    ganancia esperada de un solo día, aunque la posición suele mantenerse varios días, así que
    con costos altos cambia de posición menos de lo que convendría."""
    mu = (2 * p - 1) * abs_r
    K = np.array([-3.0, -1.0, 0.0, 1.0, 3.0])
    # costo puede ser un escalar o una serie diaria (p. ej. pesos por dólar / tipo de cambio)
    kap = (pd.Series(costo, index=p.index) if np.isscalar(costo) else pd.Series(costo).reindex(p.index)).to_numpy(float)
    pos, prev = [], 0.0
    for m, s, k_ in zip(mu, sd_r, kap):
        if np.isnan(m) or np.isnan(s):
            pos.append(0.0); prev = 0.0; continue
        u = K * m - K ** 2 * s ** 2 / (2 * c) - k_ * np.abs(K - prev)
        prev = float(K[u.argmax()]); pos.append(prev)
    return pd.Series(pos, index=p.index)


def backtest(pos, rex, costo=C.COSTO_POR_UNIDAD):
    """PnL diario neto: posición × retorno en exceso − costo × |cambio de posición|.
    costo puede ser un escalar o una serie diaria alineada con rex."""
    pos = pos.reindex(rex.index).fillna(0)
    if not np.isscalar(costo):
        costo = pd.Series(costo).reindex(rex.index).ffill().bfill()
    cambio = pos.diff().abs().fillna(pos.abs())
    bruto = pos * rex
    neto = bruto - costo * cambio
    return pd.DataFrame({"pos": pos, "bruto": bruto, "costo": costo * cambio, "neto": neto})


def sensibilidad_costos(p, abs_r, sd_r, rex, costos_pb, c=C.KELLY_C, swap_anual=0.0):
    """E08 (20-oct): resultado neto según el costo por unidad de cambio (en pb).

    Dos variantes: 'fija' mantiene las posiciones decididas con el costo base (2 pb) y solo
    cobra el costo nuevo; 'reoptimiza' vuelve a decidir con la regla de utilidad usando el
    costo nuevo. swap_anual (fracción por año) cobra una tenencia extra sobre |posición|
    (sobreprecio del swap de un CFD por encima del carry justo)."""
    pos_fija = posicion_kelly_utilidad(p, abs_r, sd_r, c=c)
    filas = []
    for cbp in costos_pb:
        costo = cbp * 1e-4
        for regla, pos in [("fija", pos_fija),
                           ("reoptimiza", posicion_kelly_utilidad(p, abs_r, sd_r, c=c, costo=costo))]:
            bt = backtest(pos, rex, costo=costo)
            n = bt.neto - swap_anual / 252 * bt.pos.abs()
            filas.append({"costo_pb": cbp, "regla": regla, "Ret. anual neto %": n.mean() * 252 * 100,
                          "Sharpe": n.mean() / n.std() * np.sqrt(252) if n.std() > 0 else np.nan,
                          "Rotación anual": bt.pos.diff().abs().mean() * 252,
                          "% días en 0": float((bt.pos == 0).mean() * 100)})
    return pd.DataFrame(filas)


def costo_equilibrio(pos, rex):
    """Costo por unidad de cambio (pb) que lleva el retorno neto a cero con posiciones dadas."""
    pos = pos.reindex(rex.index).fillna(0)
    rot = pos.diff().abs().fillna(pos.abs()).sum()
    return float((pos * rex).sum() / rot * 1e4) if rot > 0 else np.nan


def perfiles_inversionista(p, abs_r, sd_r, rex, spot, c=C.KELLY_C, perfiles=None):
    """E12: resultado para cada perfil de inversionista (costo en pesos por dólar transado).

    Para cada perfil, el costo diario es pesos / tipo de cambio. 'Regla propia' = Kelly con el
    costo del perfil; 'posiciones del torneo' = posiciones decididas con 2 pb, cobrando el costo
    del perfil. También reporta la convención del torneo (2 pb)."""
    perfiles = C.PERFILES_COSTO_CLP if perfiles is None else perfiles
    pos_torneo = posicion_kelly_utilidad(p, abs_r, sd_r, c=c)
    filas = {"Torneo (2 pb)": resumen(backtest(pos_torneo, rex), rex)}
    for nombre, clp in perfiles.items():
        k = (clp / spot).reindex(rex.index)
        filas[f"{nombre.capitalize()} ({clp} CLP), regla propia"] = resumen(
            backtest(posicion_kelly_utilidad(p, abs_r, sd_r, c=c, costo=k), rex, costo=k), rex)
        filas[f"{nombre.capitalize()} ({clp} CLP), posiciones del torneo"] = resumen(
            backtest(pos_torneo, rex, costo=k), rex)
        filas[f"{nombre.capitalize()} ({clp} CLP), regla propia"]["Costo medio (pb)"] = float(k.mean() * 1e4)
    out = pd.DataFrame(filas).T
    return out


def perfiles_por_ejecucion(p, abs_r, sd_r, tabla, c=C.KELLY_C, ejecuciones=None):
    """E13 (prerregistrado el 21-oct para la corrida del 8-nov): perfiles de E12 × ejecución.

    `tabla` es la tabla de modelamiento reindexada a las fechas de `p`. Las posiciones se deciden
    igual en todas las ejecuciones (la regla no usa el retorno del día siguiente); solo cambia el
    retorno con que se liquidan: cierre a cierre (convención del torneo) o apertura a apertura
    (ejecución disponible para quien decide después del cierre de Nueva York).
    Devuelve un DataFrame con índice (ejecución, perfil)."""
    ejecuciones = C.EJECUCIONES_E13 if ejecuciones is None else ejecuciones
    partes = {}
    for nombre, col in ejecuciones.items():
        rex = tabla[col].reindex(p.index).fillna(0)
        partes[nombre] = perfiles_inversionista(p, abs_r, sd_r, rex, tabla["spot"].reindex(p.index), c=c)
    return pd.concat(partes, names=["ejecución", "perfil"])


def descomposicion_tramos(pos, tabla, costo=C.COSTO_POR_UNIDAD):
    """Descompone el resultado cierre a cierre de unas posiciones dadas (auditoría B9).

    tramo nocturno (cierre t → apertura t+1) + sesión (apertura → cierre t+1) = retorno bruto del
    tipo de cambio (identidad logarítmica); + carry recibido − costos = resultado neto, que coincide
    con el de la convención del torneo. Los costos se cobran una sola vez. Cifras anuales en %."""
    pos = pos.reindex(tabla.index).fillna(0)
    anual = lambda s: float(s.mean() * 252 * 100)
    noche = pos * tabla["rex_noche"].fillna(0)
    sesion = pos * tabla["rex_ap_ci"].fillna(0)
    carry = -pos * tabla["carry_periodo"].fillna(0)            # un largo en USD paga el carry; un corto lo recibe
    costos = costo * pos.diff().abs().fillna(pos.abs())
    neto = noche + sesion + carry - costos
    return pd.Series({"Tramo nocturno (bruto)": anual(noche), "Sesión (bruto)": anual(sesion),
                      "Retorno del tipo de cambio": anual(noche + sesion), "Carry recibido": anual(carry),
                      "Costos": -anual(costos), "Resultado neto": anual(neto),
                      "Posición media": float(pos.mean())})


def resumen(bt, rex):
    n = bt["neto"]
    acum = n.cumsum()
    dd = (acum - acum.cummax()).min()
    activos = bt.pos != 0
    max_exp = bt.pos.abs() == 3
    acierto = lambda m: float((np.sign(bt.pos[m]) == np.sign(rex[m])).mean()) if m.sum() else np.nan
    return {
        "Ret. anual neto %": n.mean() * 252 * 100,
        "Ret. anual bruto %": bt.bruto.mean() * 252 * 100,
        "Vol. anual %": n.std() * np.sqrt(252) * 100,
        "Sharpe": n.mean() / n.std() * np.sqrt(252) if n.std() > 0 else np.nan,
        "Máx. drawdown %": dd * 100,
        "% días en 0": float((bt.pos == 0).mean() * 100),
        "% días en ±1": float((bt.pos.abs() == 1).mean() * 100),
        "% días en ±3": float(max_exp.mean() * 100),
        "Acierto días activos": acierto(activos),
        "Acierto días ±3 (DA@3x)": acierto(max_exp),
        "Costos / PnL bruto %": float(bt.costo.sum() / bt.bruto.sum() * 100) if bt.bruto.sum() > 0 else np.nan,
    }


# ---------- evaluación formal contra las referencias (20-oct, E09) ----------
def indices_bootstrap_estacionario(n, B=10_000, bloque=10, semilla=0):
    """Índices del bootstrap estacionario de Politis y Romano (1994), circular.
    Cada día empieza un bloque nuevo con probabilidad 1/bloque (largo esperado = bloque)."""
    rng = np.random.default_rng(semilla)
    idx = np.empty((B, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, B)
    nuevo = rng.random((B, n)) < 1 / bloque
    saltos = rng.integers(0, n, (B, n))
    for t in range(1, n):
        idx[:, t] = np.where(nuevo[:, t], saltos[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def _sharpe(x, eje=-1):
    sd = x.std(axis=eje, ddof=1)
    return np.where(sd > 0, x.mean(axis=eje) / np.where(sd > 0, sd, 1) * np.sqrt(252), 0.0)


def comparar_con_referencia(neto_m, neto_r, idx, lags=5):
    """Compara la ganancia neta diaria del modelo con la de una referencia (mismos días).

    - DM con pérdida económica (−PnL): d_t = PnL_modelo − PnL_ref, Newey-West + HLN, una cola.
    - Bootstrap estacionario pareado (índices `idx`): p-valores de una cola, centrados bajo H0,
      para la diferencia de retorno anual (estadístico principal) y la de Sharpe.
    - Intervalo de confianza al 95 % (percentiles del bootstrap) para la diferencia de retorno."""
    m, r = np.asarray(neto_m, float), np.asarray(neto_r, float)
    d = m - r
    n = len(d)
    _, t = _t_nw(pd.Series(d), lags)
    t_hln = t * np.sqrt((n - 1) / n)
    dif_ret = d.mean() * 252
    dif_sh = float(_sharpe(m) - _sharpe(r))
    ret_b = d[idx].mean(axis=1) * 252
    sh_b = _sharpe(m[idx]) - _sharpe(r[idx])
    lo, hi = np.percentile(ret_b, [2.5, 97.5]) * 100
    return {"Dif. retorno anual %": dif_ret * 100,
            "IC 95% inf.": float(lo), "IC 95% sup.": float(hi),
            "p bootstrap (retorno)": float(np.mean(ret_b - dif_ret >= dif_ret)),
            "Dif. Sharpe": dif_sh,
            "p bootstrap (Sharpe)": float(np.mean(sh_b - dif_sh >= dif_sh)),
            "DM (HLN)": float(t_hln), "p DM": float(1 - stats.t.cdf(t_hln, df=n - 1))}


def holm(pvalores):
    """Corrección de Holm-Bonferroni (controla la tasa de error familiar)."""
    p = pd.Series(pvalores, dtype=float)
    orden = p.sort_values()
    k = len(p)
    ajust = (orden * (k - np.arange(k))).cummax().clip(upper=1)
    return ajust.reindex(p.index)


def sharpe_deflactado(neto, sharpes_ensayos, N=None):
    """Sharpe deflactado de Bailey y López de Prado (2014).

    neto: PnL diario de la estrategia elegida. sharpes_ensayos: Sharpe diario (no anualizado)
    de todas las variantes probadas. N: número de ensayos; por defecto, len(sharpes_ensayos).
    Con N mayor (auditoría A4) se usa la misma varianza de Sharpe entre ensayos, para cubrir
    elecciones que no generaron una variante con resultado observado (cribado de series,
    ventanas, embargo). Devuelve (DSR, SR0 anualizado, N)."""
    x = np.asarray(neto, float)
    T = len(x)
    sr = x.mean() / x.std(ddof=1)
    g3, g4 = stats.skew(x), stats.kurtosis(x, fisher=False)
    N = len(sharpes_ensayos) if N is None else N
    v = np.var(sharpes_ensayos, ddof=1)
    em = 0.5772156649
    sr0 = np.sqrt(v) * ((1 - em) * stats.norm.ppf(1 - 1 / N) + em * stats.norm.ppf(1 - 1 / (N * np.e)))
    z = (sr - sr0) * np.sqrt(T - 1) / np.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2)
    return float(stats.norm.cdf(z)), float(sr0 * np.sqrt(252)), N
