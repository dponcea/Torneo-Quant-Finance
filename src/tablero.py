"""Tablero de la mesa de dinero: un archivo HTML autocontenido que genera run_daily.py.

Muestra, para la fecha de decisión: la señal del día y por qué la regla eligió esa exposición,
el resultado del seguimiento frente a las referencias del torneo, el riesgo de la posición,
el historial de decisiones (contrastado con lo registrado en reports/senales_diarias.csv),
el estado de cada serie de la base y la huella del código.

No estima nada: usa las probabilidades y exposiciones que calculó run_daily.calcular, así que
el tablero muestra exactamente lo que emite la señal. Funciona sin internet (sin librerías externas).
Solo usa información hasta el cierre de la fecha de decisión; la última jornada queda «abierta».
"""
# Última actualización: 2026-10-25 22:04 (hora de Chile) — precio en pesos (cierre, movimiento del dólar, gráfico con compras y ventas, PnL en pesos), separado del resultado en %
import datetime as dt
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C, evaluacion as ev

K_POSIBLES = [-3, -1, 0, 1, 3]

# Referencias del torneo (mismas que la sección 10 del notebook). «Exposición fija 1» es ambigua
# en las bases: se muestran ambas lecturas (+1 siempre y señal M1 con tamaño fijo 1).
REFERENCIAS = {
    "comprar1": "Comprar siempre (+1)",
    "comprar3": "Comprar siempre (+3)",
    "no_operar": "No operar (0)",
    "tam_fijo": "Señal M1, tamaño fijo 1",
}

# Series de la base que usa la señal: (columna, papel, holgura en días corridos)
SERIES = [
    ("USDCLP Curncy|PX_LAST", "Tipo de cambio (cierre): objetivo, r_CLP y riesgo", 0),
    ("USDCLP Curncy|PX_OPEN", "Apertura (ejecución alternativa, E13)", 0),
    ("USDCLP Curncy|PX_HIGH", "Máximo (filtro de cotizaciones rancias)", 0),
    ("USDCLP Curncy|PX_LOW", "Mínimo (filtro de cotizaciones rancias)", 0),
    *[(f"{t}|PX_LAST", "Señal NY", 0) for t in C.PARES_NY],
    ("CLICP Index|PX_LAST", "Carry: tasa de cámara (ICP)", 4),
    ("CHOVCHOV Index|PX_LAST", "Carry: TPM (respaldo del ICP)", 31),
    ("FEDL01 Index|PX_LAST", "Carry: Fed Funds (rezagada 1 día)", 4),
]
CONTEXTO = [  # no entran al modelo; solo dan contexto de mercado en la sección de riesgo
    ("USDCLPV1M Curncy|PX_LAST", "Volatilidad implícita USD/CLP 1M"),
    ("JPMVXYEM Index|PX_LAST", "Volatilidad de monedas emergentes (EM-VXY)"),
    ("HG1 Comdty|PX_LAST", "Cobre COMEX"),
]


