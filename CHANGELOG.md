# Bitácora de actualizaciones

Cada cambio que Claude hace en esta carpeta queda anotado aquí, con fecha y hora de Chile.
Para verificar que tienes la última versión, compara la fecha de arriba con la que aparece
al inicio de cada archivo de `src/` y en la sección 0 del notebook.

| Fecha y hora (Chile) | Archivo | Cambio |
|---|---|---|
| 2026-10-21 22:22 | Informe_Torneo_USDCLP.tex (Desktop e informe/) | Auditoría, bloque 3: lo que se vio del tramo de prueba (3.4); DSR con N = 48, 100 y 200 y lugar entre las 48 variantes; 7.2 reescrita con la evidencia de huecos y tamaño de apuestas; calibración con ambos lados; H2 no rechazada; supuestos de costo, apertura y Clark-West; carry 2,5 %; nota de la Tabla 9; Lustig y Verdelhan (2007) y Kelly Jr.; Apéndice B con 16 secciones |
| 2026-10-21 22:11 | Informe_Torneo_USDCLP.tex (Desktop e informe/), figura 3 | Auditoría, bloque 2: la información es la del cierre de Nueva York; resumen e introducción con ambas ejecuciones; la validación se declara no confirmatoria; Tabla 10 que suma (carry corregido); Tabla 12 con ejecución a la apertura (E13); costo de 2 pb rotulado como supuesto; E13 en el Apéndice A |
| 2026-10-21 21:54 | src/config.py, src/evaluacion.py, notebook (sección 12b), registro E13 | E13 prerregistrado para el 8-nov: perfiles (torneo, institucional, minorista) × ejecución (cierre a cierre y apertura a apertura) |
| 2026-10-21 21:54 | src/datos.py | Corrección: la ejecución apertura→apertura paga el carry de t+1 a t+2 (estaba desfasado un día) y excluye huecos de t+1 a t+2. 2011–19: −13,4 % (antes −14,5 %); 2020–23: 10,6 % (antes 10,7 %) |
| 2026-10-21 21:54 | src/evaluacion.py, src/figuras.py, notebook (secciones 8 y 10) | Descomposición por tramos que suma (costos cobrados una vez) y Figura 3 en bruto; DSR con N = 48, 100 y 200 |
| 2026-10-21 21:54 | registro E05/E09, reports/AUDITORIA_DATOS.md, README.md, .gitignore, data/README.md, comentarios en modelo.py y run_daily.py | Auditoría externa del 21-oct: registro al día (E09 con N = 48), aclaración de lo que se vio del tramo de prueba, la base de Bloomberg queda fuera del repositorio |
| 2026-10-21 21:18 | Informe (Desktop e informe/) | Resumen (abstract) redactado; falta la frase del tramo de prueba (8-nov) |
| 2026-10-21 17:43 | .gitignore, LICENSE, README.md, informe/ | Preparación del repositorio: archivos a ignorar, licencia MIT (solo código), informe en un solo .tex con figuras; prueba de clon limpio OK (notebook sin errores, test de run_daily OK) |
| 2026-10-21 17:29 | src/figuras.py, notebook (sección 14) | Figura de costos: retorno neto vs costo, costo de equilibrio y canales de inversión |
| 2026-10-21 17:29 | Informe_Torneo_USDCLP.tex (Desktop) | La figura de costos reemplaza las tablas de sensibilidad y de equilibrio en la sección 7 |
| 2026-10-21 17:21 | Informe_Torneo_USDCLP.tex (Desktop) | Figuras de confiabilidad, curva de resultado y tramos del retorno en las secciones 6.1 y 7; imágenes en figuras_torneo/ junto al .tex |
| 2026-10-21 17:21 | src/figuras.py, notebook (sección 14) | Figuras del informe en reports/figuras/ (PDF): curva de resultado con exposición, confiabilidad, tramos del retorno; decisiones pasan a sección 15 |
| 2026-10-21 16:48 | Informe_Torneo_USDCLP.tex (Desktop) | Apéndice A (registro E01–E12 y conteo de ensayos) y B (reproducibilidad, origen de cada tabla, señal diaria); Tabla 3 corregida |
| 2026-10-21 16:46 | notebook (sección 13) | Tablas del informe que faltaban (descriptivas, valor económico 2011–2019, resultado anual con comprar siempre); decisiones pasan a sección 14 |
| 2026-10-21 16:27 | run_daily.py, tests/test_run_daily.py | Señal diaria con el modelo congelado y registro en reports/senales_diarias.csv; prueba de que reproduce el backtest (5 fechas, coincidencia exacta) |
| 2026-10-21 16:27 | src/config.py | FECHA_CONGELAMIENTO = 2026-11-08: antes de esa fecha run_daily.py no acepta fechas posteriores a 2023 |
| 2026-10-21 16:27 | README.md | Instrucciones de la señal diaria |
| 2026-10-21 16:20 | Informe_Torneo_USDCLP.tex (Desktop) | Sección 7: perfiles institucional y minorista (Tabla 15); banca privada en la tabla de canales; síntesis actualizada |
| 2026-10-21 16:19 | src/config.py, src/datos.py, src/evaluacion.py | E12: perfiles institucional (0,5 CLP) y retail (2 CLP); costos diarios en pesos / tipo de cambio; función `perfiles_inversionista` |
| 2026-10-21 16:19 | notebook (sección 12) | Perfiles de inversionista; decisiones pasan a sección 13 |
| 2026-10-20 19:15 | Informe_Torneo_USDCLP.tex (Desktop) | Sección 7 (robustez) redactada: Kelly, estabilidad anual, ejecución realista, costos minoristas y equilibrio; 3 fuentes web |
| 2026-10-20 19:15 | notebook (sección 9), registro E08 | CORRECCIÓN: 1 CLP de spread ≈ 10 pb (no 1 pb). Canales retail recalculados; escenario CFD con 4 pb |
| 2026-10-20 19:15 | registro E11 | Diagnóstico por año: 2011–2012 concentran el resultado de 2011–2019 |
| 2026-10-20 19:08 | src/evaluacion.py, notebook (sección 10) | Intervalo de confianza al 95 % del bootstrap para la diferencia de retorno |
| 2026-10-20 19:08 | Informe_Torneo_USDCLP.tex (Desktop) | Sección 6.1 (resultados de validación): coeficientes, pronóstico, tests, valor económico, evaluación formal y DSR |
| 2026-10-20 18:59 | Informe_Torneo_USDCLP.tex (Desktop) | Sección 5 (diseño de la evaluación) redactada: pronóstico, valor económico vs referencias, DSR (N=48), potencia, disciplina |
| 2026-10-20 18:57 | Informe_Torneo_USDCLP.tex (Desktop) | Sección 4 (metodología) redactada: objetivo, modelos anidados y escalera, walk-forward, Platt, regla de Kelly derivada, PnL |
| 2026-10-20 18:53 | Informe_Torneo_USDCLP.tex (Desktop) | Sección 3 (datos) redactada: muestra y tramos, carry, series y horarios, auditoría, descriptivas, hecho estilizado |
| 2026-10-20 18:48 | Informe_Torneo_USDCLP.tex (Desktop) | Términos en inglés: nonsynchronous trading, order flow, directional accuracy, backtest overfitting, Deflated Sharpe Ratio |
| 2026-10-20 18:46 | Informe_Torneo_USDCLP.tex (Desktop) | «paseo aleatorio» → *random walk* (términos técnicos en su idioma original) |
| 2026-10-20 18:43 | Informe_Torneo_USDCLP.tex (Desktop) | Sección 2 redactada (7 subsecciones + síntesis); referencias De Gregorio, Jaramillo-Selaive y González Cañón corregidas; bibliografía en castellano |
| 2026-10-20 18:38 | Informe_Torneo_USDCLP.tex (Desktop) | Se elimina la portada aparte; la primera página es título, autores y resumen |
| 2026-10-20 18:36 | Informe_Torneo_USDCLP.tex (Desktop) | Sección 1: H1 nombra MXN, ZAR y BRL; énfasis en rentabilidad; aporte reescrito (sin «primer estudio») |
| 2026-10-20 18:23 | Informe_Torneo_USDCLP.tex (Desktop) | Sección 1 redactada: motivación, pregunta de investigación, H1–H3, método, hallazgos no hipotetizados, aporte y organización |
| 2026-10-20 18:12 | (fuera de esta carpeta) | Informe oficial pasa a un solo archivo: Desktop\Carpeta Finanzas Corporativas\Informe_Torneo_USDCLP.tex. `informe/` queda como respaldo |
| 2026-10-20 18:10 | informe/main.tex | Autores: Diego Ponce y Simón Canales |
| 2026-10-20 18:05 | informe/main.tex | Tipografía Times (newtxtext + newtxmath), portada, página de resumen, títulos en versalitas, encabezado de working paper y saltos de página |
| 2026-10-20 18:00 | informe/ | Plantilla LaTeX del informe: `main.tex`, 9 secciones + apéndice, `referencias.bib` (29 entradas), estilo `apalike-es.bst` |
| 2026-10-20 18:00 | (varios) | Corrección de sellos: entre E08 y E10 se habían anotado horas adelantadas 3–8 min; se reemplazaron por la hora real |
| 2026-10-20 17:57 | src/datos.py | Variable `cobre` (COMEX con limpieza de rolls vía LME); incluida en la prueba anti look-ahead |
| 2026-10-20 17:57 | notebook (sección 11) | Candidato M1C: descartado (CW p = 0,55). Sharpe deflactado ahora con N = 48. Decisiones pasan a sección 12 |
| 2026-10-20 17:52 | src/config.py | E10: prerregistro del candidato M1C (M1 + cobre COMEX) y regla de limpieza de rolls |
| 2026-10-20 17:45 | src/evaluacion.py | E09: bootstrap estacionario, comparación con referencias (DM económico + bootstrap), Holm y Sharpe deflactado |
| 2026-10-20 17:45 | notebook (sección 10) | Evaluación formal contra las referencias; decisiones pasan a sección 11 |
| 2026-10-20 17:39 | src/evaluacion.py | Nueva función `pesaran_timmermann` (test de acierto direccional) |
| 2026-10-20 17:39 | notebook (sección 4) | Tabla de DA con test de Pesaran-Timmermann para M1 y M2 |
| 2026-10-20 17:21 | src/evaluacion.py | E08: nuevas funciones `sensibilidad_costos` y `costo_equilibrio` |
| 2026-10-20 17:21 | notebook (sección 9) | Sensibilidad a costos retail y punto de equilibrio; decisiones pasan a sección 10 |
| 2026-10-20 17:21 | reports/ | `sensibilidad_costos.csv`, `breakeven_costos.csv`; E08 en el registro |
| 2026-10-20 17:15 (hora de Chile) | src/*.py | Sello de versión en el encabezado de cada módulo |
| 2026-10-20 17:15 (hora de Chile) | notebooks/01_modelo_nucleo.ipynb | Sección 0 (versión y fecha de cada archivo en tu PC) y sección 9 (ejecución realista) |
| 2026-10-20 17:12 | src/datos.py | Retornos con ejecución realista: rex_ap_ap, rex_ap_ci, rex_noche |
| 2026-10-20 17:12 | reports/registro_experimentos.csv | Experimento E07 (ejecución realista) |
| 2026-10-20 17:01 | (toda la carpeta) | Copia inicial del proyecto a este PC |
| 2026-10-13 | src/evaluacion.py | Regla oficial: Kelly discreto por utilidad |
| 2026-10-13 | src/*.py, notebook | Versión inicial: datos, modelo, calibración, evaluación |
