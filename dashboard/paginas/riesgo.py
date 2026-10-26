"""Página: riesgo de la posición de hoy, historia del riesgo y contexto de mercado."""
# Última actualización: 2026-10-25 22:23 (hora de Chile) — con exposición 0 ya no muestra ceros: tabla de riesgo para cada exposición posible (±1, ±3)
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import comun as cm
from comun import C

fecha, S, m = cm.contexto_pagina()
F, t, pos = S["fila"], S["tabla"], S["pos"]
k, sigma = F["exposicion"], S["sigma"]
spot = float(t.loc[fecha, "spot"])

st.title("Riesgo")
st.caption(f"Posición para la jornada siguiente: **{cm.kf(k)}** ({F['direccion']}) · decisión al cierre del {cm.fecha_txt(fecha)}")

# ---------- riesgo de hoy
nocional = cm.nocional()
st.caption(f"Montos en pesos para USD {cm.num(nocional / 1e6, 1)} MM por unidad de exposición (se cambia en la barra lateral).")
rex_hist = t["rex_sig"].dropna()
rex_hist = rex_hist[rex_hist.index < fecha]
u250 = rex_hist.iloc[-250:]


def medidas(kk):
    """Riesgo de un día para una exposición kk (fracción del nocional por unidad)."""
    pnl = kk * u250
    var_h = float(-np.percentile(pnl, 5)) if kk else 0.0
    return {"σ diaria": abs(kk) * sigma, "VaR 95 % normal": 1.645 * abs(kk) * sigma, "VaR 95 % histórico": var_h,
            "Pérdida media más allá del VaR": float(-pnl[pnl <= -var_h].mean()) if kk else 0.0,
            "Peor día (250 j.)": float(-pnl.min()) if kk else 0.0}


hoy_m = medidas(k)
if k != 0:
    c = st.columns(5)
    for col, (nombre, v) in zip(c, hoy_m.items()):
        cm.metrica(col, f"{nombre} de la posición" if nombre == "σ diaria" else nombre, f"{cm.num(v * 1e4, 1)} pb",
                   f"${cm.num(v * spot * nocional / 1e6, 1)} MM con {cm.kf(k)} × USD {cm.num(nocional / 1e6, 1)} MM",
                   help="Expected shortfall histórico: promedio de las pérdidas del 5 % de peores días (250 jornadas)."
                   if nombre.startswith("Pérdida") else None)
else:
    st.info("**Hoy el modelo no tiene posición, así que el riesgo de mercado de mañana es cero.** La tabla de abajo muestra "
            "cuánto riesgo tendría cada exposición posible, para saber qué implicaría que la señal cambie.", icon="ℹ️")

st.markdown("**Riesgo de un día según la exposición**")
filas = {}
for kk in [k] + [v for v in [1, -1, 3, -3] if v != k] if k != 0 else [1, -1, 3, -3]:
    etiqueta = f"{cm.kf(kk)}{'  ← posición de mañana' if kk == k else ''}"
    filas[etiqueta] = {n: f"{cm.num(v * 1e4, 0)} pb · ${cm.num(v * spot * nocional / 1e6, 1)} MM" for n, v in medidas(kk).items()}
st.dataframe(pd.DataFrame(filas).T, width="stretch")
carry_dia = -k * t.loc[fecha, "carry"] / 100 / 360
st.caption(f"Pesos para USD {cm.num(nocional / 1e6, 1)} MM por unidad (barra lateral), al spot de ${cm.num(spot, 2)}. "
           "VaR 95 %: en 1 de cada 20 días la pérdida debería superar esa cifra. Histórico = últimas 250 jornadas del USD/CLP "
           "en exceso de carry; por eso comprar y vender tienen riesgos algo distintos. "
           f"Diferencial de tasas CLP − USD: {cm.sg(t.loc[fecha, 'carry'], 2)} % anual (un largo en USD lo paga, un corto lo recibe); "
           f"con la posición de mañana {'se paga' if carry_dia < 0 else 'se recibe' if carry_dia > 0 else 'no se paga ni se recibe'}"
           f"{'' if carry_dia == 0 else ' ' + cm.num(abs(carry_dia) * 1e4, 2) + ' pb por día corrido'}.")

st.divider()

