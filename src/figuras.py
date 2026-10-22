"""Figuras del informe (PDF vectorial, tipografía tipo Times, legibles en blanco y negro)."""
# Última actualización: 2026-10-21 21:54 (hora de Chile) — Figura 3: tramos nocturno y sesión en bruto (costos cobrados una vez)
from pathlib import Path

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config as C, evaluacion as ev

CARPETA = C.RAIZ / "reports" / "figuras"
ANCHO = 6.3            # pulgadas ≈ ancho del texto del informe (16 cm)

# Estrategia en un color de acento; referencias en grises con trazos distintos (legible impreso)
ESTILO = {
    "Estrategia M1": dict(color="#1f4e79", lw=1.6, ls="-"),
    "Comprar siempre (+1)": dict(color="#555555", lw=1.1, ls="--"),
    "Señal con tamaño fijo": dict(color="#8c8c8c", lw=1.1, ls="-."),
    "No operar": dict(color="#b3b3b3", lw=0.9, ls=":"),
}


def estilo_paper():
    matplotlib.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Nimbus Roman", "STIXGeneral", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 9, "axes.titlesize": 9, "axes.labelsize": 9,
        "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": "#e3e3e3", "grid.linewidth": 0.5,
        "axes.edgecolor": "#666666", "axes.linewidth": 0.6,
        "pdf.fonttype": 42, "savefig.bbox": "tight", "savefig.dpi": 300,
    })


def _eje_anios(ax, a, b):
    """Marcas anuales legibles: cada 2 años si el tramo es largo."""
    paso = 2 if int(b) - int(a) > 5 else 1
    ax.xaxis.set_major_locator(mdates.YearLocator(paso))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


def _leyenda_abajo(fig, ejes_ref, ncol=4, y=-0.04):
    h, l = ejes_ref.get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=ncol, frameon=False, bbox_to_anchor=(0.5, y))


def _guardar(fig, nombre):
    CARPETA.mkdir(parents=True, exist_ok=True)
    ruta = CARPETA / nombre
    fig.savefig(ruta)
    plt.close(fig)
    return ruta


def _series_tramo(res, T, a, b):
    v = res[a:b].dropna(subset=["y"])
    t = T.reindex(v.index)
    rex = v.rex.fillna(0)
    pos = ev.posicion_kelly_utilidad(v.M1_cal, t.abs_r_60, t.sd_r_60)
    netos = {
        "Estrategia M1": ev.backtest(pos, rex).neto,
        "Comprar siempre (+1)": ev.backtest(pd.Series(1.0, index=v.index), rex).neto,
        "Señal con tamaño fijo": ev.backtest(np.sign(v.M1_cal - 0.5), rex).neto,
        "No operar": pd.Series(0.0, index=v.index),
    }
    return netos, pos


def fig_curva_resultado(res, T, tramos=(("2011", "2019"), ("2020", "2023")), nombre="fig1_curva_resultado.pdf"):
    """Figura 1 (exigida por las bases): resultado acumulado neto frente a las referencias y exposición diaria."""
    estilo_paper()
    fig, ejes = plt.subplots(2, len(tramos), figsize=(ANCHO, 3.9), sharex="col",
                             gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08, "wspace": 0.18})
    ejes = np.atleast_2d(ejes).reshape(2, len(tramos))
    for j, (a, b) in enumerate(tramos):
        netos, pos = _series_tramo(res, T, a, b)
        arriba, abajo = ejes[0, j], ejes[1, j]
        for nom, n in netos.items():
            arriba.plot(n.index, n.cumsum() * 100, label=nom, **ESTILO[nom])
        arriba.set_title(f"{a}–{b}")
        arriba.set_ylabel("Resultado acumulado neto (%)" if j == 0 else "")
        abajo.step(pos.index, pos.values, where="post", color="#1f4e79", lw=0.5)
        abajo.set_ylim(-3.6, 3.6)
        abajo.set_yticks([-3, -1, 0, 1, 3])
        abajo.set_ylabel("Exposición" if j == 0 else "")
        abajo.grid(axis="x", visible=False)
        _eje_anios(abajo, a, b)
    _leyenda_abajo(fig, ejes[0, 0], y=0.02)
    return _guardar(fig, nombre)