def _f(v, nd=6):
    """Número para JSON (None si no es finito)."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return round(v, nd) if np.isfinite(v) else None


def _metricas(bt, rex, nombre_modelo=False):
    n = bt["neto"]
    acum = n.cumsum()
    dd = acum - acum.cummax()
    d = len(n)
    out = {
        "acum": _f(acum.iloc[-1] * 100 if d else 0, 3),
        "anual": _f(n.mean() * 252 * 100 if d else None, 2),
        "vol": _f(n.std() * np.sqrt(252) * 100 if d > 1 else None, 2),
        "sharpe": _f(n.mean() / n.std() * np.sqrt(252) if d > 1 and n.std() > 0 else None, 2),
        "maxdd": _f(dd.min() * 100 if d else 0, 3),
        "dd_actual": _f(dd.iloc[-1] * 100 if d else 0, 3),
        "costos": _f(bt["costo"].sum() * 100, 3),
        "rotacion": _f(bt["pos"].diff().abs().fillna(bt["pos"].abs()).sum(), 0),
        "jornadas": d,
    }
    if nombre_modelo:
        act = bt.pos != 0
        out["acierto"] = _f((np.sign(bt.pos[act]) == np.sign(rex[act])).mean() * 100 if act.sum() else None, 1)
        out["dias_activos"] = int(act.sum())
        out["mejor"] = _f(n.max() * 1e4, 1)
        out["peor"] = _f(n.min() * 1e4, 1)
    return out


def _ventana(nombre, etiqueta, desde, pos, p, tabla, fecha):
    """Backtest de modelo y referencias desde `desde` (cada estrategia parte sin posición)."""
    rex = tabla["rex_sig"]
    idx = pos.index[(pos.index >= desde) & (pos.index < fecha)]
    idx = idx[rex.reindex(idx).notna()]              # jornadas con resultado conocido
    if len(idx) == 0:
        return None
    r = rex.reindex(idx)
    estr = {"modelo": pos.reindex(idx),
            "comprar1": pd.Series(1.0, index=idx), "comprar3": pd.Series(3.0, index=idx),
            "no_operar": pd.Series(0.0, index=idx), "tam_fijo": np.sign(p.reindex(idx) - 0.5)}
    curvas, metr = {}, {}
    for k, s in estr.items():
        bt = ev.backtest(s, r)
        curvas[k] = [_f(v * 100, 4) for v in bt["neto"].cumsum()]
        metr[k] = _metricas(bt, r, nombre_modelo=(k == "modelo"))
    bt_m = ev.backtest(estr["modelo"], r)
    return {
        "nombre": nombre, "etiqueta": etiqueta,
        "desde": idx[0].date().isoformat(), "hasta": idx[-1].date().isoformat(),
        "fechas": [d.date().isoformat() for d in idx],
        "k": [int(v) for v in estr["modelo"]],
        "p": [_f(v, 4) for v in p.reindex(idx)],
        "rex_pb": [_f(v * 1e4, 1) for v in r],
        "pnl_pb": [_f(v * 1e4, 2) for v in bt_m["neto"]],
        "spot": [_f(v, 2) for v in tabla["spot"].reindex(idx)],        # precio de cierre en pesos (solo para mostrar)
        "k_antes": int(pos[pos.index < idx[0]].iloc[-1]) if (pos.index < idx[0]).any() else 0,
        "curvas": curvas, "metricas": metr,
        "dist": {str(k): int((estr["modelo"] == k).sum()) for k in K_POSIBLES},
    }


def _utilidades(mu, sigma, k_prev, c=C.KELLY_C, costo=C.COSTO_POR_UNIDAD):
    """U(k) = k·mu − k²·sigma²/(2c) − costo·|k − k_anterior|, en pb (la regla elige el máximo)."""
    filas = []
    for k in K_POSIBLES:
        ganancia, riesgo, cst = k * mu, k ** 2 * sigma ** 2 / (2 * c), costo * abs(k - k_prev)
        filas.append({"k": k, "ganancia": _f(ganancia * 1e4, 2), "riesgo": _f(-riesgo * 1e4, 2),
                      "costo": _f(-cst * 1e4, 2), "u": _f((ganancia - riesgo - cst) * 1e4, 2)})
    return filas


def _estado_datos(x, fecha, tabla):
    filas = []
    for col, papel, holgura in SERIES:
        if col not in x.columns:
            filas.append({"serie": col, "papel": papel, "ultima": None, "atraso": None, "estado": "falta"})
            continue
        ult = x[col].last_valid_index()
        atraso = (fecha - ult).days if ult is not None else None
        estado = "ok" if atraso is not None and atraso <= holgura else "atrasada"
        filas.append({"serie": col.replace("|", " · "), "papel": papel,
                      "ultima": ult.date().isoformat() if ult is not None else None,
                      "atraso": atraso, "estado": estado})
    insumos = {c: _f(tabla.loc[fecha, c], 4) for c in ["ny", "r_clp", "abs_r_60", "sd_r_60", "carry", "spot"]}
    return filas, insumos


def _contexto_mercado(x, fecha):
    out = []
    for col, nombre in CONTEXTO:
        if col not in x.columns:
            continue
        s = x[col].dropna()
        s = s[s.index <= fecha]
        if s.empty:
            continue
        ult = float(s.iloc[-1])
        u5 = s[s.index > fecha - pd.Timedelta(days=5 * 365)]
        pct = float((u5 <= ult).mean() * 100)
        var20 = float(np.log(ult / s.iloc[-21]) * 100) if len(s) > 21 else None
        out.append({"nombre": nombre, "valor": _f(ult, 3), "fecha": s.index[-1].date().isoformat(),
                    "percentil5a": _f(pct, 0), "var20": _f(var20, 2)})
    return out


def _sellos():
    """Línea «Última actualización» de cada archivo del código."""
    out = []
    archivos = sorted((C.RAIZ / "src").glob("*.py")) + [C.RAIZ / "run_daily.py"]
    for f in archivos:
        if not f.exists():
            continue
        m = re.search(r"#\s*Última actualización:\s*(.+)", f.read_text(encoding="utf-8"))
        out.append({"archivo": str(f.relative_to(C.RAIZ)).replace("\\", "/"),
                    "sello": m.group(1).strip() if m else "sin sello"})
    return out


def _registro(archivo, pos, tabla, fecha):
    """Historial: últimas 30 decisiones, contrastadas con lo que quedó registrado ese día."""
    reg = {}
    if archivo is not None and Path(archivo).exists():
        r = pd.read_csv(archivo, dtype=str)
        reg = {row["fecha_decision"]: row for _, row in r.iterrows()}
    ult = pos[pos.index <= fecha].iloc[-30:]
    filas = []
    for d, k in ult.items():
        clave = d.date().isoformat()
        rx = tabla["rex_sig"].get(d, np.nan)
        prev = pos.shift(1).get(d, 0.0)
        costo = C.COSTO_POR_UNIDAD * abs(k - (0.0 if np.isnan(prev) else prev))
        pnl = k * rx - costo if np.isfinite(rx) else None
        s0, s1 = tabla["spot"].get(d, np.nan), tabla["spot"].shift(-1).get(d, np.nan)
        r = reg.get(clave)
        k_reg = int(float(r["exposicion"])) if r is not None and str(r.get("exposicion", "")) not in ("", "nan") else None
        filas.append({"fecha": clave, "k": int(k), "ny": _f(tabla.loc[d, "ny"], 2),
                      "rex_pb": _f(rx * 1e4, 1), "pnl_pb": _f(pnl * 1e4, 1) if pnl is not None else None,
                      "spot": _f(s0, 2), "dspot": _f(s1 - s0, 2) if np.isfinite(rx) else None,
                      # resultado en pesos por USD 1 MM de nocional por unidad (≈ retorno neto × nocional × tipo de cambio)
                      "pnl_clp": _f(pnl * s0 * 1e6, 0) if pnl is not None else None,
                      "k_registrada": k_reg, "emitida": r.get("emitida") if r is not None else None,
                      "huella": r.get("huella_codigo") if r is not None else None,
                      "coincide": (k_reg == int(k)) if k_reg is not None else None})
    return filas[::-1], len(reg)


def generar(fila, ctx, desde=None, archivo_registro=None, salida=None):
    """Escribe reports/tablero.html y una copia en reports/tableros/tablero_<fecha>.html."""
    x, tabla, p, pos, fecha = ctx["x"], ctx["tabla"], ctx["p_cal"], ctx["pos"], ctx["fecha"]
    monitoreo = fecha >= pd.Timestamp(C.INICIO_MONITOREO)
    if desde is None:
        desde = pd.Timestamp(C.INICIO_MONITOREO) if monitoreo else pd.Timestamp(f"{fecha.year}-01-01")
    desde = pd.Timestamp(desde)

    ventanas = []
    w = _ventana("seguimiento", "Seguimiento", desde, pos, p, tabla, fecha)
    if w:
        ventanas.append(w)
    anio = pd.Timestamp(f"{fecha.year}-01-01")
    if anio != desde:
        w = _ventana("anio", f"Año {fecha.year}", anio, pos, p, tabla, fecha)
        if w:
            ventanas.append(w)
    w = _ventana("historico", "Desde 2011", pd.Timestamp("2011-01-01"), pos, p, tabla, fecha)
    if w:
        ventanas.append(w)

    k, sigma, mu, spot = fila["exposicion"], ctx["sigma"], ctx["mu"], float(tabla.loc[fecha, "spot"])
    pnl_hist = (pos * tabla["rex_sig"]).dropna()
    rex_250 = tabla["rex_sig"].dropna()
    rex_250 = rex_250[rex_250.index < fecha].iloc[-250:]
    var_hist = float(-np.percentile(k * rex_250, 5)) if k != 0 else 0.0
    riesgo = {
        "sigma_pb": _f(sigma * 1e4, 1), "sigma_pos_pb": _f(abs(k) * sigma * 1e4, 1),
        "var95_normal_pb": _f(1.645 * abs(k) * sigma * 1e4, 1),
        "var95_hist_pb": _f(var_hist * 1e4, 1),
        "peor_250_pb": _f(-(k * rex_250).min() * 1e4 if k != 0 else 0, 1),
        "spot": _f(spot, 2),
        "clp_por_millon": _f(1.645 * abs(k) * sigma * spot * 1e6, 0),   # VaR normal en CLP por USD 1 MM por unidad
        "carry_anual_pct": _f(tabla.loc[fecha, "carry"], 2),
        "carry_dia_pb": _f(-k * tabla.loc[fecha, "carry"] / 100 / 360 * 1e4, 2),   # lo que paga/recibe la posición por día corrido
    }
    datos_estado, insumos = _estado_datos(x, fecha, tabla)
    historial, n_registradas = _registro(archivo_registro, pos, tabla, fecha)
    base = Path(C.ARCHIVO_BASE)
    hoy = pd.Timestamp(dt.date.today())

    data = {
        "senal": {**{k_: v for k_, v in fila.items()}, "mu_pb": _f(mu * 1e4, 2), "spot": _f(spot, 2),
                  "spot_ant": _f(tabla["spot"][tabla.index < fecha].iloc[-1], 2)},
        "utilidades": _utilidades(mu, sigma, ctx["k_prev"]),
        "ventanas": ventanas, "riesgo": riesgo, "mercado": _contexto_mercado(x, fecha),
        "datos": datos_estado, "insumos": insumos, "historial": historial,
        "n_registradas": n_registradas,
        "referencias": REFERENCIAS,
        "meta": {
            "modo": "monitoreo" if monitoreo else "simulacion",
            "desde": desde.date().isoformat(),
            "inicio_monitoreo": C.INICIO_MONITOREO, "fin_monitoreo": C.FIN_MONITOREO,
            "congelamiento": C.FECHA_CONGELAMIENTO,
            "candado": bool(hoy < pd.Timestamp(C.FECHA_CONGELAMIENTO)),
            "base_archivo": base.name,
            "base_modificada": dt.datetime.fromtimestamp(base.stat().st_mtime).strftime("%Y-%m-%d %H:%M") if base.exists() else None,
            "modelo": "M1 = logit(señal NY, r_CLP) · Platt anual · Kelly discreto por utilidad",
            "variables": C.MODELOS["M1"], "kelly_c": C.KELLY_C, "costo_pb": C.COSTO_POR_UNIDAD * 1e4,
            "sellos": _sellos(),
            "generado": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        },
    }
    html = PLANTILLA.replace("/*__DATOS__*/null", json.dumps(data, ensure_ascii=False, allow_nan=False).replace("</", "<\\/"))
    salida = Path(salida) if salida else C.RAIZ / "reports" / "tablero.html"
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(html, encoding="utf-8")
    copia = salida.parent / "tableros" / f"tablero_{fecha.date().isoformat()}.html"
    copia.parent.mkdir(exist_ok=True)
    copia.write_text(html, encoding="utf-8")
    return salida


PLANTILLA = (Path(__file__).with_name("tablero_plantilla.html")).read_text(encoding="utf-8")
