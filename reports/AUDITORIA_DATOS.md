# Auditoría de datos · Torneo USD/CLP (Fase 2)

Fecha: 13-oct-2026. Script: `src/auditoria.py`. Todos los análisis estadísticos (correlaciones, retornos, carry, prueba de factibilidad) usan solo datos hasta 2023-12-31.

**Qué se vio del tramo de prueba (aclaración del 21-oct-2026, tras una auditoría externa):** al revisar la cobertura de la base el 13-oct se miraron dos cosas posteriores a 2023, ambas de metadatos y no de retornos del USD/CLP: (1) la fecha de la última observación de cada serie (filas «Series rancias»), necesaria para descartar las series que la base ya no actualiza; (2) la caída de −24,9 % del cobre COMEX (HG1) del 31-jul-2025 por la prima arancelaria de EE. UU. (fila «Cobre COMEX»). El candidato M1C con cobre (E10) se propuso después, el 20-oct; se descartó por la regla de la escalera, así que ese conocimiento no entró al modelo final. El rendimiento de ninguna estrategia ni el retorno del USD/CLP de 2024–2026 se calcularon.

**Corrección del 6-nov-2026:** las filas «Cámara (ICP)» y «SOFR vs Fed Funds» se calculaban con toda la muestra (tasas de 2024–2026; no retornos ni estrategias). `src/auditoria.py` ahora las recorta a 2023 como el resto, y las cifras de esas filas son las del recorte (antes: −0,01 pp, 12,4 % vs 4,8 %, −0,2 pb y p95 9 pb). Ninguna decisión cambia.

## Base actualizada del 6-nov-2026

El laboratorio envió `base_usdclp_actualizada.xlsx` el 6-nov, después de la mentoría 1. Se revisó **solo su estructura**, sin calcular retornos posteriores a 2023:

- Mismas hojas (`datos`, `diccionario`), mismas 76 columnas en el mismo orden y diccionario idéntico. Agrega 31 filas (7-oct a 6-nov-2026).
- **Hasta 2023-12-31 no cambia ninguna celda.** La huella de los datos que usa el modelo hasta el 29-dic-2023 es la misma con ambas bases (`d6ae3102ed`), y el notebook completo reproduce todas las cifras de validación.
- Revisiones: 8 celdas en dos fechas (30-sep y 6-oct-2026), todas en series que el modelo no usa (flujos del BCCh, desempleo e Imacec).
- Los insumos del modelo (USD/CLP, las seis series de la señal NY, cámara, TPM y Fed Funds) llegan hasta el 5-6 de noviembre. Único día hábil sin USD/CLP: 12-oct (feriado en Chile).
- Desde esta fecha el código lee la base por su **nombre exacto** (`data/base_usdclp_actualizada.xlsx`): antes tomaba el primer `base_usdclp*.xlsx` en orden alfabético, que con dos versiones en la carpeta era la antigua.

## Hallazgo principal

La única señal predictiva clara son los movimientos de mercados que cierran después del USD/CLP onshore. Una señal compuesta (MXN, ZAR, BRL, DXY, EUR invertido y S&P 500 invertido, del día t, normalizados por su volatilidad pasada) tiene correlación positiva con el retorno del USD/CLP de t+1 en todos los años de 2004 a 2023:

- 0,14 en promedio en 2004–2019;
- 0,05 en 2020–2023, una caída clara.

Toda la señal vive en el tramo nocturno, del cierre de t a la apertura de t+1 (correlación 0,21 en 2004–2019); del tramo apertura→cierre de t+1 no explica nada (−0,01). Por eso es decisivo cómo calcula el retorno el evaluador:

- **cierre a cierre:** la señal vale;
- **ejecución a la apertura de t+1:** la señal desaparece.

**Es la primera pregunta para el laboratorio.**

Prueba rápida de factibilidad, con costo supuesto de 2 pb por unidad de cambio de posición y umbral fijado con datos 2004–2015:

| Tramo | Regla | Retorno anual | Sharpe |
|---|---|---|---|
| 2016–2019 | Siempre ±1 según signo | 9,0 % | 0,89 |
| 2020–2023 | Siempre ±1 según signo | 10,4 % | 0,67 |
| 2016–2019 | Comprar siempre | −0,3 % | −0,03 |
| 2020–2023 | Comprar siempre | 0,4 % | 0,02 |

Es una prueba exploratoria, no el modelo. Los costos reales son desconocidos.

## Trampas del diccionario

| Trampa | Resultado | Decisión |
|---|---|---|
| OHLC del USD/CLP | Hasta 2003, 100 % de los días con rango cero; desde 2004, entre 0 % y 3 % | Usar OHLC solo desde 2004 |
| Feriados | Hasta 2003 aparecen todos los días hábiles con precio repetido; desde 2004 quedan 13 días rancios | Calendario desde 2004 y eliminar los días con cierre repetido y rango cero |
| Huecos 2011–2012 | 2011 tiene 229 jornadas y 2012 solo 140 (faltan 121 días hábiles). Saltos de más de 6 días corridos: 15→30-nov-2011, 30-nov→13-dic-2011, 9-feb→5-mar-2012 (25 días) y 10 más, de 7 a 11 días, entre marzo y octubre de 2012 | Marcar los retornos que cruzan huecos. Opción: rellenar con el dólar observado de t+1 (≈ spot de t) |
| Dólar observado | corr(Δobs_t, Δspot_t−1) = 0,75 frente a 0,07 con Δspot_t | El observado de t es el spot de t−1. No sirve para definir retornos ni como variable nueva |
| Cámara (ICP) | Dividiendo por días corridos ≈ TPM (diferencia −0,02 pp). Sin dividir, el lunes da 11,9 % frente a 4,7 % del martes | Tasa overnight = (ICP_t/ICP_{t−1})^(1/días) − 1, anualizada base 360 |
| CHON vs TPM | CHON 3,5 % (real) + UF 3,55 % ≈ TPM 6,5 % (nominal) | No empalmar; el carry usa cámara desde 2002 |
| SOFR vs Fed Funds | Diferencia media −0,9 pb (p95: 8 pb) | Usar Fed Funds rezagado 1 día en toda la muestra |
| Flujos BCCh | Series antiguas y nuevas con correlación de nivel 0,998. El flujo correlaciona con el retorno del mismo día (−0,34), no con el siguiente (−0,02) | Empalme posible, pero los flujos **reaccionan** al precio, no lo predicen. Prioridad baja |
| Macro | La fecha de publicación llega unas 5 semanas después del mes de referencia | Usar solo desde `FECHA_RELEASE`. Poco útil a diario |
| BRL | Sin saltos de unidad en los retornos; viene re-escalado | Usar desde 2004 |
| Cobre COMEX (HG1) | Caída de −24,9 % el 31-jul-2025 (prima arancelaria de EE. UU.); HG1/LME hasta 1,10 | Preferir LME para fundamentos; HG1 tiene distorsión arancelaria |
| Series rancias | LIBOR (hasta 2024-09), IPSA (2026-08), BTP 5 años (2026-05), BTP 10 años (2026-09), CNY y SHCOMP (2026-09-30) | Excluirlas del modelo |

## Carry construido

- i_CLP = cámara overnight del ICP; i_USD = Fed Funds rezagado 1 día.
- Carry de t a t+1 = (días corridos / 360) · (i_CLP − i_USD).
- Correlación con el diferencial implícito del NDF a 1 mes: 0,87 (basis medio −0,17 pp).
- Costo medio para un largo en USD: 2,6 % anual, frente a una volatilidad diaria de 74 pb.
- El signo del retorno y el del retorno en exceso difieren solo en el 1,4 % de los días.

## Preguntas para el laboratorio, por prioridad

1. **¿El retorno se mide de cierre a cierre, de cierre a apertura o con precio promedio?** Esto decide si existe la señal principal.
2. ¿Qué costo se cobra por unidad de cambio de posición?
3. ¿Qué carry usa el evaluador: cámara − Fed Funds o el implícito del NDF?
4. ¿Cómo se tratan los huecos de 2011–2012 y los feriados?