# ---------- historia del riesgo
a, b = st.columns([1.4, 1])
with a:
    st.subheader("Volatilidad del USD/CLP y exposición")
    desde = st.select_slider("Desde", options=list(range(2011, fecha.year + 1)), value=max(2011, fecha.year - 2))
    tt = t[(t.index >= f"{desde}-01-01") & (t.index <= fecha)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=tt.index, y=tt["sd_r_60"] * 1e4 * np.sqrt(252) / 100, name="Volatilidad realizada 60 j. (% anual)",
                             line=dict(color=cm.COLORES["modelo"])))
    vi = cm.base(m)["USDCLPV1M Curncy|PX_LAST"].dropna()
    vi = vi[(vi.index >= f"{desde}-01-01") & (vi.index <= fecha)]
    fig.add_trace(go.Scatter(x=vi.index, y=vi, name="Volatilidad implícita 1M (% anual)", line=dict(color=cm.COLORES["comprar1"], width=1.2)))
    pp = pos.reindex(tt.index)
    fig.add_trace(go.Bar(x=pp.index, y=pp.abs(), name="|exposición|", yaxis="y2", marker_color="rgba(120,120,120,.35)"))
    fig.update_layout(yaxis=dict(title="% anual"), yaxis2=dict(overlaying="y", side="right", range=[0, 12], showgrid=False,
                                                               tickvals=[0, 1, 3], title="|k|"), bargap=0)
    cm.estilo_fig(fig, alto=360)
    st.plotly_chart(fig, width="stretch")
    st.caption("Con más volatilidad, la regla de Kelly exige más ventaja para tomar posición y reduce el tamaño.")
with b:
    st.subheader("Distribución del PnL diario del modelo")
    pnl = (pos.reindex(rex_hist.index) * rex_hist - C.COSTO_POR_UNIDAD * pos.reindex(rex_hist.index).diff().abs().fillna(0))
    pnl = pnl[(pnl.index >= f"{desde}-01-01")]
    activos = pnl[pos.reindex(pnl.index) != 0] * 1e4
    fig = go.Figure(go.Histogram(x=activos, nbinsx=60, marker_color=cm.COLORES["modelo"], opacity=.8,
                                 hovertemplate="%{x} pb: %{y} días<extra></extra>"))
    q5 = np.percentile(activos, 5) if len(activos) else 0
    fig.add_vline(x=q5, line_dash="dash", line_color=cm.COLORES["corto"], annotation_text=f"percentil 5: {cm.num(q5, 0)} pb")
    fig.update_xaxes(title="PnL del día (pb), solo días con posición")
    cm.estilo_fig(fig, alto=360, leyenda=False)
    fig.update_layout(hovermode="closest")
    st.plotly_chart(fig, width="stretch")
    st.caption(f"{len(activos)} días con posición desde {desde}. Ganancia media {cm.sg(activos.mean(), 1)} pb; "
               f"días positivos {cm.num((activos > 0).mean() * 100, 1)} %.")

st.divider()

# ---------- contexto
st.subheader("Contexto de mercado")
st.caption("Estas series no entran al modelo: dan contexto sobre el régimen de riesgo. Percentil frente a los últimos 5 años.")
x = cm.base(m)
series = {"USDCLPV1M Curncy|PX_LAST": "Vol. implícita USD/CLP 1M", "JPMVXYEM Index|PX_LAST": "EM-VXY",
          "VIX Index|PX_LAST": "VIX", "HG1 Comdty|PX_LAST": "Cobre COMEX", "DXY Curncy|PX_LAST": "DXY",
          "USDCLP Curncy|PX_LAST": "USD/CLP"}
cols = st.columns(len(series))
for (col, nombre), cc in zip(series.items(), cols):
    s = x[col].dropna()
    s = s[s.index <= fecha]
    u5 = s[s.index > fecha - pd.Timedelta(days=5 * 365)]
    pct = (u5 <= s.iloc[-1]).mean() * 100
    var = (s.iloc[-1] / s.iloc[-21] - 1) * 100
    cc.metric(nombre, cm.num(s.iloc[-1], 2), f"{var:+.1f} % en 20 j.".replace(".", ","), delta_color="off")
    cc.caption(f"percentil 5 años: {cm.num(pct, 0)}")
    f2 = go.Figure(go.Scatter(x=u5.index[-250:], y=u5.iloc[-250:], line=dict(width=1.2, color="#6b7280"), hovertemplate="%{y:.2f}"))
    cm.estilo_fig(f2, alto=90, leyenda=False)
    f2.update_layout(margin=dict(l=0, r=0, t=0, b=0)); f2.update_xaxes(visible=False); f2.update_yaxes(visible=False)
    cc.plotly_chart(f2, width="stretch", config={"displayModeBar": False})
