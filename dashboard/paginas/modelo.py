"""Página: cómo funciona el modelo, parámetros congelados y huella del código."""
# Última actualización: 2026-10-25 21:32 (hora de Chile) — versión inicial
import re

import pandas as pd
import streamlit as st

import comun as cm
from comun import C
import run_daily

st.title("Cómo funciona")

st.markdown(f"""
**Qué predice.** Si el USD/CLP sube o baja en la jornada siguiente, en exceso de carry:
r = ln(S<sub>t+1</sub>/S<sub>t</sub>) − días/360 · (i<sub>CLP</sub> − i<sub>USD</sub>). Un largo en dólares paga el diferencial de tasas; un corto lo recibe.

**Por qué puede funcionar.** El peso chileno cierra en Santiago (~13:00–13:30) antes que Nueva York (17:00 ET). Lo que pasa
después en las monedas emergentes, el dólar global y la bolsa de EE.UU. todavía no está en el cierre local y suele trasladarse
al día siguiente (*nonsynchronous trading*).

**Cómo decide, cada día al cierre de Nueva York:**
1. **Señal NY:** promedio de los retornos del día de MXN, ZAR, BRL, DXY, −EURUSD y −S&P 500, cada uno dividido por su volatilidad de 250 días.
2. **Logit M1** con la señal NY y el retorno del propio USD/CLP. Se estima una vez al año con datos anteriores al 1 de enero
   (ventana expansiva desde 2004 y móvil de {cm.num(C.VENTANA_MOVIL, 0)} jornadas, promediadas; embargo de 5 jornadas).
3. **Calibración de Platt** con todas las predicciones fuera de muestra de años anteriores.
4. **Regla de Kelly discreta:** elige k en {{−3, −1, 0, +1, +3}} que maximiza U(k) = k·μ − k²σ²/(2c) − costo·|k − k<sub>anterior</sub>|,
   con μ = (2p − 1)·E|r|<sub>60</sub>, σ = desviación de 60 jornadas, c = {cm.num(C.KELLY_C, 2)} y costo = {cm.num(C.COSTO_POR_UNIDAD * 1e4, 0)} pb.
""", unsafe_allow_html=True)

st.subheader("Fechas")
f = pd.DataFrame({"Hito": ["Fin de la exploración", "Congelamiento y corrida única", "Inicio del monitoreo", "Fin del monitoreo"],
                  "Fecha": [cm.fecha_txt(C.FIN_EXPLORACION), cm.fecha_txt(C.FECHA_CONGELAMIENTO),
                            cm.fecha_txt(C.INICIO_MONITOREO), cm.fecha_txt(C.FIN_MONITOREO)]})
st.dataframe(f, hide_index=True, width="content")

st.subheader("Cómo usar esta app")
st.markdown("""
- **Señal del día:** qué operar mañana, dónde cae la probabilidad respecto de los umbrales y qué serie movió la señal NY.
- **Desempeño:** modelo contra las referencias del torneo en cualquier período, por perfil de costo y tipo de ejecución.
- **Riesgo:** VaR de la posición en pesos, volatilidad realizada e implícita, distribución de resultados y contexto de mercado.
- **Base de datos:** explorar cualquier serie de la base, su ficha del diccionario y la cobertura de datos.
- **Variables del modelo:** coeficientes del año, calibración y relación entre la señal NY y el dólar del día siguiente.
- **Registro de señales:** lo emitido por `run_daily.py` contrastado con la reconstrucción de hoy.

La app **no registra** señales. La señal oficial de cada día se emite con `python run_daily.py`.
""")

st.subheader("Huella del código")
st.markdown(f"Huella actual: `{run_daily.huella_codigo()}` (SHA-256 de `src/*.py` y `run_daily.py`). Si cambia durante el "
            "monitoreo, alguien modificó el código.")
filas = []
for p in sorted((C.RAIZ / "src").glob("*.py")) + [C.RAIZ / "run_daily.py"]:
    mm = re.search(r"#\s*Última actualización:\s*(.+)", p.read_text(encoding="utf-8"))
    filas.append({"Archivo": str(p.relative_to(C.RAIZ)).replace("\\", "/"), "Última actualización": mm.group(1) if mm else "sin sello"})
st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")
st.caption("No es una recomendación de inversión. Base del Laboratorio Bloomberg FEN, sujeta a los términos de uso de Bloomberg.")
