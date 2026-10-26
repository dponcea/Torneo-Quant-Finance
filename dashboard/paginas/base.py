"""Página: explorador de la base del Laboratorio Bloomberg (solo lectura)."""
# Última actualización: 2026-10-25 21:32 (hora de Chile) — versión inicial
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import comun as cm
from comun import C

fecha, S, m = cm.contexto_pagina()
x = cm.base(m)
dic = cm.diccionario(m)

st.title("Base de datos")
st.caption(f"Base del Laboratorio Bloomberg FEN, solo lectura. {x.shape[1]} columnas, "
           f"{cm.fecha_txt(x.index.min())} a {cm.fecha_txt(x.index.max())}"
           + (" (recortada al 31-dic-2023 por el candado)." if cm.candado_activo() else "."))

usa_modelo = {f"{t}|PX_LAST" for t in C.PARES_NY} | {"USDCLP Curncy|PX_LAST", "USDCLP Curncy|PX_OPEN", "USDCLP Curncy|PX_HIGH",
                                                     "USDCLP Curncy|PX_LOW", "CLICP Index|PX_LAST", "CHOVCHOV Index|PX_LAST",
                                                     "FEDL01 Index|PX_LAST"}


# ---------- selección
bloques = sorted(dic["bloque"].dropna().unique()) if not dic.empty else []
with st.sidebar:
    st.markdown("#### Series")
    solo_modelo = st.toggle("Solo las que usa el modelo", value=False)
    bl = st.multiselect("Bloques", bloques, default=[])
disponibles = [c for c in x.columns if (not solo_modelo or c in usa_modelo)
               and (not bl or (c in dic.index and dic.loc[c, "bloque"] in bl))]
etq = lambda c: f"{c.split('|')[0]} · {c.split('|')[1]}" + (f" — {dic.loc[c, 'nombre']}" if c in dic.index else "")
defecto = [c for c in ["USDCLP Curncy|PX_LAST", "HG1 Comdty|PX_LAST", "DXY Curncy|PX_LAST"] if c in disponibles]
sel = st.multiselect("Series", disponibles, default=defecto, format_func=etq)
c1, c2, c3 = st.columns([1.3, 1, 1])
rango = c1.date_input("Rango", value=(pd.Timestamp("2019-01-01").date(), x.index.max().date()),
                      min_value=x.index.min().date(), max_value=x.index.max().date(), format="DD/MM/YYYY")
modo = c2.radio("Mostrar", ["Nivel", "Base 100", "Retorno diario %"], index=1, horizontal=True)
jornadas = c3.toggle("Solo jornadas del USD/CLP", value=True,
                     help="Usa el calendario del modelo (sin feriados ni cotizaciones rancias). Si se apaga, se ve la base en bruto, "
                          "con su unión de calendarios (incluye fines de semana por la UF).")
if len(rango) == 2:
    d0, d1 = pd.Timestamp(rango[0]), pd.Timestamp(rango[1])
else:
    d0, d1 = pd.Timestamp(rango[0]), x.index.max()

if not sel:
    st.info("Elige una o más series.")
    st.stop()
pest = st.tabs(["Gráfico", "Tabla", "Ficha de la serie", "Cobertura de la base"])
d = x.loc[(x.index >= d0) & (x.index <= d1), sel]
if jornadas:
    d = d.reindex(cm.jornadas_validas(x)).loc[d0:d1]
if modo == "Base 100":
    v = d.apply(lambda s: s / s.dropna().iloc[0] * 100 if s.notna().any() else s)
elif modo == "Retorno diario %":
    v = np.log(d.ffill(limit=3)).diff() * 100
else:
    v = d

with pest[0]:
    eje2 = []
    if modo == "Nivel" and len(sel) > 1:
        eje2 = st.multiselect("Series en el eje derecho", sel, default=sel[1:2] if len(sel) > 1 else [], format_func=etq)
    fig = go.Figure()
    for c in sel:
        s = v[c].dropna()
        fig.add_trace(go.Scatter(x=s.index, y=s, name=etq(c)[:60], yaxis="y2" if c in eje2 else "y",
                                 mode="lines", line=dict(width=1.4)))
    fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False))
    cm.estilo_fig(fig, alto=480)
    st.plotly_chart(fig, width="stretch")
    if len(sel) > 1:
        with st.expander("Correlación de retornos diarios entre las series elegidas"):
            r = np.log(d.ffill(limit=3)).diff()
            st.dataframe(r.corr().rename(index=lambda c: c.split("|")[0], columns=lambda c: c.split("|")[0])
                         .style.format("{:.2f}").background_gradient(cmap="RdBu_r", vmin=-1, vmax=1), width="stretch")
            st.caption("Retornos del mismo día. Ojo: las series cierran a distintas horas (ver la ficha de cada una).")

with pest[1]:
    tabla = v.copy()
    tabla.columns = [c.split("|")[0] + ("" if c.endswith("PX_LAST") else " " + c.split("|")[1]) for c in tabla.columns]
    tabla.index = tabla.index.date
    st.dataframe(tabla.iloc[::-1], width="stretch", height=480)
    st.download_button("Descargar CSV", tabla.to_csv().encode("utf-8"), file_name="seleccion_base.csv", mime="text/csv",
                       help="Solo para uso personal: la base está sujeta a los términos de uso de Bloomberg.")

with pest[2]:
    if dic.empty:
        st.info("La base no trae la hoja «diccionario».")
    for c in sel:
        if c not in dic.index:
            continue
        r = dic.loc[c]
        s = x[c].dropna()
        st.markdown(f"#### {c.replace('|', ' · ')}  \n{r['nombre']}")
        a, b, cc, dd = st.columns(4)
        a.metric("Bloque", r["bloque"])
        b.metric("Observaciones visibles", f"{len(s):,}".replace(",", "."))
        cc.metric("Desde", cm.fecha_txt(s.index.min()))
        dd.metric("Último dato visible", cm.fecha_txt(s.index.max()))
        st.markdown(f"- **Moneda / unidad:** {r.get('moneda', '—')}\n- **Cierre declarado:** {r['plaza_y_hora_cierre_declarada']}\n"
                    f"- **Se revisa:** {r.get('revisable', '—')} · **Fecha de publicación:** {r.get('tiene_fecha_release', '—')}\n"
                    f"- **Uso en el modelo:** {'sí' if c in usa_modelo else 'no'}")
        if isinstance(r.get("nota"), str):
            st.warning(r["nota"], icon="🔎")
        st.divider()

with pest[3]:
    st.caption("Último dato y huecos de cada serie dentro de las jornadas del USD/CLP del último año visible.")
    jj = cm.jornadas_validas(x)
    j1 = jj[jj > jj[-1] - pd.Timedelta(days=365)]
    filas = []
    for c in x.columns:
        s = x[c].dropna()
        if s.empty:
            continue
        filas.append({"columna": c.replace("|", " · "), "bloque": dic.loc[c, "bloque"] if c in dic.index else "",
                      "usa el modelo": "sí" if c in usa_modelo else "",
                      "desde": s.index.min().date(), "último dato": s.index.max().date(),
                      "días de atraso": (x.index.max() - s.index.max()).days,
                      "% jornadas sin dato (último año)": (1 - s.reindex(j1).notna().mean()) * 100})
    cob = pd.DataFrame(filas).sort_values(["usa el modelo", "días de atraso"], ascending=[False, False])
    st.dataframe(cob.style.format({"% jornadas sin dato (último año)": "{:.1f}"})
                 .background_gradient(cmap="OrRd", subset=["días de atraso"], vmin=0, vmax=30),
                 width="stretch", height=520, hide_index=True)
