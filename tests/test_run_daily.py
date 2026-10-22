"""Prueba: run_daily.py reproduce exactamente la probabilidad calibrada y la exposición del backtest.

Uso: python tests/test_run_daily.py   (desde la carpeta del proyecto; solo usa fechas hasta 2023)
"""
# Última actualización: 2026-10-21 16:27 (hora de Chile) — versión inicial
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_daily as rd
from src import config as C, datos, modelo, evaluacion as ev

FECHAS = ["2021-02-10", "2022-07-01", "2023-03-15", "2023-09-12", "2023-12-28"]

T = datos.recortar(datos.construir_tabla(datos.cargar_base()))
res, _ = modelo.correr_escalera(T, range(C.INICIO_OOS, C.VALIDACION[1] + 1))
v = res["2011":"2023"].dropna(subset=["y"])
t = T.reindex(v.index)
pos = ev.posicion_kelly_utilidad(v.M1_cal, t.abs_r_60, t.sd_r_60)

for f in FECHAS:
    s = rd.senal(f)
    p_bt, k_bt = round(float(v.M1_cal.loc[f]), 4), int(pos.loc[f])
    assert s["p_calibrada"] == p_bt, (f, s["p_calibrada"], p_bt)
    assert s["exposicion"] == k_bt, (f, s["exposicion"], k_bt)
    print(f"{f}: p = {p_bt:.4f}, exposición = {k_bt:+d}  OK")
print("run_daily.py coincide con el backtest.")
