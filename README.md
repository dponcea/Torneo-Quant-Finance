# Torneo USD/CLP · Itaú–FEN

Última actualización: 2026-11-12 (hora de Chile). Autores: Diego Ponce y Simón Canales.

Modelo para predecir la dirección del USD/CLP de la jornada siguiente (en exceso de carry) y traducirla en exposición −3/−1/0/+1/+3.

**Modelo operativo: M1** = logit con la señal de Nueva York (MXN, ZAR, BRL, DXY, −EURUSD, −S&P 500, normalizados por volatilidad) y el retorno del propio CLP; walk-forward anual con ventana expansiva y móvil promediadas; calibración de Platt; exposición con Kelly fraccional discreto (c = ¼) y costo de 2 pb por unidad de cambio.

## Resultados

| Tramo | Retorno neto anual | Sharpe | Pérdida máx. | Clark-West M1 vs M0 |
|---|---|---|---|---|
| Validación 2020–2023 (elección del modelo) | 12,1 % | 0,92 | −10 % | p = 0,029 |
| **Prueba 2024–2026** (corrida única, 6-nov-2026) | **−5,1 %** | **−0,54** | −21 % | p = 0,52 |

Netos de carry y de 2 pb por unidad de cambio de exposición, con la convención del torneo (cierre a cierre). En la prueba, comprar dólares siempre ganó 2,7 % anual.

| Estadísticas de trading | Validación 2020–2023 | Prueba 2024–2026 |
|---|---|---|
| Jornadas | 1.010 | 716 |
| Volatilidad anual | 13,1 % | 9,6 % |
| Acierto en días con posición | 55 % | 48 % |
| Operaciones (cambios de exposición) | 337 (84 por año) | 207 (73 por año) |
| Unidades transadas | 452 (113 por año) | 280 (99 por año) |
| Tiempo en el mercado | 46 % de las jornadas | 46 % |
| Duración media de una posición | 3,5 días | 4,2 días |
| Días comprado / vendido | 231 / 231 | 115 / 215 |

La tabla completa, con la curva de resultados y la exposición diaria, está en la sección 6 y 6b del notebook; la de la prueba, en `reports/prueba/resultados.txt`.

**Lectura.** La señal de Nueva York anticipó la dirección del peso entre 2004 y 2023, pero se fue debilitando: su correlación con el retorno del día siguiente pasó de 0,16 (2004–2012) a 0,11 (2013–2019), 0,05 (2020–2023) y −0,02 (2024–2026). La fragilidad se registró antes de mirar la prueba (E15), y el modelo no se modificó después de verla. El detalle está en el informe (`informe/`, secciones 6.2 y 9) y en `reports/prueba/resultados.txt`.

**Materiales del laboratorio.** Las bases mencionan un «código de evaluación» y una «estructura base del programa»; el laboratorio informó que el código de evaluación no se publica, y la estructura base no la recibimos. El repositorio se construyó desde cero, con las tres referencias de las bases (comprar siempre, no operar y exposición fija 1) implementadas en `src/evaluacion.py` y `prueba.py`.

## Cómo ejecutar el proyecto (paso a paso)

Pensado para que cualquier miembro del laboratorio lo clone y lo corra sin ayuda. Requiere Python 3.11 o superior.

```bash
# 1. Clonar
git clone <URL de este repositorio>
cd Torneo-Quant-Finance

# 2. Dependencias (pandas, numpy, scipy, statsmodels, openpyxl, matplotlib, ipykernel; streamlit y plotly solo para el tablero)
pip install -r requirements.txt

# 3. Datos: la base del Laboratorio Bloomberg FEN no está en el repositorio (términos de uso de Bloomberg).
#    Guardarla con este nombre exacto; el código no lee ningún otro archivo.
#    → data/base_usdclp_actualizada.xlsx

# 4. Verificar que todo está bien instalado (compara la señal diaria con el backtest; ~30 s)
python -m pytest tests/ -q          # o: python tests/test_run_daily.py

# 5. Reproducir el backtest completo (validación 2010–2023, tablas y figuras del informe; 1–2 min por el bootstrap)
#    Abrir notebooks/01_modelo_nucleo.ipynb en VS Code o Jupyter y «Run All», o desde la terminal:
jupyter nbconvert --to notebook --execute --inplace notebooks/01_modelo_nucleo.ipynb

# 6. Reproducir las cifras de validación con el mismo script de la prueba (escribe en reports/prueba_ensayo/)
python prueba.py --ensayo

# 7. Señal del día para el monitoreo (escribe en reports/senales_diarias.csv y reports/tablero.html)
python run_daily.py --pendientes
```

