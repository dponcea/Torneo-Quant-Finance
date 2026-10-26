"""Señal diaria del torneo USD/CLP: exposición para la jornada siguiente.

Uso (desde la carpeta del proyecto, después de actualizar el Excel de la base):

    python run_daily.py                    # usa la última fecha disponible en la base
    python run_daily.py --fecha 2023-12-28 # simula la decisión de un día pasado
    python run_daily.py --fecha 2023-12-28 --desde 2023-11-13   # tablero con seguimiento desde esa fecha

Qué hace, con el modelo congelado (M1 + Platt + Kelly fraccional, ver src/config.py):
  1. Construye la tabla de variables con información hasta el cierre de la fecha de decisión.
  2. Estima el logit M1 del año en curso con las jornadas anteriores al 1 de enero
     (ventanas expansiva y móvil, embargo de 5 jornadas), igual que en el walk-forward.
  3. Calibra con Platt usando todas las predicciones fuera de muestra de los años anteriores.
  4. Aplica la regla de Kelly discreta y entrega la exposición en {-3, -1, 0, +1, +3}.
  5. Agrega una fila a reports/senales_diarias.csv (una por fecha de decisión).
  6. Genera el tablero de la mesa de dinero en reports/tablero.html (y una copia con fecha en
     reports/tableros/): señal del día, resultado del seguimiento frente a las referencias,
     riesgo, historial de decisiones, estado de los datos y huella del código.

Cuándo correrlo: después del cierre de Nueva York (17:00 ET, ~18:00-19:00 hora de Chile),
cuando la base ya trae los cierres del día de MXN, ZAR, BRL, DXY, EURUSD y S&P 500.

Disciplina: antes de C.FECHA_CONGELAMIENTO el script se niega a usar fechas posteriores a
C.FIN_EXPLORACION, para no mirar el tramo de prueba antes de la corrida única.
El candado usa la fecha del sistema del computador: evita un accidente, pero no es una
garantía (cambiar la fecha del sistema lo desactiva). La garantía es el registro de
experimentos y la huella del código de cada señal.
"""
# Última actualización: 2026-10-25 20:16 (hora de Chile) — calcular() devuelve el contexto para el tablero; genera reports/tablero.html (--no-tablero, --desde); la señal no cambia
import argparse
import datetime as dt
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from src import config as C, datos, modelo, evaluacion as ev

MODELO = "M1"
ARCHIVO_REGISTRO = C.RAIZ / "reports" / "senales_diarias.csv"


def huella_codigo():
    """Huella corta del código y los parámetros (para saber con qué versión se emitió cada señal)."""
    h = hashlib.sha256()
    for f in sorted((C.RAIZ / "src").glob("*.py")) + [Path(__file__)]:
        h.update(f.read_bytes())
    return h.hexdigest()[:10]


def _predecir(tabla, cols, ventana, anio, embargo=5):
    """Probabilidad bruta para TODAS las jornadas del año `anio` con variables completas
    (incluida la última, cuyo resultado aún no se conoce)."""
    validas = modelo._filas_validas(tabla, cols)
    train = validas[validas.index < f"{anio}-01-01"].iloc[:-embargo]
    if ventana == "movil":
        train = train.iloc[-C.VENTANA_MOVIL:]
    res, media, desv = modelo.ajustar(train, cols)
    filas = tabla[(tabla.index >= f"{anio}-01-01")].dropna(subset=cols)
    return pd.Series(res.predict(modelo._diseno(filas, cols, media, desv)), index=filas.index)


