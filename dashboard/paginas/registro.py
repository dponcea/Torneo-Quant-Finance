"""Página: registro de señales emitidas (reports/senales_diarias.csv) y tableros diarios."""
# Última actualización: 2026-10-25 21:32 (hora de Chile) — versión inicial
import pandas as pd
import streamlit as st

import comun as cm
from comun import C
import run_daily

fecha, S, m = cm.contexto_pagina()
pos = S["pos"]

st.title("Registro de señales")
st.caption("Cada vez que se corre `python run_daily.py` queda una fila en `reports/senales_diarias.csv`. Esta página la "
           "contrasta con lo que el modelo reconstruye hoy: si no coinciden, la base cambió hacia atrás o cambió el código.")

arch = run_daily.ARCHIVO_REGISTRO
if not arch.exists():
    st.info("Todavía no hay señales registradas. Se crean al correr `python run_daily.py` (sin `--no-registrar`).")
    st.stop()

r = pd.read_csv(arch, dtype=str)
r["fecha"] = pd.to_datetime(r["fecha_decision"])
r["exposición registrada"] = r["exposicion"].astype(float).astype(int)
r["reconstruida hoy"] = r["fecha"].map(lambda d: pos.get(d)).astype("Int64")
r["coincide"] = (r["exposición registrada"] == r["reconstruida hoy"]).map({True: "✓", False: "≠"})
r.loc[r["reconstruida hoy"].isna(), "coincide"] = "fuera de rango"
huella_hoy = run_daily.huella_codigo()

a, b, c = st.columns(3)
a.metric("Señales registradas", len(r))
b.metric("Coinciden con la reconstrucción", f"{(r.coincide == '✓').sum()} de {(r.coincide != 'fuera de rango').sum()}")
cm.metrica(c, "Versiones de código usadas", r["huella_codigo"].nunique(), f"huella de hoy: {huella_hoy}")
if (r.coincide == "≠").any():
    st.error("Hay señales registradas que no coinciden con la reconstrucción de hoy: revisar la base y la huella del código.", icon="⚠️")

vista = r[["fecha_decision", "emitida", "p_calibrada", "exposición registrada", "reconstruida hoy", "coincide",
           "senal_ny", "mu_pb", "sigma_pb", "huella_codigo", "ultima_fecha_base", "avisos"]].iloc[::-1]
st.dataframe(vista, width="stretch", hide_index=True)

st.divider()
st.subheader("Tableros diarios guardados")
carpeta = C.RAIZ / "reports" / "tableros"
arch_t = sorted(carpeta.glob("tablero_*.html"), reverse=True) if carpeta.exists() else []
if not arch_t:
    st.caption("No hay tableros guardados. `run_daily.py` deja una copia en `reports/tableros/` cada vez que se corre.")
else:
    elegido = st.selectbox("Tablero", arch_t, format_func=lambda f: f.stem.replace("tablero_", "Decisión del "))
    st.download_button("Descargar este tablero", elegido.read_bytes(), file_name=elegido.name, mime="text/html")
    st.caption("Son la evidencia de lo que el modelo indicaba cada día; ábrelos con doble clic desde la carpeta.")
