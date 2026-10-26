"""Tablero interactivo de la mesa de dinero (Streamlit).

Uso, desde la carpeta del proyecto:

    streamlit run dashboard/app.py

Se abre en el navegador (http://localhost:8501). Usa el mismo modelo congelado que run_daily.py;
no modifica la base ni el registro de señales. Para registrar la señal oficial del día se sigue
usando run_daily.py.
"""
# Última actualización: 2026-10-25 21:32 (hora de Chile) — versión inicial
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

st.set_page_config(page_title="Tablero USD/CLP", page_icon="💱", layout="wide")

paginas = [
    st.Page("paginas/senal.py", title="Señal del día", icon="🎯", default=True),
    st.Page("paginas/desempeno.py", title="Desempeño", icon="📈"),
    st.Page("paginas/riesgo.py", title="Riesgo", icon="🛡️"),
    st.Page("paginas/base.py", title="Base de datos", icon="🗄️"),
    st.Page("paginas/variables.py", title="Variables del modelo", icon="🔬"),
    st.Page("paginas/registro.py", title="Registro de señales", icon="📋"),
    st.Page("paginas/modelo.py", title="Cómo funciona", icon="ℹ️"),
]
pg = st.navigation(paginas)
comun.barra_lateral()
pg.run()
