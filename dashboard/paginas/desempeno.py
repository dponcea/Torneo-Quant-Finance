"""Página: resultado del modelo frente a las referencias, por período, perfil de costo y ejecución."""
# Última actualización: 2026-10-25 22:04 (hora de Chile) — precio en pesos (cierre, movimiento del dólar, gráfico con compras y ventas, PnL en pesos), separado del resultado en %
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

import comun as cm
from comun import C, ev

fecha, S, m = cm.contexto_pagina()
t, p, pos_torneo = S["tabla"], S["p"], S["pos"]

st.title("Desempeño frente a las referencias")
st.caption("Resultado neto de carry y costos, en % del nocional por unidad de exposición. Solo jornadas con "
           "resultado conocido hasta la fecha de decisión.")

# ---------- controles
c1, c2, c3 = st.columns([1.4, 1.2, 1.2])
hoy = fecha
opciones = {
    "Seguimiento (monitoreo)": (pd.Timestamp(C.INICIO_MONITOREO), hoy),
    f"Año {hoy.year}": (pd.Timestamp(f"{hoy.year}-01-01"), hoy),
    "Últimos 3 meses": (hoy - pd.DateOffset(months=3), hoy),
    "Validación 2020–2023": (pd.Timestamp("2020-01-01"), pd.Timestamp("2023-12-31")),
    "Entrenamiento OOS 2011–2019": (pd.Timestamp("2011-01-01"), pd.Timestamp("2019-12-31")),
    "Desde 2011": (pd.Timestamp("2011-01-01"), hoy),
    "Personalizado": None,
}
if hoy < pd.Timestamp(C.INICIO_MONITOREO):
    opciones.pop("Seguimiento (monitoreo)")
eleccion = c1.selectbox("Período", list(opciones), index=list(opciones).index(f"Año {hoy.year}"))
if eleccion == "Personalizado":
    r = c1.date_input("Desde – hasta", value=(pd.Timestamp(f"{hoy.year}-01-01").date(), hoy.date()),
                      min_value=pd.Timestamp("2011-01-03").date(), max_value=hoy.date(), format="DD/MM/YYYY")
    desde, hasta = (pd.Timestamp(r[0]), pd.Timestamp(r[1])) if len(r) == 2 else (pd.Timestamp(r[0]), hoy)
else:
    desde, hasta = opciones[eleccion]
hasta = min(hasta, hoy)

perfiles = {"Torneo (2 pb)": None, **{f"{n.capitalize()} ({v} CLP por dólar)": v for n, v in C.PERFILES_COSTO_CLP.items()}}
perfil = c2.selectbox("Perfil de costo", list(perfiles),
                      help="E12 (prerregistrado): institucional 0,5 CLP y minorista 2 CLP por dólar transado. "
                           "Cada perfil decide con su propio costo.")
ejec = c3.selectbox("Ejecución", list(C.EJECUCIONES_E13),
                    help="E13 (prerregistrado): cierre a cierre es la convención del torneo; apertura a apertura es "
                         "lo que puede ejecutar quien decide después del cierre de Nueva York.")

# ---------- posiciones y retornos
col = C.EJECUCIONES_E13[ejec]
rex_all = t[col]
clp = perfiles[perfil]
if clp is None:
    costo = C.COSTO_POR_UNIDAD
    pos = pos_torneo
else:
    costo = (clp / t["spot"]).reindex(p.index)
    tt = t.reindex(p.index)
    pos = ev.posicion_kelly_utilidad(p, tt.abs_r_60, tt.sd_r_60, c=C.KELLY_C, costo=costo)

idx = pos.index[(pos.index >= desde) & (pos.index <= hasta) & (pos.index < fecha)]
rex = rex_all.reindex(idx).dropna()
if len(rex) < 2:
    st.info("No hay suficientes jornadas con resultado en el período elegido.")
    st.stop()
est = cm.estrategias(pos, p, rex)
bts = {k: ev.backtest(s, rex, costo=costo) for k, s in est.items()}

ocultar = st.multiselect("Referencias en el gráfico", [k for k in cm.NOMBRES if k != "modelo"],
                         default=["comprar1", "no_operar", "tam_fijo"], format_func=cm.NOMBRES.get)

# ---------- KPIs
N = cm.nocional()
mt = {k: cm.metricas(b, rex if k == "modelo" else None, spot=t["spot"], nocional=N) for k, b in bts.items()}
mm = mt["modelo"]
mejor = max([k for k in mt if k != "modelo"], key=lambda k: mt[k]["Acumulado neto %"])
k1, k6, k2, k3, k4, k5 = st.columns(6)
cm.metrica(k1, "Modelo, acumulado", f"{cm.sg(mm['Acumulado neto %'], 2)} %",
           f"{len(rex)} jornadas · {cm.fecha_txt(rex.index[0])} – {cm.fecha_txt(rex.index[-1])}")
vp = mm["Resultado en pesos (MM$)"]
cm.metrica(k6, "Resultado en pesos", f"{cm.sg(vp, 0 if abs(vp) >= 10 else 1)} MM$",
           f"con USD {cm.num(N / 1e6, 1)} MM por unidad",
           help="≈ retorno neto diario × nocional × tipo de cambio del día de la decisión. El resultado oficial del torneo se mide en %.")
cm.metrica(k2, "vs mejor referencia", f"{cm.sg(mm['Acumulado neto %'] - mt[mejor]['Acumulado neto %'], 2)} pp",
           f"{cm.NOMBRES[mejor]}: {cm.sg(mt[mejor]['Acumulado neto %'], 2)} %")