`python prueba.py` sin opciones es la corrida única del tramo de prueba: ya se ejecutó el 6-nov y el script se niega a sobrescribir `reports/prueba/`. Las semillas del bootstrap y del placebo están fijas; los resultados son idénticos en cada ejecución.

## Mecanismo de ejecución

Esto es lo que el monitor del laboratorio necesita para replicar la estrategia exactamente.

- **Qué se predice.** Si el retorno del USD/CLP en exceso de carry entre el cierre local de la jornada *t* y el de *t+1* será positivo. El carry es la tasa de cámara menos la Fed Funds efectiva del día anterior, por los días corridos hasta la jornada siguiente (base 360).
- **Con qué información.** Los cierres de la jornada *t* de las trece series de la Tabla 2 del informe (USD/CLP, MXN, ZAR, BRL, DXY, EURUSD, S&P 500, tasas, volatilidad emergente, cobre), tratados como si cerraran a la misma hora, según indicó el laboratorio. Las series de Nueva York cierran en realidad 3–6 horas después que el peso; eso es el supuesto de cierre común y se discute en §7.3 y §7.6 del informe. **No se usa el dólar observado** (es el spot del día anterior).
- **Cómo se decide.** Probabilidad calibrada *p_t* del logit M1 → retorno esperado μ_t = (2p_t − 1)·E|r|₆₀ y riesgo σ_t (60 jornadas) → exposición k_t = argmax sobre {−3, −1, 0, +1, +3} de k·μ_t − k²σ_t²/(2c) − κ·|k − k_{t−1}|, con c = ¼ y κ = 2 pb. Los coeficientes del logit y la calibración de cada año calendario se estiman solo con jornadas anteriores al 1 de enero de ese año (embargo de 5 jornadas); lo único que cambia día a día son E|r|₆₀, σ_t y la volatilidad de 250 días que normaliza la señal.
- **Qué gatilla una operación.** Un cambio de k_t respecto de k_{t−1}. Si k_t = k_{t−1} no hay operación ni costo; si cambia, se compran o venden |k_t − k_{t−1}| unidades de nocional (1 unidad ≈ USD 1 millón) y se cobra κ por unidad. Una señal débil no se ejecuta cuando su ganancia esperada no cubre ese costo: el término κ|k − k_{t−1}| es el castigo a la señal.
- **A qué precio se liquida.** Convención del torneo: **al cierre local**. La exposición decidida con la información de *t* se acredita el retorno entre el cierre de *t* y el de *t+1* (`rex_sig`). Como alternativa realista para quien decide después del cierre de Nueva York, el informe reporta la misma secuencia de posiciones ejecutada **a la apertura** local de *t+1* y liquidada a la apertura de *t+2* (`rex_ap_ap`, §7.3); ambas columnas existen en la tabla de modelamiento (`src/config.py`, `EJECUCIONES_E13`).
- **Salida diaria.** `run_daily.py` escribe en `reports/senales_diarias.csv` una fila por jornada con la fecha de decisión, la señal NY, *p* bruta y calibrada (y los parámetros de Platt), μ_t y σ_t en pb, la exposición elegida, la anterior, el cambio (la operación) y la dirección («compra USD», «vende USD», «sin posición»), más las huellas de código, archivo y datos. Esa fila es la orden del día; el tablero `reports/tablero.html` muestra además la utilidad de cada k.

## Supuestos explícitos

Lo que un evaluador debería conocer antes de leer los resultados. Cada supuesto está discutido en el informe (sección entre paréntesis).

