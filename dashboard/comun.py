"""Funciones compartidas por las páginas del tablero interactivo (Streamlit).

Todo lo que se calcula aquí sale del mismo código que run_daily.py: la señal, las probabilidades
calibradas y las exposiciones vienen de run_daily.calcular, sin recalcular el modelo por otra vía.

Disciplina: mientras no llegue la fecha de congelamiento (C.FECHA_CONGELAMIENTO), la app solo
muestra datos hasta C.FIN_EXPLORACION (31-dic-2023), igual que run_daily.py.
"""
# Última actualización: 2026-10-25 22:04 (hora de Chile) — precio en pesos (cierre, movimiento del dólar, gráfico con compras y ventas, PnL en pesos), separado del resultado en %
import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import run_daily  # noqa: E402
from src import config as C, datos, evaluacion as ev  # noqa: E402

K_POSIBLES = [-3, -1, 0, 1, 3]
COLORES = {"modelo": "#1f5fd6", "comprar1": "#d97a0b", "comprar3": "#b8452f",
           "no_operar": "#8a929e", "tam_fijo": "#7b4fc4", "largo": "#0f8a6a", "corto": "#c2410c"}
NOMBRES = {"modelo": "Modelo (M1 + Kelly)", "comprar1": "Comprar siempre (+1)",
           "comprar3": "Comprar siempre (+3)", "no_operar": "No operar (0)",
           "tam_fijo": "Señal M1, tamaño fijo 1"}
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


# ---------------------------------------------------------------- formato
def num(v, d=1):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "—"
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def sg(v, d=1):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "—"
    return ("+" if v > 0 else "−" if v < 0 else "") + num(abs(v), d)


def kf(k):
    k = int(k)
    return f"+{k}" if k > 0 else (f"−{abs(k)}" if k < 0 else "0")


def fecha_txt(f):
    f = pd.Timestamp(f)
    return f"{f.day} {MESES[f.month - 1]} {f.year}"


def metrica(col, etiqueta, valor, nota=None, help=None):
    """st.metric sin flecha de variación; la nota va debajo como texto."""
    col.metric(etiqueta, valor, help=help)
    if nota:
        col.caption(nota)


def tabla_es(df, formatos, defecto=None):
    """Copia de `df` con números en formato chileno (coma decimal). formatos: {columna: (decimales, con_signo)}."""
    out = df.copy().astype(object)
    for c in df.columns:
        f = formatos.get(c, defecto)
        if f is None or not pd.api.types.is_numeric_dtype(df[c]):
            continue
        d, signo = f
        out[c] = [("—" if pd.isna(v) else (sg(float(v) + 0.0, d) if signo else num(float(v) + 0.0, d))) for v in df[c]]
    return out


def estilo_fig(fig, alto=380, leyenda=True):
    fig.update_layout(height=alto, margin=dict(l=10, r=10, t=30, b=10), separators=",.",
                      hovermode="x unified", legend=dict(orientation="h", y=1.08, x=0) if leyenda else None,
                      showlegend=leyenda)
    return fig


# ---------------------------------------------------------------- estado y candado
def candado_activo():
    return pd.Timestamp(dt.date.today()) < pd.Timestamp(C.FECHA_CONGELAMIENTO)


def fecha_tope():
    """Última fecha que la app puede mirar (31-dic-2023 hasta el congelamiento)."""
    return pd.Timestamp(C.FIN_EXPLORACION) if candado_activo() else pd.Timestamp("2100-01-01")


def mtime_base():
    p = Path(C.ARCHIVO_BASE)
    return p.stat().st_mtime if p.exists() else 0.0


# ---------------------------------------------------------------- carga (en caché)
@st.cache_data(show_spinner="Leyendo la base de Bloomberg…")
def base(mtime):
    """Base completa recortada a la fecha tope (el recorte se hace ANTES de usarla)."""
    x = datos.cargar_base()
    return x[x.index <= fecha_tope()]


@st.cache_data(show_spinner=False)
def diccionario(mtime):
    try:
        d = pd.read_excel(C.ARCHIVO_BASE, sheet_name="diccionario")
        d["columna"] = d["ticker"] + "|" + d["campo"]
        return d.set_index("columna")
    except Exception:
        return pd.DataFrame()


@st.cache_data(show_spinner="Calculando la señal con el modelo congelado…")
def senal(fecha_iso, mtime):
    """run_daily.calcular para una fecha: fila del registro + series para las páginas."""
    fila, ctx = run_daily.calcular(fecha_iso)
    t = ctx["tabla"]
    return {"fila": fila, "tabla": t, "p": ctx["p_cal"], "pos": ctx["pos"],
            "mu": ctx["mu"], "sigma": ctx["sigma"], "k_prev": ctx["k_prev"]}