def calcular(fecha=None):
    """Calcula la señal de `fecha` y devuelve (fila del registro, contexto para el tablero).

    El contexto trae la base recortada a la fecha, la tabla de variables, las probabilidades
    calibradas y la trayectoria de exposiciones desde 2011: el tablero no recalcula el modelo."""
    x = datos.cargar_base()
    ultima_base = x.index.max()
    fecha = pd.Timestamp(fecha) if fecha else ultima_base

    hoy = pd.Timestamp(dt.date.today())
    if hoy < pd.Timestamp(C.FECHA_CONGELAMIENTO) and fecha > pd.Timestamp(C.FIN_EXPLORACION):
        sys.exit(f"Antes del congelamiento ({C.FECHA_CONGELAMIENTO}) solo se permiten fechas hasta "
                 f"{C.FIN_EXPLORACION}. Usa --fecha con un día de 2023 para probar el script.")

    x = x[x.index <= fecha]
    tabla = datos.construir_tabla(x)
    if fecha not in tabla.index:
        sys.exit(f"{fecha.date()} no es una jornada válida del USD/CLP en la base.")

    # Frescura: cada serie de la señal NY debe tener cierre en la fecha de decisión.
    avisos = [f"{t}: último cierre {x[f'{t}|PX_LAST'].last_valid_index().date()}"
              for t in C.PARES_NY if x[f"{t}|PX_LAST"].last_valid_index() < fecha]

    cols = C.MODELOS[MODELO]
    anio = fecha.year
    anios_hist = list(range(C.INICIO_OOS, anio))

    # Predicciones fuera de muestra de años anteriores (para Platt y para la trayectoria de posiciones)
    hist = (modelo.walk_forward(tabla, cols, "expansiva", anios_hist)
            + modelo.walk_forward(tabla, cols, "movil", anios_hist)) / 2
    y_hist = tabla["y"].reindex(hist.index)
    cal_hist, _ = modelo.platt_anual(hist, y_hist, anios_hist)

    # Año en curso: modelo estimado con datos anteriores al 1 de enero
    p_anio = ((_predecir(tabla, cols, "expansiva", anio) + _predecir(tabla, cols, "movil", anio)) / 2
              ).clip(modelo.EPS, 1 - modelo.EPS)
    lg = np.log(hist / (1 - hist))
    platt = sm.Logit(y_hist, sm.add_constant(lg, has_constant="add")).fit(disp=0)
    a, b = platt.params.values
    lg_anio = np.log(p_anio / (1 - p_anio))
    cal_anio = pd.Series(1 / (1 + np.exp(-(a + b * lg_anio))), index=p_anio.index)

    # Trayectoria de exposiciones desde 2011 (la regla depende de la posición anterior)
    p_cal = pd.concat([cal_hist[cal_hist.index >= "2011-01-01"], cal_anio]).sort_index()
    t = tabla.reindex(p_cal.index)
    pos = ev.posicion_kelly_utilidad(p_cal, t.abs_r_60, t.sd_r_60, c=C.KELLY_C)

    k, k_prev = pos.loc[fecha], (pos.iloc[-2] if len(pos) > 1 else 0.0)
    mu = (2 * p_cal.loc[fecha] - 1) * tabla.loc[fecha, "abs_r_60"]
    fila = {
        "fecha_decision": fecha.date().isoformat(),
        "ultima_fecha_base": ultima_base.date().isoformat(),
        "p_bruta": round(float(p_anio.loc[fecha]), 4),
        "p_calibrada": round(float(p_cal.loc[fecha]), 4),
        "platt_a": round(float(a), 4), "platt_b": round(float(b), 4),
        "mu_pb": round(float(mu) * 1e4, 2),
        "sigma_pb": round(float(tabla.loc[fecha, "sd_r_60"]) * 1e4, 2),
        "senal_ny": round(float(tabla.loc[fecha, "ny"]), 3),
        "exposicion": int(k),
        "exposicion_anterior": int(k_prev),
        "cambio": int(k - k_prev),
        "direccion": "compra USD" if k > 0 else ("vende USD" if k < 0 else "sin posición"),
        "kelly_c": C.KELLY_C, "costo_pb": C.COSTO_POR_UNIDAD * 1e4,
        "huella_codigo": huella_codigo(),
        "emitida": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "avisos": " | ".join(avisos),
    }
    contexto = {"x": x, "tabla": tabla, "p_cal": p_cal, "pos": pos, "fecha": fecha,
                "mu": float(mu), "sigma": float(tabla.loc[fecha, "sd_r_60"]), "k_prev": float(k_prev)}
    return fila, contexto


def senal(fecha=None):
    """Fila del registro para `fecha` (la usa tests/test_run_daily.py)."""
    return calcular(fecha)[0]


def registrar(fila):
    ARCHIVO_REGISTRO.parent.mkdir(exist_ok=True)
    nuevo = pd.DataFrame([fila])
    if ARCHIVO_REGISTRO.exists():
        previo = pd.read_csv(ARCHIVO_REGISTRO, dtype=str)
        previo = previo[previo["fecha_decision"] != fila["fecha_decision"]]   # una fila por fecha
        nuevo = pd.concat([previo, nuevo.astype(str)], ignore_index=True)
    nuevo.sort_values("fecha_decision").to_csv(ARCHIVO_REGISTRO, index=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fecha", help="fecha de decisión AAAA-MM-DD (por defecto, la última de la base)")
    ap.add_argument("--no-registrar", action="store_true", help="no escribir en reports/senales_diarias.csv")
    ap.add_argument("--no-tablero", action="store_true", help="no generar el tablero HTML (reports/tablero.html)")
    ap.add_argument("--desde", help="inicio del seguimiento en el tablero AAAA-MM-DD (por defecto, "
                    "C.INICIO_MONITOREO; en una simulación anterior, el 1 de enero del año de la fecha)")
    args = ap.parse_args()

    s, ctx = calcular(args.fecha)
    print(f"\nSeñal USD/CLP · decisión al cierre del {s['fecha_decision']} (para la jornada siguiente)")
    print(f"  Probabilidad de que el dólar suba en exceso de carry: {s['p_calibrada']:.1%} "
          f"(bruta {s['p_bruta']:.1%}; señal NY {s['senal_ny']:+.2f})")
    print(f"  Retorno esperado {s['mu_pb']:+.1f} pb · riesgo diario {s['sigma_pb']:.1f} pb")
    print(f"  EXPOSICIÓN: {s['exposicion']:+d}  ({s['direccion']}; antes {s['exposicion_anterior']:+d}, "
          f"cambio {s['cambio']:+d})")
    print(f"  Versión del código: {s['huella_codigo']}")
    if s["avisos"]:
        print(f"  ATENCIÓN, series sin cierre en la fecha de decisión: {s['avisos']}")
    if not args.no_registrar:
        registrar(s)
        print(f"  Registrada en {ARCHIVO_REGISTRO.relative_to(C.RAIZ)}")
    if not args.no_tablero:
        from src import tablero
        ruta = tablero.generar(s, ctx, desde=args.desde, archivo_registro=ARCHIVO_REGISTRO)
        print(f"  Tablero: {ruta.relative_to(C.RAIZ)}  (ábrelo con doble clic; funciona sin internet)")


if __name__ == "__main__":
    main()
