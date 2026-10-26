"""Página: señal del día, por qué la regla eligió esa exposición y qué movió la señal NY."""
# Última actualización: 2026-10-25 22:04 (hora de Chile) — precio en pesos (cierre, movimiento del dólar, gráfico con compras y ventas, PnL en pesos), separado del resultado en %
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import comun as cm
from comun import C

fecha, S, m = cm.contexto_pagina()
F, t = S["fila"], S["tabla"]
k, kp, ch = F["exposicion"], F["exposicion_anterior"], F["cambio"]

st.title("Señal del día")
st.caption(f"Decisión al cierre del **{cm.fecha_txt(fecha)}** para la jornada siguiente · "
           f"M1 + Platt + Kelly discreto (c = {cm.num(C.KELLY_C, 2)}) · costo {cm.num(C.COSTO_POR_UNIDAD * 1e4, 0)} pb por unidad")

if F["avisos"]:
    st.error(f"Series sin cierre en la fecha de decisión: {F['avisos']}. La señal NY usa el último dato "
             "disponible (hasta 3 jornadas). Revisar antes de operar.", icon="⚠️")

# ---------- tarjeta principal
c1, c2, c3, c4 = st.columns([1.3, 1, 1, 1])
color = "#0f8a6a" if k > 0 else "#c2410c" if k < 0 else "#6b7280"
c1.markdown(f"<div style='font-size:13px;opacity:.7'>Exposición para mañana</div>"
            f"<div style='font-size:64px;font-weight:700;line-height:1;color:{color}'>{cm.kf(k)}</div>"
            f"<div style='font-size:18px;font-weight:600;color:{color}'>{F['direccion']}</div>",
            unsafe_allow_html=True)
accion = ("Sin operación: se mantiene la posición." if ch == 0 else
          f"**{'Comprar' if ch > 0 else 'Vender'} {abs(ch)} unidad{'es' if abs(ch) > 1 else ''} de USD** "
          f"(de {cm.kf(kp)} a {cm.kf(k)}); costo ≈ {cm.num(abs(ch) * C.COSTO_POR_UNIDAD * 1e4, 0)} pb.")
c1.markdown(accion)
spot = t["spot"]
sp_hoy, sp_ant = float(spot.loc[fecha]), float(spot[spot.index < fecha].iloc[-1])
N = cm.nocional()
c1.markdown(f"Cierre de hoy: **${cm.num(sp_hoy, 2)}** ({cm.sg(sp_hoy - sp_ant, 2)} pesos en el día)  \n"
            f"Posición para mañana: {cm.kf(k)} × USD {cm.num(N / 1e6, 1)} MM"
            + (f" = **USD {cm.num(abs(k) * N / 1e6, 1)} MM {'comprados' if k > 0 else 'vendidos'}**" if k else ""))
c2.metric("Probabilidad de que suba", f"{cm.num(F['p_calibrada'] * 100, 1)} %",
          help="Probabilidad calibrada (Platt) de que el dólar suba en exceso de carry en la jornada siguiente.")
c2.metric("Probabilidad bruta (logit)", f"{cm.num(F['p_bruta'] * 100, 1)} %")
c3.metric("Retorno esperado μ", f"{cm.sg(F['mu_pb'], 1)} pb", help="μ = (2p − 1) · E|r| de las últimas 60 jornadas.")
c3.metric("Riesgo diario σ (60 j.)", f"{cm.num(F['sigma_pb'], 1)} pb")
c4.metric("Señal NY", cm.sg(F["senal_ny"], 2), help="Promedio de los 6 componentes de abajo.")
c4.metric("Posición anterior", cm.kf(kp))

st.divider()