def jornadas_validas(_x):
    return datos.calendario(_x).index


def contexto_pagina():
    """Fecha elegida en la barra lateral y la señal calculada para ella."""
    m = mtime_base()
    fecha = st.session_state.get("fecha_decision")
    return fecha, senal(fecha.date().isoformat(), m), m


# ---------------------------------------------------------------- cálculos para las páginas
def componentes_ny(x, fecha):
    """Aporte de cada serie a la señal NY de `fecha` (retorno con signo / volatilidad 250 d)."""
    s = datos.calendario(x[x.index <= fecha])
    f = s.index
    filas = []
    for ticker, signo in C.PARES_NY.items():
        px = datos._alinear(datos._px(x, ticker), f)
        r = np.log(px).diff()
        z = r * signo / (r * signo).rolling(C.VOL_VENTANA, min_periods=60).std().shift(1)
        filas.append({"serie": ticker.split()[0], "retorno %": float(r.iloc[-1] * 100),
                      "signo": "+" if signo > 0 else "−", "aporte (z)": float(z.iloc[-1])})
    return pd.DataFrame(filas)


def utilidades(mu, sigma, k_prev, c=C.KELLY_C, costo=C.COSTO_POR_UNIDAD):
    filas = []
    for k in K_POSIBLES:
        g, r, cst = k * mu, k ** 2 * sigma ** 2 / (2 * c), costo * abs(k - k_prev)
        filas.append({"k": k, "Ganancia k·μ": g * 1e4, "Riesgo −k²σ²/2c": -r * 1e4,
                      "Costo del cambio": -cst * 1e4, "U(k)": (g - r - cst) * 1e4})
    return pd.DataFrame(filas)


def umbrales_p(abs_r, sigma, k_prev, c=C.KELLY_C, costo=C.COSTO_POR_UNIDAD):
    """Probabilidad desde la que la regla elige cada exposición (dado E|r|, σ y la posición anterior).
    Se obtiene recorriendo p de 0 a 1 y anotando dónde cambia el máximo de U(k)."""
    ps = np.linspace(0.3, 0.7, 4001)
    K = np.array(K_POSIBLES, float)
    elegido = []
    for p in ps:
        mu = (2 * p - 1) * abs_r
        u = K * mu - K ** 2 * sigma ** 2 / (2 * c) - costo * np.abs(K - k_prev)
        elegido.append(K[u.argmax()])
    elegido = np.array(elegido)
    tramos, ini = [], 0
    for i in range(1, len(ps) + 1):
        if i == len(ps) or elegido[i] != elegido[ini]:
            tramos.append({"k": int(elegido[ini]), "desde": ps[ini], "hasta": ps[i - 1]})
            ini = i
    return tramos


def estrategias(pos, p, rex, costo_pos=None):
    """Posiciones del modelo y de las referencias del torneo sobre las fechas de `rex`."""
    idx = rex.index
    return {"modelo": pos.reindex(idx),
            "comprar1": pd.Series(1.0, index=idx), "comprar3": pd.Series(3.0, index=idx),
            "no_operar": pd.Series(0.0, index=idx), "tam_fijo": np.sign(p.reindex(idx) - 0.5)}


def metricas(bt, rex=None, spot=None, nocional=None):
    """Métricas en % del nocional; con `spot` y `nocional` agrega el resultado en pesos (≈ neto × nocional × spot)."""
    n = bt["neto"]
    acum = n.cumsum()
    dd = acum - acum.cummax()
    out = {"Acumulado neto %": acum.iloc[-1] * 100, "Anualizado %": n.mean() * 252 * 100,
           "Volatilidad anual %": n.std() * np.sqrt(252) * 100,
           "Sharpe": n.mean() / n.std() * np.sqrt(252) if n.std() > 0 else np.nan,
           "Pérdida máxima %": dd.min() * 100, "Costos pagados %": bt["costo"].sum() * 100,
           "% días sin posición": (bt["pos"] == 0).mean() * 100}
    if rex is not None:
        act = bt["pos"] != 0
        out["Acierto días activos %"] = (np.sign(bt.pos[act]) == np.sign(rex[act])).mean() * 100 if act.sum() else np.nan
    if spot is not None and nocional:
        out["Resultado en pesos (MM$)"] = float((n * spot.reindex(n.index)).sum() * nocional / 1e6)
    return out


def pnl_pesos(neto, spot, nocional):
    """Resultado diario en pesos: retorno neto × nocional (USD) × tipo de cambio del día de la decisión.
    Es una aproximación de primer orden (el retorno es logarítmico); el carry y los costos ya están en `neto`."""
    return neto * spot.reindex(neto.index) * nocional


