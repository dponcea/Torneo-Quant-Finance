"""Página: variables del modelo, coeficientes del año, calibración y relación señal → retorno."""
# Última actualización: 2026-10-25 21:32 (hora de Chile) — versión inicial
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

import comun as cm
from comun import C
from src import modelo

fecha, S, m = cm.contexto_pagina()
t, p, pos = S["tabla"], S["p"], S["pos"]
cols = C.MODELOS["M1"]

st.title("Variables del modelo")
st.caption("M1: logit de la probabilidad de que el dólar suba en exceso de carry, con la señal NY y el retorno del propio "
           "USD/CLP. Todo lo que se muestra usa predicciones fuera de muestra (cada año se estima con datos anteriores).")

# ---------- coeficientes del año
st.subheader(f"Coeficientes vigentes en {fecha.year}")


@st.cache_data(show_spinner=False)
def coeficientes(anio, mtime):
    validas = modelo._filas_validas(t, cols)
    out = {}
    for ventana in ["expansiva", "movil"]:
        train = validas[validas.index < f"{anio}-01-01"].iloc[:-5]
        if ventana == "movil":
            train = train.iloc[-C.VENTANA_MOVIL:]
        res, _, _ = modelo.ajustar(train, cols, cov="HAC")
        out[ventana] = pd.DataFrame({"coef.": res.params, "error est. (HAC)": res.bse, "z": res.tvalues, "p-valor": res.pvalues})
        out[ventana].attrs["n"] = len(train)
        out[ventana].attrs["periodo"] = f"{cm.fecha_txt(train.index[0])} – {cm.fecha_txt(train.index[-1])}"
    return out


coef = coeficientes(fecha.year, m)
a, b = st.columns(2)
for col, (v, df) in zip([a, b], coef.items()):
    col.markdown(f"**Ventana {'móvil' if v == 'movil' else v}** · {df.attrs['n']:,} jornadas · {df.attrs['periodo']}".replace(",", "."))
    col.dataframe(df.rename(index={"const": "constante", "ny": "señal NY (estand.)", "r_clp": "r_CLP (estand.)"})
                  .pipe(cm.tabla_es, {"coef.": (4, True), "error est. (HAC)": (4, False), "z": (2, True), "p-valor": (4, False)}),
                  width="stretch")
st.caption("Variables estandarizadas con la media y desviación de la ventana: el coeficiente es el cambio en el logit por una "
           "desviación estándar. Signo esperado: señal NY positiva; r_CLP no positivo. La probabilidad final es el promedio "
           "de ambas ventanas, calibrado con Platt.")

st.divider()

# ---------- calibración y ventaja
desde = st.select_slider("Período de evaluación", options=list(range(2011, fecha.year + 1)), value=min(2020, fecha.year),
                         help="Desde ese año hasta la fecha de decisión. Solo predicciones fuera de muestra.")
idx = p.index[(p.index >= f"{desde}-01-01") & (p.index < fecha)]
d = pd.DataFrame({"p": p.reindex(idx), "y": t["y"].reindex(idx), "rex": t["rex_sig"].reindex(idx),
                  "ny": t["ny"].reindex(idx)}).dropna()
a, b = st.columns(2)
with a:
    st.subheader("¿La probabilidad está calibrada?")
    nb = st.slider("Grupos", 5, 15, 10, key="nb")
    d["g"] = pd.qcut(d.p, nb, labels=False, duplicates="drop")
    g = d.groupby("g").agg(p=("p", "mean"), frec=("y", "mean"), n=("y", "size"))
    g["ee"] = np.sqrt(g.frec * (1 - g.frec) / g.n)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[40, 60], y=[40, 60], mode="lines", line=dict(dash="dash", color="#9ca3af"), name="calibración perfecta"))
    fig.add_trace(go.Scatter(x=g.p * 100, y=g.frec * 100, mode="markers+lines", name="observado",
                             error_y=dict(type="data", array=1.96 * g.ee * 100, visible=True),
                             marker=dict(size=9, color=cm.COLORES["modelo"]),
                             hovertemplate="p media %{x:.1f} %<br>frecuencia %{y:.1f} %<extra></extra>"))
    lo, hi = min(g.p.min(), g.frec.min()) * 100 - 3, max(g.p.max(), g.frec.max()) * 100 + 3
    fig.update_xaxes(title="probabilidad predicha %", range=[lo, hi]); fig.update_yaxes(title="frecuencia observada de alzas %", range=[lo, hi])
    cm.estilo_fig(fig, alto=380); fig.update_layout(hovermode="closest")
    st.plotly_chart(fig, width="stretch")
    st.caption(f"{len(d):,} jornadas. Barras: intervalo al 95 %. Si los puntos siguen la diagonal, «55 %» significa "
               "que sube 55 de cada 100 veces.".replace(",", "."))