# ---------- zona de decisión
izq, der = st.columns([1.15, 1])
with izq:
    st.subheader("Dónde cae la probabilidad")
    tramos = cm.umbrales_p(t.loc[fecha, "abs_r_60"], S["sigma"], S["k_prev"])
    fig = go.Figure()
    col_k = {-3: "#c2410c", -1: "#f0a070", 0: "#d1d5db", 1: "#7cc7ad", 3: "#0f8a6a"}
    pc = F["p_calibrada"] * 100
    lo = min(40, pc - 2); hi = max(60, pc + 2)
    for tr in tramos:
        fig.add_shape(type="rect", x0=tr["desde"] * 100, x1=tr["hasta"] * 100, y0=0, y1=1,
                      fillcolor=col_k[tr["k"]], line_width=0, opacity=.85)
        a_, b_ = max(tr["desde"] * 100, lo), min(tr["hasta"] * 100, hi)
        if b_ - a_ > 0.6:
            fig.add_annotation(x=(a_ + b_) / 2, y=0.5, text=f"<b>{cm.kf(tr['k'])}</b>",
                               showarrow=False, font=dict(size=15, color="#111"))
    fig.add_shape(type="line", x0=pc, x1=pc, y0=-0.25, y1=1.25, line=dict(color="#111", width=3))
    fig.add_annotation(x=pc, y=1.42, text=f"hoy {cm.num(pc, 1)} %", showarrow=False, font=dict(size=13))
    fig.update_xaxes(range=[lo, hi], ticksuffix=" %", showgrid=False)
    fig.update_yaxes(visible=False, range=[-0.4, 1.6])
    cm.estilo_fig(fig, alto=170, leyenda=False)
    fig.update_layout(hovermode=False)
    st.plotly_chart(fig, width="stretch")
    filas = [f"{cm.kf(tr['k'])}: p entre {cm.num(tr['desde'] * 100, 1)} % y {cm.num(tr['hasta'] * 100, 1)} %"
             for tr in tramos if 0.4 <= (tr["desde"] + tr["hasta"]) / 2 <= 0.6 or tr["k"] == k]
    st.caption("Con el riesgo y el costo de hoy, y partiendo de la posición anterior, la regla elige: "
               + " · ".join(filas) + ". La franja gris es la zona en que no conviene tener posición.")

with der:
    st.subheader("Por qué esta exposición")
    u = cm.utilidades(S["mu"], S["sigma"], S["k_prev"])
    fig = go.Figure(go.Bar(x=u["U(k)"], y=[cm.kf(v) for v in u.k], orientation="h",
                           marker_color=["#1f5fd6" if v == k else "#c7cdd6" for v in u.k],
                           text=[cm.sg(v, 2) for v in u["U(k)"]], textposition="auto",
                           hovertemplate="k = %{y}<br>U(k) = %{x:.2f} pb<extra></extra>"))
    fig.update_yaxes(type="category", categoryorder="array", categoryarray=[cm.kf(v) for v in [-3, -1, 0, 1, 3]], title="k")
    fig.update_xaxes(title="U(k), pb por día", zeroline=True)
    cm.estilo_fig(fig, alto=230, leyenda=False)
    fig.update_layout(hovermode="closest")
    st.plotly_chart(fig, width="stretch")
    with st.expander("Ver el detalle de U(k)"):
        st.dataframe(cm.tabla_es(u.assign(k=u.k.map(cm.kf)).set_index("k"), {}, defecto=(2, True)), width="stretch")
        st.caption("U(k) = k·μ − k²·σ²/(2c) − costo·|k − k_anterior|. La regla elige la exposición con mayor U(k).")

st.divider()

# ---------- precio en pesos
st.subheader("El dólar en pesos y las operaciones del modelo")
meses = st.radio("Ventana", [1, 3, 6, 12], index=1, horizontal=True, format_func=lambda v: f"{v} mes{'es' if v > 1 else ''}")
fig = cm.grafico_precio(t, S["pos"], fecha - pd.DateOffset(months=meses), fecha, alto=380)
st.plotly_chart(fig, width="stretch")
st.caption("Precio de cierre del USD/CLP. El tramo verde (rojo) es el movimiento del día siguiente a una decisión de compra "
           "(venta): ahí el modelo está expuesto. ▲ y ▼ marcan los cambios de posición, al cierre del día en que se "
           "decidieron. Este gráfico muestra el mercado en pesos; el resultado del modelo se mide en % (página Desempeño).")

