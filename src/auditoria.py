"""Auditoría de la base USD/CLP (Fase 2 del plan).

Reproduce las pruebas de cada trampa del diccionario y la prueba de la
hipótesis de cierres de Nueva York. Solo usa datos hasta 2023-12-31: el
tramo de prueba (2024-01 en adelante) no se mira.

Uso:  python src/auditoria.py data/base_usdclp.xlsx
Salida: imprime las tablas y guarda reports/auditoria_resultados.txt
"""
# Última actualización: 2026-10-20 17:15 (hora de Chile) — sin cambios de lógica; se agrega sello de versión
import io
import sys
from contextlib import redirect_stdout

import numpy as np
import pandas as pd

FIN_EXPLORACION = "2023-12-31"


def cargar(ruta):
    x = pd.read_excel(ruta, sheet_name="datos").set_index("fecha")
    return x


def px(x, ticker, campo="PX_LAST"):
    return x[f"{ticker}|{campo}"].dropna()


def alinear(v, idx, limit=3):
    """Valor vigente de v en cada fecha de idx (ffill acotado, sin mirar el futuro)."""
    return v.reindex(v.index.union(idx)).ffill(limit=limit).reindex(idx)


def ohlc_por_anio(x):
    u = pd.DataFrame({k: px(x, "USDCLP Curncy", f) for k, f in
                      {"o": "PX_OPEN", "h": "PX_HIGH", "l": "PX_LOW", "c": "PX_LAST"}.items()}).dropna()
    g = pd.DataFrame({
        "jornadas": u.c.groupby(u.index.year).size(),
        "%rango_cero": (u.h == u.l).groupby(u.index.year).mean() * 100,
        "%cierre_repetido": (u.c == u.c.shift()).groupby(u.index.year).mean() * 100,
    })
    print("\n[1] OHLC del USD/CLP por año (rango cero = sin contenido intradía)")
    print(g.round(1).to_string())


def huecos(x):
    s = px(x, "USDCLP Curncy")
    falt = pd.bdate_range("2004-01-01", s.index.max()).difference(s.index)
    print("\n[2] Días hábiles sin cotización desde 2004:", len(falt))
    print(pd.Series(1, index=falt).groupby(falt.year).size().to_string())


def observado(x):
    d = pd.DataFrame({"s": px(x, "USDCLP Curncy"), "ob": px(x, "CLFXDOOB Index")}).dropna()["2004":FIN_EXPLORACION]
    r = np.log(d).diff()
    print("\n[3] Dólar observado: corr(Δobservado_t, Δspot_t+k)")
    for k in range(-2, 3):
        print(f"   k={k:+d}: {r.ob.corr(r.s.shift(-k)):.3f}")


def tasas(x):
    icp = px(x, "CLICP Index")
    dias = icp.index.to_series().diff().dt.days
    cam = ((icp / icp.shift()) ** (1 / dias) - 1) * 360 * 100
    bruta = (icp / icp.shift() - 1) * 360 * 100
    tpm = alinear(px(x, "CHOVCHOV Index"), cam.index, limit=None)
    print("\n[4] Cámara overnight (desde ICP) vs TPM: diferencia media "
          f"{(cam - tpm).mean():.3f} pp; días negativos: {list((cam[cam < 0]).index.date)}")
    print(f"    Sin dividir por días: lunes {bruta[bruta.index.dayofweek == 0].mean():.2f}% vs "
          f"martes {bruta[bruta.index.dayofweek == 1].mean():.2f}%")
    uf = px(x, "CHUF Index")
    print(f"[5] CHON último {px(x, 'CHON Index').iloc[-1]} (real) + UF a/a "
          f"{(uf['2001-08-09'] / uf['2000-08-09'] - 1) * 100:.2f}% ≈ TPM inicial {px(x, 'CHOVCHOV Index').iloc[0]} (nominal)")
    j = pd.DataFrame({"so": px(x, "SOFRRATE Index"), "fe": px(x, "FEDL01 Index")}).dropna()
    print(f"[6] SOFR − Fed Funds: media {(j.so - j.fe).mean() * 100:.1f} pb; p95 |dif| {(j.so - j.fe).abs().quantile(.95) * 100:.1f} pb")


