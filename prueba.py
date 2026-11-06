"""Corrida ÚNICA del modelo congelado en el tramo de prueba (2024-01-01 en adelante).

Uso (desde la carpeta del proyecto):

    python prueba.py --ensayo   # mismo análisis sobre la validación 2020-2023 (no mira la prueba):
                                # sirve para comprobar que el script reproduce las cifras conocidas
    python prueba.py            # LA corrida única del tramo de prueba (solo después del congelamiento)

Repite, sin cambiar nada, el análisis prerregistrado de las secciones 3 a 12b del notebook:
pronóstico (Brier, Clark-West, Pesaran-Timmermann), valor económico frente a las referencias,
evaluación formal E09 (bootstrap estacionario, Holm, Sharpe deflactado con N = 48, 100 y 200),
resultado por año, ejecución y tramos (E07), costos y costo de equilibrio (E08), perfiles de E12
y perfiles × ejecución de E13, más la lectura de la convicción que piden las bases (jornadas en ±3 y en 0) y la robustez a la
muestra de entrenamiento de E15 (sin el tramo con huecos 2011-2012 y con otros puntos de partida).
Agrega la sensibilidad a 8 pb por unidad, que equivale al spread de
estrés de ~1,5 CLP que mencionó el mentor el 6-nov (cifra informativa; no cambia ninguna decisión).

Disciplina: la corrida de prueba se niega a correr antes de C.FECHA_CONGELAMIENTO y no sobrescribe
reports/prueba/ si ya existe (se corre una sola vez). Cada salida lleva la huella del código y de
la base con que se generó. Nada de lo que muestre esta corrida cambia el modelo.
"""
# Última actualización: 2026-11-06 17:59 (hora de Chile) — lectura de la convicción (sección 8, exigida por las bases) y robustez a la muestra de entrenamiento (sección 9, E15)
import argparse
import datetime as dt
import io
import sys
from contextlib import redirect_stdout

import numpy as np
import pandas as pd

from src import config as C, datos, modelo, evaluacion as ev, figuras
import run_daily

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
SH = lambda n: n.mean() / n.std() * np.sqrt(252) if n.std() > 0 else np.nan


# E15 (prerregistrado el 6-nov-2026 17:58): variantes de la muestra de entrenamiento. Solo robustez.
VARIANTES_E15 = {
    "Oficial (expansiva desde 2004, todo)": {},
    "Sin el tramo dañado (2011-11 a 2012-10 fuera)": {"excluir": ("2011-11-01", "2012-10-31")},
    "Expansiva desde 2008": {"inicio": "2008-01-01"},
    "Expansiva desde 2013 (después de los huecos)": {"inicio": "2013-01-01"},
}


def m1_variante(T, hasta, excluir=None, inicio=None):
    """Probabilidad calibrada de M1 con el mismo procedimiento oficial, pero entrenando sin las jornadas
    excluidas (su etiqueta se borra: no entran a la estimación ni a la calibración de Platt)."""
    T2 = T.copy()
    if excluir:
        T2.loc[excluir[0]:excluir[1], "y"] = np.nan
    if inicio:
        T2.loc[:pd.Timestamp(inicio) - pd.Timedelta(days=1), "y"] = np.nan
    primero = (pd.Timestamp(inicio).year + 3) if inicio else C.INICIO_OOS   # al menos 3 años de entrenamiento
    anios = range(primero, hasta + 1)
    cols = C.MODELOS["M1"]
    pe = modelo.walk_forward(T2, cols, "expansiva", anios)
    pm = modelo.walk_forward(T2, cols, "movil", anios)
    prom = (pe + pm.reindex(pe.index)) / 2
    cal, _ = modelo.platt_anual(prom.dropna(), T2["y"].reindex(prom.dropna().index), anios)
    return cal


def titulo(t):
    print(f"\n{'=' * 100}\n{t}\n{'=' * 100}")