| Supuesto | Qué asumimos | Por qué, y qué pasa si no se cumple |
|---|---|---|
| **Cierre común** | Todas las series «cierran» el mismo día a la misma hora, como indican las bases y confirmó el laboratorio. | Es la principal fuente de *leakage*: la señal NY se conoce 3–6 horas después del cierre local y la convención del torneo acredita el retorno desde ese cierre. Por eso reportamos **también la ejecución a la apertura del día siguiente**, el primer precio realmente transable: 10,6 % en validación, −13,4 % en 2011–2019 (§7.3). |
| **Costo: 2 pb por unidad de cambio de exposición** | Un operador mayorista que cruza medio spread interbancario de ~40 centavos. | Las bases no fijan el costo. Reportamos además **3,5 pb** (el 0,07 % ida y vuelta que propuso el laboratorio en la segunda mentoría: 10,4 % validación, 13,1 % 2011–2019, −6,6 % prueba), **8 pb** (spread de estrés de 1,5 pesos), dos perfiles de inversionista (6–8,5 pb institucional, 25–34 pb minorista) y el **costo de equilibrio** (9–13 pb). Las conclusiones no cambian con ninguno (§7.4–7.5). |
| **Carry** | Tasa de cámara (ICP, por días corridos) menos Fed Funds efectiva rezagada un día, base 360. | Correlación 0,87 con el diferencial implícito en el NDF a un mes. Medir en exceso de carry limpia la tendencia a la depreciación nominal del peso (§3.2). |
| **Nocional** | Del orden de USD 1 millón por unidad de exposición. | Por debajo del umbral de USD 20 millones en que el spread interbancario empieza a ampliarse; no modelamos escala de costos por tamaño (§7.6). |
| **Muestra desde 2004** | Antes, el OHLC del USD/CLP no tiene contenido (máximo = mínimo todos los días). | Auditoría de la base (§3.4). |
| **Huecos de 2011–2012** | Se excluyen los retornos que cruzan más de 6 días corridos; no se rellenan. | Rellenar inventaría valores de la variable objetivo. Robustez E15: sin ese tramo el modelo decide igual el 96 % de los días. |
| **Retorno esperado simétrico** | Si el dólar sube con probabilidad *p*, la magnitud esperada es la misma hacia arriba y hacia abajo (media de \|r\| de 60 días). | Simplificación que permite el Kelly cerrado de la ecuación (5) del informe. |

## Herramientas elegidas y descartadas

| Decisión | Elegimos | Descartamos | Por qué |
|---|---|---|---|
| Familia de modelo | **Logit anidado** (M0 → M1 → M2, más M1C con cobre) | Gradient boosting (LightGBM), redes, momentum puro, cambio de régimen | Con ~250 jornadas/año y una relación débil, la varianza de estimación es el enemigo. El logit es interpretable, se calibra bien y cada modelo adicional sube la penalización por *data snooping*. Boosting y momentum se descartaron **por diseño, antes de ver resultados**. El cambio de régimen se sugirió en la segunda mentoría y queda como extensión: incorporarlo después de ver la prueba sería sobreajuste. |
| Selección de variables | **Escalera prerregistrada**: una variable entra solo si Clark-West da *p* < 0,05 en validación | Agregar todo lo que mejore el ajuste | Ni carry, ni volatilidad emergente, ni cobre superaron a M1 (*p* = 0,68 y 0,55). M1 es el modelo operativo. |
| Entrenamiento / prueba | **Walk-forward anual** con embargo de 5 jornadas; promedio de ventana expansiva (desde 2004) y móvil (1.250 jornadas) | Validación cruzada aleatoria; elegir una ventana mirando resultados | Series de tiempo: el muestreo aleatorio filtra el futuro. Promediar en vez de elegir evita una decisión más. |
| Señal | **Una sola señal diaria**: las dos ventanas se promedian antes de calibrar, con regla fija | Varios modelos cuyos resultados se suman después | La señal que se evalúa es única; la combinación está declarada de antemano. |
| Calibración | **Platt anual** con predicciones fuera de muestra de años anteriores | Sin calibrar; isotónica | El logit bruto es demasiado confiado (pendiente 0,75–0,85). Platt es monótono y estable con pocos datos. |
| Regla de exposición | **Kelly discreto por utilidad** con término de costo, *c* = ¼ | Signo con tamaño fijo; Kelly redondeado con filtro de costo (la regla prerregistrada original) | El redondeo ignoraba el riesgo: 87 % de los días en ±3 y pérdida máxima de 71 % en 2011–2019. Se reemplazó **antes** de abrir la prueba y ambas están en el registro (E04, E05). El término de costo actúa como castigo a la señal: una señal débil no se ejecuta si no cubre entrar y salir. |
| Inferencia | Clark-West, Diebold-Mariano, Pesaran-Timmermann; bootstrap estacionario pareado con Holm; **Deflated Sharpe Ratio** con *N* = 48, 100 y 200 | Solo *t*-tests; solo Sharpe | Separar calidad del pronóstico de valor económico, y corregir por los ensayos realizados. |