st.divider()

# ---------- señal NY
st.subheader("Qué movió la señal de Nueva York hoy")
x = cm.base(m)
comp = cm.componentes_ny(x, fecha)
a, b = st.columns([1.3, 1])
with a:
    fig = go.Figure(go.Bar(x=comp["aporte (z)"], y=comp["serie"], orientation="h",
                           marker_color=["#0f8a6a" if v > 0 else "#c2410c" for v in comp["aporte (z)"]],
                           text=[cm.sg(v, 2) for v in comp["aporte (z)"]], textposition="outside",
                           hovertemplate="%{y}: %{x:.2f} desv.<extra></extra>"))
    fig.add_vline(x=F["senal_ny"], line_dash="dash", line_color="#1f5fd6",
                  annotation_text=f"promedio {cm.sg(F['senal_ny'], 2)}", annotation_position="top")
    fig.update_xaxes(title="desviaciones estándar (positivo = dólar más fuerte)")
    cm.estilo_fig(fig, alto=280, leyenda=False)
    fig.update_layout(hovermode="closest")
    st.plotly_chart(fig, width="stretch")
with b:
    st.dataframe(cm.tabla_es(comp.set_index("serie"), {"retorno %": (2, True), "aporte (z)": (2, True)}), width="stretch")
    st.caption("Cada componente es el retorno del día con el signo que fortalece al dólar (EURUSD y S&P 500 "
               "entran con signo negativo), dividido por su volatilidad de 250 días. La señal es el promedio. "
               f"El otro regresor es el retorno del propio USD/CLP normalizado: {cm.sg(t.loc[fecha, 'r_clp'], 2)}.")

# ---------- últimos días
st.divider()
st.subheader("Últimas 10 jornadas")
pos, p = S["pos"], S["p"]
u10 = pos[pos.index <= fecha].iloc[-10:]
sig = t["spot"].shift(-1).reindex(u10.index)
neto = u10 * t["rex_sig"].reindex(u10.index) - C.COSTO_POR_UNIDAD * u10.diff().abs().fillna(abs(u10.iloc[0] - pos.shift(1).get(u10.index[0], 0)))
tab = pd.DataFrame({
    "Cierre ($)": t["spot"].reindex(u10.index),
    "Señal NY": t["ny"].reindex(u10.index),
    "p calibrada %": p.reindex(u10.index) * 100,
    "Exposición": u10.map(cm.kf),
    "Dólar al día siguiente ($)": sig - t["spot"].reindex(u10.index),
    "Retorno en exceso de carry (pb)": t["rex_sig"].reindex(u10.index) * 1e4,
    "PnL neto (pb)": neto * 1e4,
    f"PnL neto ($, USD {cm.num(N / 1e6, 1)} MM por unidad)": cm.pnl_pesos(neto, t["spot"], N),
})
tab.index = [cm.fecha_txt(d) for d in tab.index]
cols_pnl = list(tab.columns[-1:])
vt = cm.tabla_es(tab.iloc[::-1], {"Cierre ($)": (2, False), "Señal NY": (2, True), "p calibrada %": (1, False),
                                   "Dólar al día siguiente ($)": (2, True), "Retorno en exceso de carry (pb)": (1, True),
                                   "PnL neto (pb)": (1, True), cols_pnl[0]: (0, True)})
vt.iloc[0, 4:] = "abierta" if np.isnan(t["rex_sig"].get(fecha, np.nan)) else vt.iloc[0, 4:]
st.dataframe(vt, width="stretch")
st.caption("Mercado en pesos: cierre y cuánto se movió el dólar al día siguiente. Resultado del modelo: en pb del nocional "
           "(exposición × retorno en exceso de carry − costo) y en pesos para el nocional elegido (≈ pb × nocional × "
           "tipo de cambio). El movimiento en pesos y el PnL no coinciden exactamente: el PnL descuenta el carry, usa retorno "
           "logarítmico y depende de la exposición. Con exposición 0 el PnL es 0 aunque el dólar se mueva.")