def analisis(res, T, a, b, salida):
    """Todo el análisis prerregistrado sobre el tramo [a, b]. Guarda CSV en `salida`."""
    v = res[a:b].dropna(subset=["y"])
    t = T.reindex(v.index)
    rex = v.rex.fillna(0)
    print(f"Jornadas evaluadas: {len(v)} ({v.index.min().date()} a {v.index.max().date()})")
    csv = {}

    titulo("1. Pronóstico (Brier, log-loss) y tests")
    cols = [f"{m}_{ver}" for m in ["M0", "M1", "M2", "M1C"] for ver in ["exp", "mov", "prom", "cal"]]
    tp = ev.tabla_pronostico(res, cols, a, b)
    print(tp.round(4).to_string()); csv["pronostico"] = tp
    filas = []
    for chico, grande in [("M0_cal", "M1_cal"), ("M1_cal", "M2_cal"), ("M1_cal", "M1C_cal"), ("M0_cal", "M2_cal")]:
        cw_t, cw_p = ev.clark_west(v.y, v[chico], v[grande])
        dm_t, dm_p = ev.diebold_mariano(v.y, v[chico], v[grande])
        filas.append({"comparación": f"{grande} vs {chico}", "CW t": cw_t, "CW p": cw_p, "DM t": dm_t, "DM p": dm_p})
    tt = pd.DataFrame(filas).set_index("comparación")
    print(tt.round(3).to_string()); csv["tests"] = tt
    da, da0, z, pv = ev.pesaran_timmermann(v.y, v.M1_cal)
    print(f"Acierto direccional M1: {da:.3f} (bajo independencia {da0:.3f}; siempre lo más frecuente "
          f"{max(v.y.mean(), 1 - v.y.mean()):.3f}); Pesaran-Timmermann {z:.2f}, p = {pv:.3f}")

    titulo("2. Valor económico (costo 2 pb, carry incluido; regla oficial: M1 + Kelly por utilidad, c = 1/4)")
    filas, curvas = {}, {}
    for c in [C.KELLY_C, C.KELLY_C_ROBUSTEZ]:
        bt = ev.backtest(ev.posicion_kelly_utilidad(v.M1_cal, t.abs_r_60, t.sd_r_60, c=c), rex)
        filas[f"M1 c={c}"] = ev.resumen(bt, v.rex); curvas[f"M1 c={c}"] = bt
    bt = ev.backtest(np.sign(v.M1_cal - .5), rex)
    filas["Señal M1, tamaño fijo 1"] = ev.resumen(bt, v.rex)
    for ref, k in [("Comprar siempre (+1)", 1), ("Comprar siempre (+3)", 3), ("No operar (0)", 0)]:
        bt = ev.backtest(pd.Series(float(k), index=v.index), rex)
        filas[ref] = ev.resumen(bt, v.rex); curvas[ref] = bt
    ve = pd.DataFrame(filas).T
    print(ve.round(2).to_string()); csv["valor_economico"] = ve
    of = curvas[f"M1 c={C.KELLY_C}"]
    print(f"Resultado acumulado neto de la estrategia oficial: {of.neto.sum() * 100:.2f} % "
          f"(comprar siempre: {curvas['Comprar siempre (+1)'].neto.sum() * 100:.2f} %)")

    titulo("3. Resultado por año (estrategia oficial)")
    n, yr = of.neto, of.index.year
    bh = curvas["Comprar siempre (+1)"].neto
    pa = pd.DataFrame({"Retorno neto %": n.groupby(yr).sum() * 100, "Sharpe": n.groupby(yr).apply(SH),
                       "% en 0": (of.pos == 0).groupby(yr).mean() * 100, "% en ±3": (of.pos.abs() == 3).groupby(yr).mean() * 100,
                       "Comprar siempre %": bh.groupby(yr).sum() * 100, "Jornadas": n.groupby(yr).size()})
    print(pa.round(2).to_string()); csv["por_anio"] = pa

    titulo("4. Evaluación formal frente a las referencias (E09): bootstrap estacionario 10.000, Holm, DSR")
    nm = of.neto
    refs = {"No operar (0)": pd.Series(0., index=v.index), "Comprar siempre (+1)": pd.Series(1., index=v.index),
            "Comprar siempre (+3)": pd.Series(3., index=v.index), "Señal M1, tamaño fijo 1": np.sign(v.M1_cal - .5)}
    rob = {}
    for L in [10, 5, 20]:
        idx = ev.indices_bootstrap_estacionario(len(nm), bloque=L)
        R = pd.DataFrame({k: ev.comparar_con_referencia(nm, ev.backtest(p_, rex).neto, idx) for k, p_ in refs.items()}).T
        R["p Holm (retorno)"] = ev.holm(R["p bootstrap (retorno)"])
        if L == 10:
            print("Bloque medio 10 días:"); print(R.round(3).to_string()); csv["evaluacion_formal"] = R
        rob[f"bloque {L}"] = R["p bootstrap (retorno)"]
    print("Robustez al largo de bloque (p bootstrap de la diferencia de retorno):")
    print(pd.DataFrame(rob).round(3).to_string())
    sh = [(lambda n_: n_.mean() / n_.std())(ev.backtest(f(v[f"{m}_{ver}"], t.abs_r_60, t.sd_r_60, c=c), rex).neto)
          for m in ["M1", "M2", "M1C"] for ver in ["exp", "mov", "prom", "cal"] for c in [0.25, 0.2]
          for f in [ev.posicion_kelly_utilidad, ev.posicion_kelly]]
    print(f"Sharpe {SH(nm):.2f} | lugar entre los {len(sh)} ensayos: {int((np.array(sh) > nm.mean() / nm.std() + 1e-12).sum()) + 1}.º")
    filas = []
    for N_ in [len(sh), 100, 200]:
        dsr, sr0, N = ev.sharpe_deflactado(nm, sh, N=N_)
        filas.append({"N": N, "umbral SR0": sr0, "DSR": dsr})
        print(f"   N = {N}: umbral SR0 = {sr0:.2f} | Sharpe deflactado (prob.) = {dsr:.3f}")
    csv["dsr"] = pd.DataFrame(filas)

    titulo("5. Ejecución y tramos del retorno (E07)")
    tramos = [("Torneo: cierre→cierre", "rex_sig"), ("Realista: apertura→apertura", "rex_ap_ap"),
              ("Solo sesión t+1: apertura→cierre", "rex_ap_ci"), ("Solo tramo nocturno (no transable)", "rex_noche")]
    pos = of.pos
    te = pd.DataFrame({nom: ev.resumen(ev.backtest(pos, t[col].fillna(0)), t[col]) for nom, col in tramos}).T
    print(te[["Ret. anual neto %", "Sharpe", "Máx. drawdown %", "Acierto días activos"]].round(2).to_string())
    csv["ejecucion"] = te
    print("Descomposición que suma (% anual; costos cobrados una vez):")
    print(ev.descomposicion_tramos(pos, t).round(2).to_frame(f"{a}–{b}").T.to_string())

    titulo("6. Costos (E08): sensibilidad y costo de equilibrio. 8 pb ≈ spread de estrés de 1,5 CLP (mentoría 6-nov)")
    grid = [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25]
    S = ev.sensibilidad_costos(v.M1_cal, t.abs_r_60, t.sd_r_60, rex, grid)
    sc = S.pivot(index="costo_pb", columns="regla", values=["Ret. anual neto %", "Sharpe"])
    print(sc.round(2).to_string()); csv["sensibilidad_costos"] = S
    filas = []
    for c in [C.KELLY_C, C.KELLY_C_ROBUSTEZ]:
        p_ = ev.posicion_kelly_utilidad(v.M1_cal, t.abs_r_60, t.sd_r_60, c=c)
        for ej, col in [("cierre→cierre", "rex_sig"), ("apertura→apertura", "rex_ap_ap")]:
            filas.append({"c": c, "ejecución": ej, "costo de equilibrio (pb)": ev.costo_equilibrio(p_, t[col].fillna(0))})
    eq = pd.DataFrame(filas)
    print("Costo por unidad de cambio que deja el retorno neto en 0:"); print(eq.round(2).to_string())
    csv["costo_equilibrio"] = eq
    print(f"Tipo de cambio medio del tramo: {t.spot.mean():.0f} CLP/USD (1 CLP ≈ {1e4 / t.spot.mean():.1f} pb)")

    titulo("7. Perfiles de inversionista (E12) y perfiles × ejecución (E13)")
    cols_p = ["Ret. anual neto %", "Vol. anual %", "Sharpe", "Máx. drawdown %", "% días en 0", "Costos / PnL bruto %", "Costo medio (pb)"]
    P = ev.perfiles_inversionista(v.M1_cal, t.abs_r_60, t.sd_r_60, rex, t.spot)
    print(P[cols_p].round(2).to_string()); csv["perfiles_E12"] = P
    E = ev.perfiles_por_ejecucion(v.M1_cal, t.abs_r_60, t.sd_r_60, t)
    print(E[["Ret. anual neto %", "Sharpe", "Máx. drawdown %", "% días en 0"]].round(2).to_string()); csv["perfiles_E13"] = E

    titulo("8. Lectura de la convicción (exigida por las bases): jornadas de máxima exposición (±3) y de abstención (0)")
    g = of.pos.abs()
    s1 = np.sign(v.M1_cal - .5)
    acierto = lambda m: float((np.sign(of.pos[m]) == np.sign(rex[m])).mean()) if (m.sum() and (of.pos[m] != 0).any()) else np.nan
    conv = pd.DataFrame({
        "Jornadas": g.value_counts().sort_index(),
        "% de jornadas": g.value_counts(normalize=True).sort_index() * 100,
        "Convicción media max(p, 1-p)": v.M1_cal.groupby(g).apply(lambda q: np.maximum(q, 1 - q).mean()),
        "Acierto de dirección": pd.Series({k: acierto(g == k) for k in sorted(g.unique())}),
        "Acierto de la señal (signo de p-0,5)": pd.Series({k: float((s1[g == k] == np.sign(rex[g == k])).mean()) for k in sorted(g.unique())}),
        "PnL bruto %": of.bruto.groupby(g).sum() * 100,
        "PnL neto %": of.neto.groupby(g).sum() * 100,
        "|Retorno en exceso| medio (pb)": rex.abs().groupby(g).mean() * 1e4,
    })
    conv.index.name = "|exposición|"
    print(conv.round(3).to_string()); csv["conviccion"] = conv
    m0 = g == 0
    print(f"Abstención: en las {int(m0.sum())} jornadas en 0, seguir el signo de la señal con tamaño 1 habría dado "
          f"{(s1[m0] * rex[m0]).sum() * 100:+.2f} % en bruto (antes de los costos de entrar y salir): es lo que la "
          f"regla dejó pasar por considerar que la ventaja esperada no cubría el riesgo y el costo.")
    m3 = g == 3
    det = pd.DataFrame({"p calibrada": v.M1_cal[m3], "exposición": of.pos[m3], "señal NY": t.ny[m3],
                        "retorno en exceso t+1 (pb)": rex[m3] * 1e4, "PnL neto (pb)": of.neto[m3] * 1e4})
    csv["jornadas_max_exposicion"] = det
    if len(det):
        print(f"Jornadas en ±3: {len(det)}; las 5 mejores y las 5 peores (lista completa en jornadas_max_exposicion.csv):")
        o = det.sort_values("PnL neto (pb)")
        print(pd.concat([o.tail(5)[::-1], o.head(5)]).round(3).to_string())

    titulo("9. Robustez a la muestra de entrenamiento (E15, sugerida en la mentoría del 6-nov para los huecos 2011-2012)")
    print("Mismo M1 y misma regla; solo cambia qué jornadas entran al entrenamiento. El modelo oficial no cambia con esto.")
    base_cal = v.M1_cal
    filas = {}
    for nombre, kw in VARIANTES_E15.items():
        pc = m1_variante(T, int(b), **kw).reindex(v.index)
        ok = pc.notna()
        pv_ = ev.posicion_kelly_utilidad(pc[ok], t.abs_r_60[ok], t.sd_r_60[ok])
        r_ = ev.resumen(ev.backtest(pv_, rex[ok]), v.rex[ok])
        filas[nombre] = {"Jornadas": int(ok.sum()), "Brier": ev.brier(pc[ok], v.y[ok]),
                         "Ret. anual neto %": r_["Ret. anual neto %"], "Sharpe": r_["Sharpe"],
                         "Máx. drawdown %": r_["Máx. drawdown %"],
                         "% jornadas con la misma exposición que el oficial": float((pv_ == of.pos[ok]).mean() * 100),
                         "Corr. de p con el oficial": float(pc[ok].corr(base_cal[ok]))}
    rob_m = pd.DataFrame(filas).T
    print(rob_m.round(3).to_string()); csv["robustez_muestra_E15"] = rob_m

    for k_, df in csv.items():
        df.to_csv(salida / f"{k_}.csv", encoding="utf-8")
    of.to_csv(salida / "serie_diaria_estrategia.csv", encoding="utf-8")
    return v


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ensayo", action="store_true", help="correr sobre la validación 2020-2023 (no mira la prueba)")
    ap.add_argument("--forzar", action="store_true", help="sobrescribir reports/prueba/ (NO usar: la corrida es única)")
    args = ap.parse_args()

    x = datos.cargar_base()
    hoy = pd.Timestamp(dt.date.today())
    if args.ensayo:
        T = datos.recortar(datos.construir_tabla(x))
        a, b = "2020", "2023"
        salida = C.RAIZ / "reports" / "prueba_ensayo"
    else:
        if hoy < pd.Timestamp(C.FECHA_CONGELAMIENTO):
            sys.exit(f"La corrida de prueba solo se permite desde el congelamiento ({C.FECHA_CONGELAMIENTO}).")
        salida = C.RAIZ / "reports" / "prueba"
        if salida.exists() and not args.forzar:
            sys.exit("reports/prueba/ ya existe: la corrida de prueba es única y no se repite.")
        T = datos.construir_tabla(x)
        a, b = "2024", str(T.dropna(subset=["y"]).index.max().year)
    salida.mkdir(parents=True, exist_ok=True)
    anios = range(C.INICIO_OOS, int(b) + 1)

    buf = io.StringIO()
    with redirect_stdout(buf):
        titulo(f"{'ENSAYO sobre la validación' if args.ensayo else 'CORRIDA ÚNICA DEL TRAMO DE PRUEBA'} · {a}–{b}")
        print(f"Generado: {dt.datetime.now():%Y-%m-%d %H:%M} · huella del código {run_daily.huella_codigo()} · "
              f"base {C.ARCHIVO_BASE.name} (huella {datos.huella_archivo()}, último cierre USD/CLP {datos.ultima_jornada(x).date()})")
        print("Modelo congelado: M1 = logit(señal NY, r_CLP), walk-forward anual (expansiva + móvil 1.250, embargo 5), "
              "Platt anual; Kelly discreto por utilidad c = 1/4; costo 2 pb por unidad de cambio.")
        res, _ = modelo.correr_escalera(T, anios)
        analisis(res, T, a, b, salida)
        if not args.ensayo:
            r = figuras.fig_curva_resultado(res, T, tramos=((a, b),), nombre="fig5_curva_prueba.pdf")
            print(f"\nFigura: {r.relative_to(C.RAIZ)}")
    texto = buf.getvalue()
    print(texto)
    (salida / "resultados.txt").write_text(texto, encoding="utf-8")
    print(f"Resultados guardados en {salida.relative_to(C.RAIZ)}/")


if __name__ == "__main__":
    main()