## Disciplina del estudio

- **Prerregistro.** Especificación, regla y diseño de la evaluación se fijaron el 13, 20 y 21 de octubre. El tramo de prueba se abrió **una sola vez**, el 6 de noviembre a las 18:05, con el código etiquetado `v0.9-congelado` (commit `74e9896`).
- **Registro de experimentos.** Los 16 análisis que miraron datos están en `reports/registro_experimentos.csv` y en el Apéndice A del informe, con la decisión que se tomó a partir de cada uno. Ese registro alimenta el Deflated Sharpe Ratio.
- **Tiempo en el mercado.** La estrategia tiene posición en ~46 % de las jornadas en validación y prueba (75 % en 2011–2019), exposición de 1 en casi todas ellas y ±3 en 2–3 % de los días. No es un modelo que gane en tres días extremos y esté fuera el resto del tiempo.
- **Coherencia interna.** Decimos que la estrategia es defensiva y lo es: en la prueba se abstuvo el 54 % de los días y perdió menos que la misma señal con tamaño fijo (−5,1 % vs −8,9 %). Decimos que la señal se agotó y lo mostramos: la correlación señal–retorno cae de 0,16 (2004–2012) a −0,02 (2024–2026).
- **Lo que vimos del tramo de prueba antes de congelar.** Solo la fecha de la última observación de cada serie (para descartar series desactualizadas) y una caída del cobre COMEX del 31-jul-2025 detectada en la auditoría. Ningún retorno ni estrategia de 2024–2026.
- **Qué esperamos del monitoreo (13-nov a 1-dic).** Con la señal agotada, un resultado cercano a cero y dominado por el azar (±2–3 puntos porcentuales en tres semanas no dicen nada). Lo que sí debería mantenerse es el perfil: posición en cerca de la mitad de las jornadas, exposición de 1 casi siempre, ±3 solo con señal extrema y baja volatilidad reciente.

## Qué haríamos distinto (extensiones)

1. **Regla de apagado prerregistrada**: suspender la estrategia cuando la capacidad predictiva en una ventana reciente cae bajo un umbral. Las señales estaban: la correlación ya era 0,05 en 2020–2023.
2. **Modelo de cambio de régimen** (cadena de Markov con 2–3 estados) estimado antes del modelo direccional, y un **PCA** de las series de la base para interpretar factores (dólar global, tasas, risk-on/off), como sugirió la segunda mentoría. Nuestra señal NY es, de hecho, una versión manual del primer componente de las monedas emergentes y el dólar.
3. **Datos intradía a hora fija**, para separar la información que realmente llega después del cierre local de la que solo lo aparenta.
4. **Mercado offshore de NDF**, como lugar de ejecución para quien decide tras el cierre de Nueva York y como posible explicación de que la información se incorpore antes de la apertura.

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
- `reports/registro_experimentos.csv`: todas las pruebas realizadas (E01–E16), para el Deflated Sharpe Ratio.
- `src/figuras.py`: figuras del informe (se guardan en `reports/figuras/`).
- `informe/`: el informe en LaTeX (un solo `.tex`), sus figuras y el PDF compilado.
- `presentacion/`: láminas para la final del 2 de diciembre (`Presentacion_Torneo_USDCLP.tex`) y guía de presentación.
- `CHANGELOG.md`: bitácora de cambios con fecha y hora.