def fig_confiabilidad(res, a="2011", b="2023", grupos=5, nombre="fig2_confiabilidad.pdf"):
    """Figura 2: probabilidad pronosticada vs frecuencia observada de alzas, antes y después de Platt
    (quintiles de probabilidad; barras = intervalo de confianza al 95 %)."""
    estilo_paper()
    v = res[a:b].dropna(subset=["y", "M1_prom", "M1_cal"])
    fig, ax = plt.subplots(figsize=(ANCHO * 0.55, ANCHO * 0.55))
    lo, hi = 0.36, 0.64
    ax.plot([lo, hi], [lo, hi], color="#999999", lw=0.8, ls="--", label="Calibración perfecta")
    for col, nom, kw in [("M1_prom", "Sin calibrar", dict(color="#8c8c8c", marker="o", mfc="white")),
                         ("M1_cal", "Calibrada (Platt)", dict(color="#1f4e79", marker="s"))]:
        q = pd.qcut(v[col], grupos, duplicates="drop")
        g = v.groupby(q, observed=True).agg(p=(col, "mean"), f=("y", "mean"), n=("y", "size"))
        se = np.sqrt(g.f * (1 - g.f) / g.n)
        ax.errorbar(g.p, g.f, yerr=1.96 * se, lw=1.1, ms=4, capsize=2, elinewidth=0.6, label=nom, **kw)
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_xlabel("Probabilidad pronosticada de alza")
    ax.set_ylabel("Frecuencia observada de alzas")
    ax.set_title(f"Quintiles de probabilidad, {a}–{b}")
    ax.legend(loc="upper left", frameon=False)
    return _guardar(fig, nombre)


def fig_tramos_retorno(res, T, tramos=(("2011", "2019"), ("2020", "2023")), nombre="fig3_tramos_retorno.pdf"):
    """Figura 3: resultado acumulado de la misma estrategia según el tramo del retorno de t+1."""
    estilo_paper()
    fig, ejes = plt.subplots(1, len(tramos), figsize=(ANCHO, 2.7), sharey=False, gridspec_kw={"wspace": 0.18})
    # Netas (carry y costos): las dos ejecuciones. Brutas (sin carry ni costos): los dos tramos del
    # retorno cierre a cierre, que así suman exactamente el retorno del tipo de cambio (auditoría B9).
    series = [("rex_sig", "Cierre a cierre, neto (torneo)", "neto", dict(color="#1f4e79", lw=1.6, ls="-")),
              ("rex_ap_ap", "Apertura a apertura, neto (realista)", "neto", dict(color="#1f4e79", lw=1.0, ls=":")),
              ("rex_noche", "Cierre → apertura, bruto (no transable)", "bruto", dict(color="#555555", lw=1.1, ls="--")),
              ("rex_ap_ci", "Apertura → cierre, bruto (sesión)", "bruto", dict(color="#8c8c8c", lw=1.1, ls="-."))]
    for j, (a, b) in enumerate(tramos):
        v = res[a:b].dropna(subset=["y"])
        t = T.reindex(v.index)
        pos = ev.posicion_kelly_utilidad(v.M1_cal, t.abs_r_60, t.sd_r_60)
        ax = ejes[j]
        for col, nom, tipo, kw in series:
            n = ev.backtest(pos, t[col].fillna(0))[tipo]
            ax.plot(n.index, n.cumsum() * 100, label=nom, **kw)
        ax.axhline(0, color="#999999", lw=0.6)
        ax.set_title(f"{a}–{b}")
        ax.set_ylabel("Resultado acumulado (%)" if j == 0 else "")
        _eje_anios(ax, a, b)
    _leyenda_abajo(fig, ejes[0], ncol=2, y=0.0)
    return _guardar(fig, nombre)


