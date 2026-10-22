# Torneo USD/CLP · Itaú–FEN

Última actualización: 2026-10-21 21:54 (hora de Chile). Autores: Diego Ponce y Simón Canales.

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
- `tests/test_run_daily.py`: verifica que `run_daily.py` reproduce exactamente el backtest.
- `reports/registro_experimentos.csv`: todas las pruebas realizadas (E01–E13), para el Deflated Sharpe Ratio.
- `src/figuras.py`: figuras del informe (se guardan en `reports/figuras/`).
- `informe/`: el informe en LaTeX (un solo `.tex`), sus figuras y el PDF compilado.
- `CHANGELOG.md`: bitácora de cambios con fecha y hora.

## Datos
La base (`data/base_usdclp*.xlsx`) es del Laboratorio Bloomberg FEN y está sujeta a los términos de uso de Bloomberg, por lo que **no se incluye en este repositorio** (`.gitignore` la excluye). Para reproducir los resultados, pide la base al laboratorio y déjala en `data/`. El código está bajo licencia MIT (`LICENSE`); la base no.

## Cómo correrlo (VS Code)
1. Deja el Excel del laboratorio (`base_usdclp*.xlsx`) en `data/` o en esta carpeta.
2. Instala las dependencias: `pip install -r requirements.txt`
3. Abre `notebooks/01_modelo_nucleo.ipynb`, elige el kernel de Python y usa «Run All» (tarda 1–2 minutos por el bootstrap).

## Señal diaria (monitoreo en vivo, 13-nov a 1-dic)
1. Actualiza el Excel de la base con los cierres del día (después de las ~19:00 hora de Chile, cuando cerró Nueva York).
2. `python run_daily.py` → imprime la probabilidad y la exposición (−3/−1/0/+1/+3) para la jornada siguiente y la anota en `reports/senales_diarias.csv`.
3. Si avisa que una serie no tiene cierre del día, la señal usa el último disponible: revisar antes de operar.

Para probarlo antes del congelamiento: `python run_daily.py --fecha 2023-12-28 --no-registrar`.

Mientras el modelo no esté congelado (8-nov), todo el código corta los datos el 2023-12-31. **No mirar el tramo 2024–2026 antes de la corrida única.**