cm.metrica(k3, "Sharpe anualizado", cm.num(mm["Sharpe"], 2), f"volatilidad {cm.num(mm['Volatilidad anual %'], 1)} %")
cm.metrica(k4, "Pérdida máxima", f"{cm.sg(mm['Pérdida máxima %'], 2)} %", f"costos pagados {cm.num(mm['Costos pagados %'], 2)} %")
cm.metrica(k5, "Acierto días activos", f"{cm.num(mm['Acierto días activos %'], 1)} %",
           f"{cm.num(100 - mm['% días sin posición'], 0)} % de días con posición")

# ---------- curva + exposición + drawdown
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.62, 0.16, 0.22], vertical_spacing=0.03)
for k in ["no_operar", "comprar1", "comprar3", "tam_fijo", "modelo"]:
    if k != "modelo" and k not in ocultar:
        continue
    y = bts[k]["neto"].cumsum() * 100
    fig.add_trace(go.Scatter(x=y.index, y=y, name=cm.NOMBRES[k], line=dict(color=cm.COLORES[k], width=2.6 if k == "modelo" else 1.4),
                             hovertemplate="%{y:.2f} %"), row=1, col=1)
pm = bts["modelo"]["pos"]
fig.add_trace(go.Bar(x=pm.index, y=pm, name="Exposición", marker_color=np.where(pm > 0, cm.COLORES["largo"], cm.COLORES["corto"]),
                     showlegend=False, hovertemplate="exposición %{y:+d}"), row=2, col=1)
acum = bts["modelo"]["neto"].cumsum() * 100
fig.add_trace(go.Scatter(x=acum.index, y=acum - acum.cummax(), name="Caída desde el máximo", fill="tozeroy",
                         line=dict(color=cm.COLORES["corto"], width=1), showlegend=False,
                         hovertemplate="%{y:.2f} %"), row=3, col=1)
fig.update_yaxes(title_text="acumulado %", row=1, col=1)
fig.update_yaxes(title_text="k", tickvals=[-3, 0, 3], row=2, col=1)
fig.update_yaxes(title_text="caída %", row=3, col=1)
fig.update_layout(bargap=0)
cm.estilo_fig(fig, alto=620)
g1, g2 = st.tabs(["Resultado acumulado (%)", "El dólar en pesos y las operaciones"])
with g1:
    st.plotly_chart(fig, width="stretch")
with g2:
    st.plotly_chart(cm.grafico_precio(t, pos, rex.index[0], fecha, alto=560), width="stretch")
    st.caption("Precio de cierre del USD/CLP. Verde (rojo): el día siguiente a una decisión de compra (venta). ▲ y ▼ marcan "
               "los cambios de posición del modelo con el perfil y período elegidos. Es el mercado en pesos; el resultado "
               "del modelo se mide en % (pestaña anterior).")

# ---------- tabla de métricas
st.subheader("Métricas del período")
tm = pd.DataFrame(mt).T.rename(index=cm.NOMBRES)
st.dataframe(cm.tabla_es(tm, {"Acumulado neto %": (2, True), "Anualizado %": (1, True), "Pérdida máxima %": (2, True),
                              "Sharpe": (2, False), "Resultado en pesos (MM$)": (1, True)}, defecto=(1, False)), width="stretch")
st.caption(f"«Resultado en pesos» usa USD {cm.num(N / 1e6, 1)} MM por unidad de exposición (barra lateral) y el tipo de cambio "
           "de cada día; el resto de las cifras está en % del nocional, que es la unidad del torneo.")

# ---------- por año y por mes
a, b = st.columns([1, 1.3])
with a:
    st.subheader("Por año (%)")
    anual = pd.DataFrame({cm.NOMBRES[k]: bts[k]["neto"].groupby(bts[k].index.year).sum() * 100 for k in bts})
    anual.index.name = "año"
    st.dataframe(cm.tabla_es(anual, {}, defecto=(2, True)), width="stretch")
with b:
    st.subheader("Modelo por mes (%)")
    n = bts["modelo"]["neto"]
    mes = n.groupby([n.index.year, n.index.month]).sum().unstack() * 100
    mes.columns = [cm.MESES[c - 1] for c in mes.columns]
    fig = go.Figure(go.Heatmap(z=mes.values, x=mes.columns, y=[str(i) for i in mes.index], colorscale="RdYlGn", zmid=0,
                               text=np.vectorize(lambda v: "" if np.isnan(v) else f"{v:+.1f}")(mes.values),
                               texttemplate="%{text}", hovertemplate="%{y} %{x}: %{z:.2f} %<extra></extra>", showscale=False))
    fig.update_yaxes(autorange="reversed", type="category")
    cm.estilo_fig(fig, alto=max(220, 28 * len(mes) + 60), leyenda=False)
    fig.update_layout(hovermode="closest")
    st.plotly_chart(fig, width="stretch")

st.caption("Cada estrategia parte sin posición al inicio del período y paga el costo de entrar. «Exposición fija 1» "
           "es ambigua en las bases: se muestran las dos lecturas (+1 siempre y señal M1 con tamaño 1). Los perfiles y "
           "la ejecución a la apertura son reportes prerregistrados (E12, E13): no se elige nada a partir de ellos. "
           "Con pocas jornadas, el Sharpe y el acierto son muy ruidosos.")