## Datos
La base es del Laboratorio Bloomberg FEN y está sujeta a los términos de uso de Bloomberg, por lo que **no se incluye en este repositorio** (`.gitignore` la excluye). Para reproducir los resultados, pide la base al laboratorio y guárdala como **`data/base_usdclp_actualizada.xlsx`** (nombre exacto). El código está bajo licencia MIT (`LICENSE`); la base no.

**Nombre exacto, sin búsqueda.** El código lee solo ese archivo (`src/config.py`, `NOMBRE_BASE`). Si no está, se detiene con un mensaje: nunca usa otra versión en silencio. Cada base nueva que envía el laboratorio se guarda con ese mismo nombre, **reemplazando** la anterior (respalda la antigua fuera de la carpeta del proyecto si quieres conservarla). Para usar otro archivo sin renombrarlo, define la variable de entorno `TORNEO_BASE` con su ruta completa (en PowerShell: `$env:TORNEO_BASE="C:\ruta\base.xlsx"`).

**Trazabilidad.** Cada señal registra el archivo leído (`archivo_base`), su huella SHA-256 (`huella_base`, cambia con cada envío) y la huella de los datos que usa el modelo hasta la fecha de decisión (`huella_datos`: USD/CLP, cámara, TPM, Fed Funds y las seis series de la señal NY). Si una base nueva deja igual la `huella_datos` de un día, la señal de ese día no puede cambiar; si cambia, hubo una revisión de datos que afecta al modelo. Ejemplo: la base del 6-nov-2026 da la misma huella de datos que la del 6-oct para todo 2004–2023.

## Señal diaria (monitoreo en vivo, 13-nov a 1-dic)
1. El laboratorio envía la base actualizada cada par de días: guárdala como `data/base_usdclp_actualizada.xlsx`, reemplazando la anterior.
2. `python run_daily.py --pendientes` → calcula y registra en `reports/senales_diarias.csv` la exposición (−3/−1/0/+1/+3) de **cada** jornada nueva desde la última registrada, cada una con información hasta su propio cierre. `python run_daily.py` (sin opciones) calcula solo la última jornada de la base.
3. Abre `reports/tablero.html` (doble clic; funciona sin internet): señal del día y por qué la regla eligió esa exposición, resultado del seguimiento frente a las referencias, riesgo, historial (contrastado con lo registrado), estado de cada serie y huella del código. Cada día queda además una copia en `reports/tableros/`.
4. Si avisa que una serie no tiene cierre del día, la señal usa el último disponible: revisar antes de operar. Si avisa «base atrasada», la base no trae los días recientes: pedir la actualización al laboratorio. Si se pide una fecha posterior al último cierre de la base, el script se detiene.
5. El modelo no se modifica durante el monitoreo: lo único que se adapta solo son las volatilidades de 60 y 250 días y la regla de Kelly (parte del modelo congelado). Los coeficientes del año y la calibración se estiman con datos anteriores al 1 de enero.

**Tablero interactivo:** `streamlit run dashboard/app.py` abre en el navegador una app para explorar la señal, el desempeño frente a las referencias, el riesgo y la base. No registra señales: la señal oficial se emite con `run_daily.py`.

Para probarlo antes del congelamiento: `python run_daily.py --fecha 2023-12-28 --desde 2023-11-13 --no-registrar` (simula un monitoreo del 13-nov al 28-dic de 2023).

**Congelamiento: 6-nov-2026** (adelantado desde el 8-nov). Hasta ese día todo el código cortaba los datos el 2023-12-31. El commit etiquetado `v0.9-congelado` es la versión con la que se corrió, una sola vez, el tramo de prueba (`prueba.py`); el modelo no cambia después.