def flujos(x):
    print("\n[7] Flujos BCCh")
    for nueva, vieja in [("CLPBODMB Index", "CLPBODM Index"), ("CLPBLDMB Index", "CLPBLDM Index")]:
        j = pd.DataFrame({"n": px(x, nueva), "o": px(x, vieja)}).dropna()
        print(f"   {nueva} vs {vieja}: traslape {len(j)} días, corr nivel {j.n.corr(j.o):.3f}, "
              f"corr Δ {j.n.diff().corr(j.o.diff()):.3f}, diferencia media {(j.n - j.o).mean():.0f}")
    s = px(x, "USDCLP Curncy")[:FIN_EXPLORACION]
    rc = np.log(s).diff()
    for t in ["CLPBODMB Index", "CLPBSMB Index"]:
        f = px(x, t)[:FIN_EXPLORACION].reindex(s.index).diff()
        print(f"   {t}: corr(Δflujo_t, retorno_t) {f.corr(rc):.3f} | con retorno_t+1 {f.corr(rc.shift(-1)):.3f}")


def senal_ny(x):
    s = px(x, "USDCLP Curncy")["2004":FIN_EXPLORACION]
    o = px(x, "USDCLP Curncy", "PX_OPEN")["2004":FIN_EXPLORACION]
    rc = np.log(s).diff()

    def r(t):
        return np.log(alinear(px(x, t), s.index)).diff()

    R = pd.DataFrame({"mxn": r("USDMXN Curncy"), "zar": r("USDZAR Curncy"), "eur": -r("EURUSD Curncy"),
                      "spx": -r("SPX Index"), "dxy": r("DXY Curncy"), "brl": r("USDBRL Curncy")})
    comp = (R / R.rolling(250, min_periods=60).std().shift(1)).mean(axis=1)

    print("\n[8] Correlación con el USD/CLP: mismo día vs día siguiente")
    filas = []
    for nombre, col in R.items():
        for a, b in [("2004", "2019"), ("2020", "2023")]:
            m = (R.index >= a) & (R.index <= b + "-12-31")
            filas.append((nombre, f"{a}-{b}", col[m].corr(rc[m]), col[m].corr(rc.shift(-1)[m])))
    t = pd.DataFrame(filas, columns=["serie", "tramo", "mismo_dia", "dia_siguiente"])
    print(t.pivot(index="serie", columns="tramo", values=["mismo_dia", "dia_siguiente"]).round(3).to_string())

    y = rc.shift(-1)
    print("\n[9] Señal compuesta: corr con retorno del día siguiente, por año")
    d = pd.DataFrame({"c": comp, "y": y}).dropna()
    print(d.groupby(d.index.year).apply(lambda z: round(z.c.corr(z.y), 3)).to_string())

    print("\n[10] ¿Dónde vive la señal? corr(señal_t, tramo de retorno)")
    D = pd.DataFrame({"c": comp,
                      "cierre→cierre": np.log(s.shift(-1) / s),
                      "cierre→apertura (noche)": np.log(o.shift(-1) / s),
                      "apertura→cierre t+1": np.log(s.shift(-1) / o.shift(-1))}).dropna()
    for a, b in [("2004", "2019"), ("2020", "2023")]:
        z = D[a:b]
        print(f"   {a}-{b}: " + " | ".join(f"{k} {z.c.corr(z[k]):.3f}" for k in D.columns[1:]))


def main(ruta):
    x = cargar(ruta)
    buf = io.StringIO()
    with redirect_stdout(buf):
        print("AUDITORÍA BASE USD/CLP — datos hasta", FIN_EXPLORACION)
        ohlc_por_anio(x)
        huecos(x)
        observado(x)
        tasas(x)
        flujos(x)
        senal_ny(x)
    out = buf.getvalue()
    print(out)
    with open("reports/auditoria_resultados.txt", "w", encoding="utf-8") as f:
        f.write(out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/base_usdclp.xlsx")
