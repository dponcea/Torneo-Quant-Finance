"""Parámetros prerregistrados del modelo (13-oct-2026).

No modificar después de ver resultados: cualquier cambio debe anotarse en
el registro de experimentos (reports/registro_experimentos.csv).
"""
# Última actualización: 2026-10-25 20:16 (hora de Chile) — fechas del monitoreo (INICIO_MONITOREO, FIN_MONITOREO) para el tablero
from pathlib import Path

# Rutas (relativas a la raíz del proyecto)
RAIZ = Path(__file__).resolve().parents[1]
def _buscar_base():
    """Busca el Excel del laboratorio (base_usdclp*.xlsx) en data/ o en la raíz del proyecto."""
    for carpeta in (RAIZ / "data", RAIZ):
        encontrados = sorted(carpeta.glob("base_usdclp*.xlsx"))
        if encontrados:
            return encontrados[0]
    return RAIZ / "data" / "base_usdclp.xlsx"


ARCHIVO_BASE = _buscar_base()

# Tramos de la muestra
INICIO = "2004-01-01"          # antes: calendario con feriados rancios y OHLC sin contenido
INICIO_OOS = 2010              # primer año con predicciones fuera de muestra (para Platt)
VALIDACION = (2020, 2023)      # tramo de validación
FIN_EXPLORACION = "2023-12-31" # NO usar datos posteriores hasta congelar el modelo (8-nov)
FECHA_CONGELAMIENTO = "2026-11-08"  # run_daily.py no acepta fechas > FIN_EXPLORACION antes de este día
INICIO_MONITOREO = "2026-11-13"    # primer día del monitoreo en vivo (el tablero mide el seguimiento desde aquí)
FIN_MONITOREO = "2026-12-01"       # último día del monitoreo en vivo

# Variables
VOL_VENTANA = 250              # días para normalizar retornos por su volatilidad pasada
PARES_NY = {                   # ticker: signo (+1 si sube cuando el dólar se fortalece)
    "USDMXN Curncy": +1,
    "USDZAR Curncy": +1,
    "USDBRL Curncy": +1,
    "DXY Curncy": +1,
    "EURUSD Curncy": -1,
    "SPX Index": -1,
}
MAX_DIAS_ENTRE_JORNADAS = 6    # retornos que cruzan huecos mayores se excluyen

# Modelos anidados
MODELOS = {
    "M0": [],
    "M1": ["ny", "r_clp"],
    "M2": ["ny", "r_clp", "carry", "riesgo", "carry_x_riesgo"],
    # E10, prerregistrado el 20-oct-2026 17:52, ANTES de correrlo. Único candidato nuevo de la escalera.
    # Entra al modelo final solo si supera a M1 con Clark-West (p < 0,05) en validación 2020-2023.
    "M1C": ["ny", "r_clp", "cobre"],
}
# Cobre: retorno de HG1 (COMEX, settlement 13:00 ET, posterior al cierre onshore del CLP ~13:00-13:30).
# Días de cambio de contrato: si |r_HG - r_LME| > 3 desv. (ventana 250, pasada), se usa r_LME ese día.
COBRE_PRINCIPAL = "HG1 Comdty"
COBRE_LIMPIEZA = "LMCADS03 Comdty"
COBRE_UMBRAL_ROLL = 3.0
VENTANA_MOVIL = 1250           # jornadas (~5 años)

# Regla de decisión (Kelly fraccional)
KELLY_C = 0.25                 # regla principal
KELLY_C_ROBUSTEZ = 0.20        # análisis aparte
VENTANA_RIESGO = 60            # días para E|r| y sigma
CORTES = (0.5, 2.0)            # |k*|<0.5 -> 0 ; <2 -> 1 ; >=2 -> 3

# SUPUESTO de costo hasta que el laboratorio lo informe (pregunta 1 a David; las bases no lo fijan)
COSTO_POR_UNIDAD = 2e-4        # 2 pb por unidad de cambio de posición (supuesto prerregistrado, no una regla del torneo)

# E12 (21-oct-2026, prerregistrado para la corrida del 8-nov): perfiles de inversionista.
# Costo en pesos por dólar comprado o vendido (cada unidad de cambio de exposición), según la
# experiencia profesional de uno de los autores en carteras discrecionales de alto patrimonio.
# El costo diario en fracción es pesos / tipo de cambio del día. Cada perfil usa la regla de
# Kelly con su propio costo; las posiciones con el costo del torneo se reportan como comparación.
PERFILES_COSTO_CLP = {
    "institucional": 0.5,
    "retail": 2.0,
}

# E13 (21-oct-2026, PRERREGISTRADO para la corrida del 8-nov; cambio de reporte, no de modelo).
# En el tramo de prueba se reporta cada perfil de E12 (y el torneo con 2 pb) con las dos ejecuciones:
# la convención del torneo (cierre a cierre) y la ejecución disponible para quien decide después del
# cierre de Nueva York (apertura de t+1 a apertura de t+2, con el carry de t+1 a t+2).
# Las posiciones son las mismas en ambas ejecuciones: solo cambia el retorno con que se liquidan.
# Función: evaluacion.perfiles_por_ejecucion. No se elige nada a partir de este reporte.
EJECUCIONES_E13 = {
    "cierre a cierre (torneo)": "rex_sig",
    "apertura a apertura": "rex_ap_ap",
}
