# Torneo USD/CLP · Itaú–FEN

Última actualización: 2026-11-06 17:52 (hora de Chile). Autores: Diego Ponce y Simón Canales.

Modelo para predecir la dirección del USD/CLP de la jornada siguiente (en exceso de carry) y traducirla en exposición −3/−1/0/+1/+3.

**Modelo operativo: M1** = logit con la señal de Nueva York (MXN, ZAR, BRL, DXY, −EURUSD, −S&P 500, normalizados por volatilidad) y el retorno del propio CLP; walk-forward anual con ventana expansiva y móvil promediadas; calibración de Platt; exposición con Kelly fraccional discreto (c = ¼) y costo de 2 pb por unidad de cambio.

## Estructura
- `src/config.py`: parámetros prerregistrados (13 y 20-oct-2026). No cambiarlos tras ver resultados.
- `src/datos.py`: carga de la base y tabla de modelamiento sin look-ahead (incluye una prueba automática).
- `src/modelo.py`: logit con walk-forward anual, ventanas expansiva y móvil, y calibración de Platt.
- `src/evaluacion.py`: Brier, log-loss, Clark-West, Diebold-Mariano (HLN), Pesaran-Timmermann, regla de Kelly, backtest, sensibilidad a costos, bootstrap estacionario con intervalos de confianza, Holm y Deflated Sharpe Ratio.
- `src/auditoria.py`: auditoría de la base (trampas del diccionario).
- `notebooks/01_modelo_nucleo.ipynb`: todo el análisis, en 16 secciones (0 a 15: versión, escalera M0 → M1 → M2 → M1C, tests, valor económico, robustez, ejecución realista, costos, evaluación formal frente a las referencias, perfiles de inversionista y E13, tablas y figuras del informe, decisiones).
- `notebooks/crear_notebook.py`: genera el notebook (editar aquí y regenerar).
- `run_daily.py`: señal diaria para el monitoreo en vivo (exposición de la jornada siguiente) y registro en `reports/senales_diarias.csv`.
- `src/tablero.py` y `src/tablero_plantilla.html`: tablero HTML de la mesa de dinero que genera `run_daily.py`.
- `dashboard/`: tablero interactivo en Streamlit (`streamlit run dashboard/app.py`), con 7 páginas: señal, desempeño, riesgo, base de datos, variables, registro y cómo funciona.
- `prueba.py`: corrida **única** del modelo congelado en el tramo de prueba (2024 en adelante), con el análisis prerregistrado de las secciones 3–12b del notebook y la «lectura de la convicción» que piden las bases (jornadas en ±3 y en 0). `python prueba.py --ensayo` corre lo mismo sobre la validación 2020–2023 y reproduce las cifras del informe; `python prueba.py` (solo desde el congelamiento, una vez) deja los resultados en `reports/prueba/`.
- `tests/test_run_daily.py`: verifica que `run_daily.py` reproduce exactamente el backtest.
- `reports/registro_experimentos.csv`: todas las pruebas realizadas (E01–E13), para el Deflated Sharpe Ratio.
- `src/figuras.py`: figuras del informe (se guardan en `reports/figuras/`).
- `informe/`: el informe en LaTeX (un solo `.tex`), sus figuras y el PDF compilado.
- `CHANGELOG.md`: bitácora de cambios con fecha y hora.

## Datos
La base es del Laboratorio Bloomberg FEN y está sujeta a los términos de uso de Bloomberg, por lo que **no se incluye en este repositorio** (`.gitignore` la excluye). Para reproducir los resultados, pide la base al laboratorio y guárdala como **`data/base_usdclp_actualizada.xlsx`** (nombre exacto). El código está bajo licencia MIT (`LICENSE`); la base no.

**Nombre exacto, sin búsqueda.** El código lee solo ese archivo (`src/config.py`, `NOMBRE_BASE`). Si no está, se detiene con un mensaje: nunca usa otra versión en silencio. Cada base nueva que envía el laboratorio se guarda con ese mismo nombre, **reemplazando** la anterior (respalda la antigua fuera de la carpeta del proyecto si quieres conservarla). Para usar otro archivo sin renombrarlo, define la variable de entorno `TORNEO_BASE` con su ruta completa (en PowerShell: `$env:TORNEO_BASE="C:\ruta\base.xlsx"`).

**Trazabilidad.** Cada señal registra el archivo leído (`archivo_base`), su huella SHA-256 (`huella_base`, cambia con cada envío) y la huella de los datos que usa el modelo hasta la fecha de decisión (`huella_datos`: USD/CLP, cámara, TPM, Fed Funds y las seis series de la señal NY). Si una base nueva deja igual la `huella_datos` de un día, la señal de ese día no puede cambiar; si cambia, hubo una revisión de datos que afecta al modelo. Ejemplo: la base del 6-nov-2026 da la misma huella de datos que la del 6-oct para todo 2004–2023.

## Cómo correrlo (VS Code)
1. Guarda el Excel del laboratorio como `data/base_usdclp_actualizada.xlsx`.
2. Instala las dependencias: `pip install -r requirements.txt`
3. Abre `notebooks/01_modelo_nucleo.ipynb`, elige el kernel de Python y usa «Run All» (tarda 1–2 minutos por el bootstrap).

## Señal diaria (monitoreo en vivo, 13-nov a 1-dic)
1. El laboratorio envía la base actualizada cada par de días: guárdala como `data/base_usdclp_actualizada.xlsx`, reemplazando la anterior.
2. `python run_daily.py --pendientes` → calcula y registra en `reports/senales_diarias.csv` la exposición (−3/−1/0/+1/+3) de **cada** jornada nueva desde la última registrada, cada una con información hasta su propio cierre. `python run_daily.py` (sin opciones) calcula solo la última jornada de la base.
3. Abre `reports/tablero.html` (doble clic; funciona sin internet): señal del día y por qué la regla eligió esa exposición, resultado del seguimiento frente a las referencias, riesgo, historial (contrastado con lo registrado), estado de cada serie y huella del código. Cada día queda además una copia en `reports/tableros/`.
4. Si avisa que una serie no tiene cierre del día, la señal usa el último disponible: revisar antes de operar. Si avisa «base atrasada», la base no trae los días recientes: pedir la actualización al laboratorio. Si se pide una fecha posterior al último cierre de la base, el script se detiene.
5. El modelo no se modifica durante el monitoreo: lo único que se adapta solo son las volatilidades de 60 y 250 días y la regla de Kelly (parte del modelo congelado). Los coeficientes del año y la calibración se estiman con datos anteriores al 1 de enero.

**Tablero interactivo:** `streamlit run dashboard/app.py` abre en el navegador una app para explorar la señal, el desempeño frente a las referencias, el riesgo y la base. No registra señales: la señal oficial se emite con `run_daily.py`.

Para probarlo antes del congelamiento: `python run_daily.py --fecha 2023-12-28 --desde 2023-11-13 --no-registrar` (simula un monitoreo del 13-nov al 28-dic de 2023).

**Congelamiento: 6-nov-2026** (adelantado desde el 8-nov). Hasta ese día todo el código cortaba los datos el 2023-12-31. El commit etiquetado `v0.9-congelado` es la versión con la que se corrió, una sola vez, el tramo de prueba (`prueba.py`); el modelo no cambia después.