# Canales de costo (pb por unidad de cambio de exposición) para la Figura de costos
CANALES = [
    ("CFD con broker internacional", 2, 4),
    ("Institucional (0,5 CLP)", 6.2, 8.5),
    ("Plataformas de criptoactivos", 7, 10),
    ("Aplicaciones y corredoras", 10, 40),
    ("Minorista (2 CLP)", 24.7, 33.9),
    ("Banca privada (3 CLP)", 29, 31),
]


def fig_costos(res, T, tramos=(("2020", "2023"), ("2011", "2019")), cmax=40, nombre="fig4_costos.pdf"):
    """Figura de costos: retorno neto anual según el costo por unidad de cambio de exposición
    (posiciones decididas con 2 pb), con el costo de equilibrio y los canales de inversión."""
    estilo_paper()
    fig, (ax, axc) = plt.subplots(2, 1, figsize=(ANCHO, 3.9), sharex=True,
                                  gridspec_kw={"height_ratios": [2.6, 1.3], "hspace": 0.08})
    costos = np.linspace(0, cmax, 161)
    estilos = [dict(color="#1f4e79", lw=1.6, ls="-"), dict(color="#555555", lw=1.2, ls="--")]
    for (a, b), kw in zip(tramos, estilos):
        v = res[a:b].dropna(subset=["y"])
        t = T.reindex(v.index)
        rex = v.rex.fillna(0)
        pos = ev.posicion_kelly_utilidad(v.M1_cal, t.abs_r_60, t.sd_r_60)
        bruto = (pos * rex).mean() * 252
        rot = pos.diff().abs().fillna(pos.abs()).mean() * 252
        ax.plot(costos, (bruto - costos * 1e-4 * rot) * 100, label=f"{a}–{b}", **kw)
        eq = ev.costo_equilibrio(pos, rex)
        ax.plot([eq], [0], marker="o", ms=4.5, color=kw["color"], zorder=5)
        ax.annotate(f"{eq:.1f} pb".replace(".", ","), (eq, 0), xytext=(4, 6), textcoords="offset points",
                    fontsize=8, color=kw["color"])
    ax.axhline(0, color="#666666", lw=0.7)
    ax.axvline(2, color="#999999", lw=0.7, ls=":")
    ax.annotate("costo del torneo (2 pb)", (2, ax.get_ylim()[1]), xytext=(3, -10), textcoords="offset points",
                fontsize=7.5, color="#666666")
    ax.set_ylabel("Retorno neto anual (%)")
    ax.legend(loc="upper right", frameon=False)
    for i, (nom, lo, hi) in enumerate(CANALES):
        y = len(CANALES) - i
        axc.plot([lo, min(hi, cmax)], [y, y], color="#8c8c8c", lw=4, solid_capstyle="butt")
        if hi >= cmax:   # la barra llega al borde: rótulo bajo la barra, alineado a su inicio
            axc.annotate(nom, (lo, y), xytext=(1, -11), textcoords="offset points", fontsize=7.5, color="#444444")
        else:
            axc.annotate(nom, (hi, y), xytext=(4, -3), textcoords="offset points", fontsize=7.5, color="#444444")
    axc.set_ylim(0.3, len(CANALES) + 0.7)
    axc.set_yticks([])
    axc.grid(axis="y", visible=False)
    axc.spines["left"].set_visible(False)
    axc.set_xlim(0, cmax)
    axc.set_xlabel("Costo por unidad de cambio de exposición (pb)")
    return _guardar(fig, nombre)


def todas(res, T):
    return [fig_curva_resultado(res, T), fig_confiabilidad(res), fig_tramos_retorno(res, T), fig_costos(res, T)]