def nocional():
    return st.session_state.get("nocional", 1_000_000)


def grafico_precio(t, pos, desde, hasta, alto=360, titulo=None):
    """USD/CLP de cierre en pesos, coloreado según la posición que el modelo tiene para el día siguiente,
    con las compras (▲) y ventas (▼) marcadas en el cierre del día en que se decidieron."""
    import plotly.graph_objects as go
    s = t["spot"][(t.index >= desde) & (t.index <= hasta)]
    k = pos.reindex(s.index).fillna(0)
    previo = pos[pos.index < s.index[0]]
    k_ant = k.shift(1).fillna(previo.iloc[-1] if len(previo) else 0.0)
    cambio = k - k_ant
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s.index, y=s, name="USD/CLP (cierre)", line=dict(color="#9aa3af", width=1.3),
                             customdata=np.stack([k.map(kf)], axis=-1),
                             hovertemplate="$%{y:,.2f} · exposición %{customdata[0]}<extra></extra>"))
    for nombre, cond, color in [("con compra de USD", k > 0, COLORES["largo"]), ("con venta de USD", k < 0, COLORES["corto"])]:
        # tramo del precio entre la decisión y el cierre siguiente, mientras se mantiene la posición
        y = s.where(cond | cond.shift(1, fill_value=False))
        fig.add_trace(go.Scatter(x=s.index, y=y, name=f"Precio {nombre}", line=dict(color=color, width=2.4),
                                 hoverinfo="skip", connectgaps=False))
    for nombre, cond, simbolo, color in [("Compra", cambio > 0, "triangle-up", COLORES["largo"]),
                                         ("Venta", cambio < 0, "triangle-down", COLORES["corto"])]:
        if cond.any():
            txt = [f"{nombre} {num(abs(c), 0)} unidad(es): de {kf(a)} a {kf(b)}" for a, b, c in
                   zip(k_ant[cond], k[cond], cambio[cond])]
            fig.add_trace(go.Scatter(x=s.index[cond], y=s[cond], mode="markers", name=nombre,
                                     marker=dict(symbol=simbolo, size=11, color=color, line=dict(width=1, color="white")),
                                     text=txt, hovertemplate="%{text}<br>al cierre de $%{y:,.2f}<extra></extra>"))
    fig.update_yaxes(title="pesos por dólar", tickprefix="$")
    estilo_fig(fig, alto=alto)
    fig.update_layout(hovermode="closest", title=titulo)
    return fig


def barra_lateral():
    """Selector de fecha de decisión y estado general (se muestra en todas las páginas)."""
    m = mtime_base()
    x = base(m)
    jornadas = jornadas_validas(x)
    # la última jornada con señal NY completa (las series de NY pueden llegar un día después)
    ultima = jornadas[-1]
    with st.sidebar:
        st.markdown("### Torneo USD/CLP")
        if candado_activo():
            st.warning(f"**Candado activo** hasta el {fecha_txt(C.FECHA_CONGELAMIENTO)}: "
                       f"solo datos hasta el {fecha_txt(C.FIN_EXPLORACION)}.", icon="🔒")
        hoy = pd.Timestamp(dt.date.today())
        if pd.Timestamp(C.INICIO_MONITOREO) <= hoy <= pd.Timestamp(C.FIN_MONITOREO):
            st.success("Monitoreo en vivo", icon="🟢")
        defecto = st.session_state.get("fecha_decision", ultima)
        f = st.date_input("Fecha de decisión (al cierre)", value=defecto.date(),
                          min_value=dt.date(2011, 1, 3), max_value=ultima.date(), format="DD/MM/YYYY",
                          help="La señal se calcula con información hasta el cierre de este día y "
                               "define la exposición de la jornada siguiente.")
        f = pd.Timestamp(f)
        if f not in jornadas:          # fin de semana o feriado: la jornada válida anterior
            f = jornadas[jornadas <= f][-1]
            st.caption(f"No es jornada del USD/CLP; se usa el {fecha_txt(f)}.")
        st.session_state["fecha_decision"] = f
        st.session_state["nocional"] = st.number_input(
            "Nocional por unidad (USD)", min_value=10_000, step=100_000, value=st.session_state.get("nocional", 1_000_000),
            format="%d", help="Para expresar resultados y riesgo en pesos. Una exposición de +3 equivale a 3 veces este nocional. "
                              "Las cifras del torneo siguen en % del nocional.")
        st.caption(f"Base: `{Path(C.ARCHIVO_BASE).name}` · última fecha visible {fecha_txt(x.index.max())}")
        st.caption(f"Huella del código: `{run_daily.huella_codigo()}`")