with b:
    st.subheader("Señal NY de hoy → dólar mañana")
    d["q"] = pd.qcut(d.ny, 5, labels=["Q1 (dólar débil afuera)", "Q2", "Q3", "Q4", "Q5 (dólar fuerte afuera)"])
    q = d.groupby("q", observed=True).agg(rex=("rex", "mean"), sube=("y", "mean"), n=("y", "size"))
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=q.index.astype(str), y=q.rex * 1e4, name="retorno medio al día siguiente (pb)",
                         marker_color=np.where(q.rex > 0, cm.COLORES["largo"], cm.COLORES["corto"])), secondary_y=False)
    fig.add_trace(go.Scatter(x=q.index.astype(str), y=q.sube * 100, name="% de días que sube", mode="markers+lines",
                             marker=dict(size=9, color=cm.COLORES["modelo"])), secondary_y=True)
    fig.update_yaxes(title_text="pb", secondary_y=False); fig.update_yaxes(title_text="% sube", secondary_y=True, showgrid=False)
    cm.estilo_fig(fig, alto=380); fig.update_layout(hovermode="closest")
    st.plotly_chart(fig, width="stretch")
    st.caption("Quintiles de la señal NY del día de la decisión y lo que hizo el USD/CLP (en exceso de carry) la jornada "
               "siguiente. Es la ventaja que explota el modelo: el peso chileno cierra antes que Nueva York.")

st.divider()

# ---------- series
st.subheader("Evolución de las variables")
r0 = st.date_input("Desde", value=(fecha - pd.DateOffset(months=6)).date(), min_value=pd.Timestamp("2011-01-03").date(),
                   max_value=fecha.date(), format="DD/MM/YYYY", key="var_desde")
tt = t[(t.index >= pd.Timestamp(r0)) & (t.index <= fecha)]
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04,
                    subplot_titles=("Señal NY", "r_CLP normalizado", "Probabilidad calibrada % y exposición"))
fig.add_trace(go.Bar(x=tt.index, y=tt.ny, marker_color=np.where(tt.ny > 0, cm.COLORES["largo"], cm.COLORES["corto"]), name="señal NY"), 1, 1)
fig.add_trace(go.Bar(x=tt.index, y=tt.r_clp, marker_color="#6b7280", name="r_CLP"), 2, 1)
pp = p.reindex(tt.index) * 100
fig.add_trace(go.Scatter(x=pp.index, y=pp, line=dict(color=cm.COLORES["modelo"]), name="p %"), 3, 1)
fig.add_hline(y=50, line_dash="dot", row=3, col=1)
kk = pos.reindex(tt.index)
fig.add_trace(go.Scatter(x=kk.index[kk != 0], y=pp[kk != 0], mode="markers", name="con posición",
                         marker=dict(color=np.where(kk[kk != 0] > 0, cm.COLORES["largo"], cm.COLORES["corto"]),
                                     size=np.where(kk[kk != 0].abs() == 3, 10, 6))), 3, 1)
cm.estilo_fig(fig, alto=620, leyenda=False); fig.update_layout(bargap=0)
st.plotly_chart(fig, width="stretch")

with st.expander("Tabla de modelamiento (una fila por jornada)"):
    vista = tt[["spot", "ny", "r_clp", "carry", "abs_r_60", "sd_r_60", "rex_sig", "y"]].copy()
    vista["p_cal"] = p.reindex(vista.index)
    vista["exposición"] = pos.reindex(vista.index)
    vista.index = vista.index.date
    st.dataframe(vista.iloc[::-1], width="stretch", height=400)
    st.caption("rex_sig e y miran la jornada siguiente (son el resultado, no un insumo). La última fila no tiene resultado.")
