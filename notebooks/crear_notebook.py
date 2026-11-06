"""Genera notebooks/01_modelo_nucleo.ipynb (se ejecuta una vez; luego se trabaja en el notebook)."""
import nbformat as nbf

nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
nb.cells = [
    md("# 01 · Modelo núcleo: escalera M0 → M1 → M2\n\n"
       "Especificación prerregistrada el 13-oct-2026 (ver `src/config.py`). "
       "**Solo datos hasta 2023-12-31**: el tramo de prueba no se toca hasta congelar el modelo el 8-nov.\n\n"
       "- M0: solo constante (benchmark ingenuo)\n- M1: + NY y r_CLP\n- M2: + carry, riesgo (EM-VXY) y carry × riesgo\n\n"
       "Cada modelo se estima con ventana expansiva (desde 2004) y móvil (1.250 jornadas); el final es el promedio, "
       "calibrado con Platt anual sobre predicciones fuera de muestra."),
    code("import sys, pathlib\nsys.path.insert(0, str(pathlib.Path.cwd().parent))\n"
         "import numpy as np, pandas as pd, matplotlib.pyplot as plt\n"
         "from src import config as C, datos, modelo, evaluacion as ev, figuras\n"
         "pd.set_option('display.width', 200); pd.set_option('display.max_columns', 30)"),
    md("## 0. Versión\n\n**Última actualización del notebook: 2026-11-06 17:46 (hora de Chile).** "
       "La celda siguiente muestra la fecha de modificación de cada archivo en tu PC y su sello de versión, "
       "para verificar que tienes la última versión (compárala con `CHANGELOG.md`)."),
    code("import datetime as _dt\nraiz = pathlib.Path.cwd().parent\nfilas = []\n"
         "for f in sorted((raiz / 'src').glob('*.py')) + [raiz / 'CHANGELOG.md']:\n"
         "    sello = next((l.split(':', 1)[1].strip() for l in f.read_text(encoding='utf-8').splitlines() if l.startswith('# Última actualización')), '—')\n"
         "    filas.append({'archivo': f.relative_to(raiz).as_posix(),\n"
         "                  'modificado en tu PC': _dt.datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M'),\n"
         "                  'sello de versión': sello})\n"
         "pd.DataFrame(filas).set_index('archivo')"),
    code("print('Base leída:', C.ARCHIVO_BASE.name, '· huella', datos.huella_archivo(),\n"
         "      '· modificada en tu PC', _dt.datetime.fromtimestamp(C.ARCHIVO_BASE.stat().st_mtime).strftime('%Y-%m-%d %H:%M'))\n"
         "print('Huella de los datos que usa el modelo hasta 2023-12-29 (base del 6-oct y del 6-nov: d6ae3102ed):',\n"
         "      datos.huella_datos(datos.cargar_base(), '2023-12-29'))"),
    md("## 1. Tabla de modelamiento y prueba anti look-ahead"),
    code("x = datos.cargar_base()\ntabla_completa = datos.construir_tabla(x)\n"
         "print('Diferencia máxima al truncar la base (debe ser 0):', datos.chequear_sin_lookahead(x, tabla_completa))\n"
         "T = datos.recortar(tabla_completa)   # hasta 2023-12-31\n"
         "T[['ny', 'r_clp', 'carry', 'riesgo', 'y', 'rex_sig']].describe().round(3).T"),
    md("## 2. Coeficientes en entrenamiento 2004–2019 (errores Newey-West, 5 rezagos)\n\n"
       "Signos esperados: β(ny) > 0, β(r_clp) ≤ 0, β(carry) < 0, β(carry×riesgo) > 0."),
    code("tr = modelo._filas_validas(T[:'2019'], C.MODELOS['M2'])\n"
         "for m in ['M1', 'M2']:\n"
         "    r, _, _ = modelo.ajustar(tr, C.MODELOS[m], cov='HAC')\n"
         "    print(m); display(pd.DataFrame({'coef': r.params, 't (NW)': r.tvalues, 'p': r.pvalues}).round(3).T)"),
    md("## 3. Walk-forward 2010–2023: calidad de pronóstico"),
    code("res, platt = modelo.correr_escalera(T, range(C.INICIO_OOS, C.VALIDACION[1] + 1))\n"
         "cols = [f'{m}_{v}' for m in ['M0', 'M1', 'M2'] for v in ['exp', 'mov', 'prom', 'cal']]\n"
         "for a, b in [('2010', '2019'), ('2020', '2023')]:\n"
         "    print(f'--- {a}–{b}'); display(ev.tabla_pronostico(res, cols, a, b).round(4))"),
    md("## 4. Tests en validación 2020–2023\n\nClark-West (una cola, H1: el modelo grande es mejor) y Diebold-Mariano con corrección HLN, ambos sobre Brier."),
    code("v = res['2020':'2023'].dropna(subset=['y'])\nfilas = []\n"
         "for chico, grande in [('M0_cal','M1_cal'), ('M1_cal','M2_cal'), ('M0_cal','M2_cal'),\n"
         "                      ('M0_exp','M2_exp'), ('M0_mov','M2_mov')]:\n"
         "    cw_t, cw_p = ev.clark_west(v.y, v[chico], v[grande])\n"
         "    dm_t, dm_p = ev.diebold_mariano(v.y, v[chico], v[grande])\n"
         "    filas.append({'comparación': f'{grande} vs {chico}', 'CW t': cw_t, 'CW p': cw_p, 'DM t': dm_t, 'DM p': dm_p})\n"
         "pd.DataFrame(filas).set_index('comparación').round(3)"),
    md("**Acierto direccional (DA) con test de Pesaran-Timmermann (1992)** — agregado el 20-oct. "
       "H0: el pronóstico de signo es independiente del resultado; descuenta el acierto que se obtendría por las frecuencias marginales."),
    code("filas = []\n"
         "for a, b in [('2010', '2019'), ('2020', '2023')]:\n"
         "    vv = res[a:b].dropna(subset=['y'])\n"
         "    for m in ['M1_cal', 'M2_cal']:\n"
         "        da, da0, z, pv = ev.pesaran_timmermann(vv.y, vv[m])\n"
         "        filas.append({'tramo': f'{a}–{b}', 'modelo': m, 'DA': da, 'DA bajo independencia': da0,\n"
         "                      'Siempre lo más frecuente': max(vv.y.mean(), 1 - vv.y.mean()), 'PT': z, 'p-valor': pv})\n"
         "pd.DataFrame(filas).set_index(['tramo', 'modelo']).round(3)"),
    md("## 5. Calibración: parámetros de Platt por año (pendiente < 1 = el modelo bruto es sobreconfiado)"),
    code("pd.DataFrame({m: {a: p[1] for a, p in platt[m].items()} for m in ['M1', 'M2']}).round(3)"),
    md("## 6. Valor económico en validación 2020–2023\n\n"
       "**Regla oficial (13-oct):** Kelly fraccional discreto por utilidad, "
       "k = argmax U(k) = k·μ − k²σ²/(2c) − costo·|k − k_anterior|, k ∈ {−3,−1,0,1,3}. "
       "Se compara con la regla prerregistrada original (`posicion_kelly`), que tenía un defecto (ver registro E04). "
       "**Costo supuesto: 2 pb por unidad de cambio** hasta que el laboratorio lo informe."),
    code("tt = T.reindex(v.index); rex = v.rex.fillna(0); filas = {}; curvas = {}\n"
         "for nombre in ['M1_cal', 'M2_cal']:\n"
         "    for c in [C.KELLY_C, C.KELLY_C_ROBUSTEZ]:\n"
         "        bt = ev.backtest(ev.posicion_kelly_utilidad(v[nombre], tt.abs_r_60, tt.sd_r_60, c=c), rex)\n"
         "        filas[f'{nombre} utilidad c={c}'] = ev.resumen(bt, v.rex); curvas[f'{nombre} utilidad c={c}'] = bt\n"
         "bt = ev.backtest(ev.posicion_kelly(v['M1_cal'], tt.abs_r_60, tt.sd_r_60, c=C.KELLY_C), rex)\n"
         "filas['M1_cal regla original c=0.25'] = ev.resumen(bt, v.rex); curvas['M1_cal regla original c=0.25'] = bt\n"
         "for ref, k in [('Comprar siempre (+1)', 1), ('Comprar siempre (+3)', 3), ('No operar (0)', 0)]:\n"
         "    bt = ev.backtest(pd.Series(float(k), index=v.index), rex)\n"
         "    filas[ref] = ev.resumen(bt, v.rex); curvas[ref] = bt\n"
         "pd.DataFrame(filas).T.round(2)"),
    code("fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={'height_ratios': [3, 1]})\n"
         "for k in ['M1_cal utilidad c=0.25', 'M1_cal utilidad c=0.2', 'M1_cal regla original c=0.25', 'Comprar siempre (+1)']:\n"
         "    a1.plot(100 * (1 + curvas[k].neto.cumsum()), label=k)\n"
         "a1.axhline(100, color='grey', lw=.8); a1.set_ylabel('Resultado acumulado neto (base 100)'); a1.legend()\n"
         "a2.step(curvas['M1_cal utilidad c=0.25'].index, curvas['M1_cal utilidad c=0.25'].pos, lw=.6)\n"
         "a2.set_ylabel('Exposición M1 (c=¼)'); plt.tight_layout(); plt.show()"),
    md("## 7. Robustez del modelo operativo (M1 calibrado, regla de utilidad, c = ¼)"),
    code("v2 = res['2011':'2023'].dropna(subset=['y']); t2 = T.reindex(v2.index); rex2 = v2.rex.fillna(0)\n"
         "pos = ev.posicion_kelly_utilidad(v2.M1_cal, t2.abs_r_60, t2.sd_r_60, c=C.KELLY_C)\n"
         "bt = ev.backtest(pos, rex2); n = bt.neto\n"
         "sh = lambda s: s.mean() / s.std() * np.sqrt(252)\n"
         "print('Por año (2011–2012 tienen huecos en la base: interpretar con cautela)')\n"
         "display(pd.DataFrame({'Retorno neto %': n.groupby(n.index.year).sum() * 100,\n"
         "                      'Sharpe': n.groupby(n.index.year).apply(sh),\n"
         "                      '% días en 0': (bt.pos == 0).groupby(bt.index.year).mean() * 100}).round(2))\n"
         "w = n['2020':'2023']; s = w.sort_values()\n"
         "print(f'Sharpe 2020–2023: {sh(w):.2f} | sin 1er semestre 2020: {sh(n[\"2020-07\":\"2023\"]):.2f} | '\n"
         "      f'sin 10 mejores y 10 peores días: {sh(s.iloc[10:-10]):.2f}')\n"
         "rng = np.random.default_rng(0); k = pos['2020':'2023'].abs(); r = rex2['2020':'2023']\n"
         "plac = [sh(k * rng.choice([-1, 1], len(k)) * r) for _ in range(1000)]\n"
         "print(f'Placebo de signo aleatorio (1.000 sorteos): p95 = {np.percentile(plac, 95):.2f}; p-valor = {np.mean(np.array(plac) >= sh(w)):.3f}')"),
    md("## 8. Ejecución realista vs. convención del torneo (E07, agregado el 20-oct)\n\n"
       "Mismo modelo y mismas posiciones; solo cambia el precio de ejecución. La convención del torneo es cierre→cierre. "
       "En la práctica, al decidir al cierre de t el primer precio onshore transable es la apertura de t+1."),
    code("tramos = [('Torneo: cierre→cierre', 'rex_sig'), ('Realista: apertura→apertura', 'rex_ap_ap'),\n"
         "          ('Solo sesión t+1: apertura→cierre', 'rex_ap_ci'), ('Solo tramo nocturno (no transable)', 'rex_noche')]\n"
         "for a, b in [('2011', '2019'), ('2020', '2023')]:\n"
         "    vv = res[a:b].dropna(subset=['y']); t3 = T.reindex(vv.index)\n"
         "    pos = ev.posicion_kelly_utilidad(vv.M1_cal, t3.abs_r_60, t3.sd_r_60, c=C.KELLY_C)\n"
         "    tabla_ej = pd.DataFrame({nom: ev.resumen(ev.backtest(pos, t3[col].fillna(0)), t3[col]) for nom, col in tramos}).T\n"
         "    print(f'--- {a}–{b}'); display(tabla_ej[['Ret. anual neto %', 'Sharpe', 'Máx. drawdown %', 'Acierto días activos']].round(2))\n"
         "    print('Descomposición que suma (costos cobrados una vez; % anual):')\n"
         "    display(ev.descomposicion_tramos(pos, t3).round(2).to_frame(f'{a}–{b}').T)\n"
         "    print(f'Correlación tramo nocturno – sesión: {t3.rex_noche.corr(t3.rex_ap_ci):.3f}')"),
    md("**Lectura:** en 2011–2019 toda la ventaja está en el tramo nocturno no transable (asincronía de cierres), y ejecutar a la apertura da Sharpe negativo: "
       "durante la sesión el CLP revierte parte del salto de apertura. Se reporta como hallazgo en el informe.\n\n"
       "**21-oct (auditoría):** (i) la ejecución apertura→apertura ahora paga el carry de t+1 a t+2 (antes, el de t a t+1, desfasado un día); "
       "(ii) las filas «solo sesión» y «solo nocturno» de la tabla de arriba cobran el costo cada una, así que no suman: la descomposición "
       "de abajo usa los tramos en bruto y cobra carry y costos una sola vez, y su resultado neto coincide con el cierre a cierre."),
    md("## 9. Sensibilidad a costos: ¿dónde deja de ser rentable? (E08, 20-oct)\n\n"
       "Costo por unidad de cambio de exposición, en pb (≈ medio spread; a ~985 CLP/USD, **1 CLP ≈ 10 pb**; corregido el 20-oct 19:15, antes decía 1 pb). "
       "Referencias retail al 20-oct-2026: CFD (Admiral) ~2–4 pb + swap; Buda ~7–10 pb; apps/fintech (Global66, Racional, XTB) ~10–40 pb; "
       "Fintual ~47 pb; AFEX ~100 pb; bancos ~75–250 pb. **Fija** = posiciones decididas con 2 pb; **reoptimiza** = la regla decide con el costo nuevo."),
    code("grid = [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25]\n"
         "for a, b in [('2011', '2019'), ('2020', '2023')]:\n"
         "    vv = res[a:b].dropna(subset=['y']); t4 = T.reindex(vv.index)\n"
         "    S = ev.sensibilidad_costos(vv.M1_cal, t4.abs_r_60, t4.sd_r_60, vv.rex.fillna(0), grid)\n"
         "    print(f'--- {a}–{b}'); display(S.pivot(index='costo_pb', columns='regla', values=['Ret. anual neto %', 'Sharpe']).round(2))"),
    code("filas = []\n"
         "for a, b in [('2011', '2019'), ('2020', '2023')]:\n"
         "    vv = res[a:b].dropna(subset=['y']); t4 = T.reindex(vv.index)\n"
         "    for c in [C.KELLY_C, C.KELLY_C_ROBUSTEZ]:\n"
         "        pos = ev.posicion_kelly_utilidad(vv.M1_cal, t4.abs_r_60, t4.sd_r_60, c=c)\n"
         "        for ej, col in [('cierre→cierre', 'rex_sig'), ('apertura→apertura', 'rex_ap_ap')]:\n"
         "            filas.append({'tramo': f'{a}–{b}', 'c': c, 'ejecución': ej,\n"
         "                          'costo de equilibrio (pb)': ev.costo_equilibrio(pos, t4[col].fillna(0))})\n"
         "print('Costo por unidad de cambio que deja el retorno neto en 0 (negativo = ya pierde antes de costos)')\n"
         "display(pd.DataFrame(filas).round(2))\n"
         "vv = res['2020':'2023'].dropna(subset=['y']); t4 = T.reindex(vv.index)\n"
         "cfd = {f'swap +{m}%/año': ev.sensibilidad_costos(vv.M1_cal, t4.abs_r_60, t4.sd_r_60, vv.rex.fillna(0), [4], swap_anual=m / 100)\n"
         "       .query('regla == \"fija\"')[['Ret. anual neto %', 'Sharpe']].iloc[0] for m in [0, 2, 5, 13]}\n"
         "print('CFD 2020–2023: costo 4 pb por unidad + sobreprecio del swap sobre el carry justo')\n"
         "display(pd.DataFrame(cfd).T.round(2))"),
    md("**Lectura:** con la convención del torneo, el punto de equilibrio está en ~9–13 pb por unidad de cambio. "
       "Para un retail solo el CFD (2–4 pb) queda bajo el equilibrio (Sharpe 0,59–0,75 sin swap); Buda queda en el borde y sin venta corta; apps, casas de cambio y bancos hacen perder dinero. "
       "Reoptimizar con el costo no rescata la estrategia: deja de operar y el Sharpe cae a ~0,1–0,2. "
       "En 2011–2019 con ejecución a la apertura ya pierde antes de costos, así que no hay costo de equilibrio. "
       "El swap del CFD (~13–15 % anual cobrado a ambos lados) es el costo dominante: con 2–4 pb y 13 % de sobrecosto, 2020–2023 rinde 3,0–5,3 % (Sharpe 0,23–0,41) y 2011–2019 pierde."),
    md("## 10. Evaluación formal contra las referencias (E09, 20-oct)\n\n"
       "Diseño acordado el 20-oct, **antes** de ver resultados:\n"
       "- Se compara la ganancia neta diaria: d_t = PnL_modelo − PnL_ref (costo 2 pb, carry incluido).\n"
       "- **Diebold-Mariano con pérdida económica** (−PnL), Newey-West 5 rezagos + HLN, una cola.\n"
       "- **Bootstrap estacionario pareado** (Politis-Romano), 10.000 réplicas, bloque medio 10 días (robustez 5 y 20), p-valor centrado bajo H0.\n"
       "- **Estadístico principal: diferencia de retorno neto anual**; Sharpe con igual prominencia.\n"
       "- «Exposición fija 1» es ambigua en las bases: se evalúan ambas lecturas (+1/+3 siempre y señal M1 con tamaño fijo 1). "
       "Holm se aplica sobre las 4 comparaciones (más conservador que sobre 3).\n"
       "- **Sharpe deflactado** con N = 48 variantes backtesteadas (M1/M2/M1C × 4 versiones × c ∈ {¼, ⅕} × 2 reglas; M1C sumado el 20-oct tras E10)."),
    code("refs = lambda idx_, p_: {'No operar (0)': pd.Series(0., index=idx_), 'Comprar siempre (+1)': pd.Series(1., index=idx_),\n"
         "                         'Comprar siempre (+3)': pd.Series(3., index=idx_), 'Señal M1, tamaño fijo 1': np.sign(p_ - .5)}\n"
         "robustez = {}\n"
         "for a, b in [('2011', '2019'), ('2020', '2023')]:\n"
         "    vv = res[a:b].dropna(subset=['y']); t5 = T.reindex(vv.index); rx = vv.rex.fillna(0)\n"
         "    nm = ev.backtest(ev.posicion_kelly_utilidad(vv.M1_cal, t5.abs_r_60, t5.sd_r_60), rx).neto\n"
         "    for L in [10, 5, 20]:\n"
         "        idx = ev.indices_bootstrap_estacionario(len(nm), bloque=L)\n"
         "        R = pd.DataFrame({k: ev.comparar_con_referencia(nm, ev.backtest(p_, rx).neto, idx) for k, p_ in refs(vv.index, vv.M1_cal).items()}).T\n"
         "        R['p Holm (retorno)'] = ev.holm(R['p bootstrap (retorno)'])\n"
         "        if L == 10:\n"
         "            print(f'--- {a}–{b} (bloque 10)'); display(R.round(3))\n"
         "        robustez[(f'{a}–{b}', f'bloque {L}')] = R['p bootstrap (retorno)']\n"
         "    sh = [ (lambda n_: n_.mean() / n_.std())(ev.backtest(f(vv[f'{m}_{ver}'], t5.abs_r_60, t5.sd_r_60, c=c), rx).neto)\n"
         "           for m in ['M1', 'M2', 'M1C'] for ver in ['exp', 'mov', 'prom', 'cal'] for c in [0.25, 0.2]\n"
         "           for f in [ev.posicion_kelly_utilidad, ev.posicion_kelly]]\n"
         "    print(f'Sharpe {nm.mean() / nm.std() * np.sqrt(252):.2f} | lugar entre los {len(sh)} ensayos: '\n"
         "          f'{int((np.array(sh) > nm.mean() / nm.std() + 1e-12).sum()) + 1}.º')\n"
         "    for N_ in [len(sh), 100, 200]:   # A4: N mayores cubren cribado de series, ventanas y embargo\n"
         "        dsr, sr0, N = ev.sharpe_deflactado(nm, sh, N=N_)\n"
         "        print(f'   N = {N}: umbral SR0 = {sr0:.2f} | Sharpe deflactado (prob.) = {dsr:.3f}')\n"
         "print('Robustez al largo de bloque: p bootstrap de la diferencia de retorno'); pd.DataFrame(robustez).round(3)"),
    md("**Lectura (validación, no es el resultado oficial):** la estrategia le gana con significancia a *no operar* en ambos tramos "
       "(tras Holm solo en 2020–2023). Contra *comprar siempre (+1)* la diferencia es grande (~12–15 pp al año) pero marginal (p ≈ 0,07–0,09); "
       "contra *+3* no es significativa por la volatilidad de esa referencia. La regla de tamaño agrega valor frente a la señal con tamaño fijo en 2011–2019 (p ≈ 0,05), no en 2020–2023. "
       "Sharpe deflactado < 0,95 en ambos tramos (ver valores arriba; bajan al sumar los ensayos de M1C). **Problema de potencia:** con Sharpe 0,9 y ~690 días de prueba, t ≈ 0,9·√2,7 ≈ 1,5; "
       "aunque la ventaja sea real, es esperable no alcanzar p < 0,05 en el tramo de prueba."),
    md("## 11. Candidato prerregistrado: M1 + cobre COMEX (E10, 20-oct)\n\n"
       "Prerregistrado a las 17:52 del 20-oct, antes de correrlo (`src/config.py`, registro E10). "
       "COMEX liquida a las 13:00 ET, después del cierre onshore del CLP (~13:00–13:30), igual que la señal NY. "
       "Días de cambio de contrato: si |r_HG − r_LME| > 3 desv. se usa r_LME. **Regla: entra solo si Clark-West vs M1 da p < 0,05 en 2020–2023.**"),
    code("print('Días con cambio de contrato reemplazados por LME (2004–2023):', int(T.cobre_roll.sum()))\n"
         "tr = modelo._filas_validas(T[:'2019'], C.MODELOS['M1C']); r, _, _ = modelo.ajustar(tr, C.MODELOS['M1C'], cov='HAC')\n"
         "display(pd.DataFrame({'coef': r.params, 't (NW)': r.tvalues, 'p': r.pvalues}).round(3).T)\n"
         "display(T[['ny', 'r_clp', 'cobre']].corr().round(2))\n"
         "filas = []\n"
         "for a, b in [('2010', '2019'), ('2020', '2023')]:\n"
         "    vv = res[a:b].dropna(subset=['y']); t6 = T.reindex(vv.index)\n"
         "    cw_t, cw_p = ev.clark_west(vv.y, vv.M1_cal, vv.M1C_cal)\n"
         "    ve = vv['2011':] if a == '2010' else vv; te = T.reindex(ve.index)   # valor económico desde 2011 (2010 sin Platt), como en las secciones 7–10\n"
         "    pos = ev.posicion_kelly_utilidad(ve.M1C_cal, te.abs_r_60, te.sd_r_60)\n"
         "    rs = ev.resumen(ev.backtest(pos, ve.rex.fillna(0)), ve.rex)\n"
         "    filas.append({'tramo': f'{a}–{b}', 'Brier M1': ev.brier(vv.M1_cal, vv.y), 'Brier M1C': ev.brier(vv.M1C_cal, vv.y),\n"
         "                  'CW t': cw_t, 'CW p': cw_p, 'Ret. neto M1C %': rs['Ret. anual neto %'], 'Sharpe M1C': rs['Sharpe']})\n"
         "pd.DataFrame(filas).set_index('tramo').round(4)"),
    md("**Resultado: M1C se descarta.** En 2004–2019 el coeficiente del cobre no es significativo (t ≈ 0,5) una vez que está la señal NY (correlación −0,38): "
       "el movimiento del cobre después del cierre ya está contenido en las monedas emergentes y el dólar global. "
       "Clark-West en validación: p = 0,55 (en 2010–2019, p = 0,07). El valor económico también es menor (Sharpe 0,78 vs 0,92 en 2020–2023). "
       "**M1 sigue siendo el modelo operativo.**"),
    md("## 12. Perfiles de inversionista (E12, 21-oct)\n\n"
       "Costo en pesos por dólar comprado o vendido, según la experiencia profesional de uno de los autores en carteras discrecionales "
       "de alto patrimonio: **institucional 0,5 CLP**, **retail 2 CLP**. El costo diario en fracción es pesos / tipo de cambio del día "
       "(por eso es mayor en pb cuando el dólar estaba más barato). Cada perfil usa la regla de Kelly con su propio costo ('regla propia'); "
       "como comparación, se cobran esos costos a las posiciones decididas con 2 pb. Prerregistrado para la corrida del 8-nov."),
    code("cols_p = ['Ret. anual neto %', 'Vol. anual %', 'Sharpe', 'Máx. drawdown %', '% días en 0', 'Costos / PnL bruto %', 'Costo medio (pb)']\n"
         "for a, b in [('2011', '2019'), ('2020', '2023')]:\n"
         "    vv = res[a:b].dropna(subset=['y']); t7 = T.reindex(vv.index)\n"
         "    P = ev.perfiles_inversionista(vv.M1_cal, t7.abs_r_60, t7.sd_r_60, vv.rex.fillna(0), t7.spot)\n"
         "    print(f'--- {a}–{b} (tipo de cambio medio {t7.spot.mean():.0f})'); display(P[cols_p].round(2))"),
    md("**Lectura:** el inversionista institucional gana dinero, pero mucho menos que con la convención del torneo; el retail, sabiendo su costo, "
       "prácticamente no opera (y si operara con las posiciones del torneo perdería). Con costos altos, la regla que conoce su costo rinde menos que "
       "mantener las posiciones de 2 pb en 2020–2023: al operar menos pierde días buenos, porque la ventaja es de alta frecuencia. "
       "Parte de esa diferencia viene de una limitación declarada de la regla: cobra el costo completo de un cambio contra la ganancia de un solo día (auditoría A5)."),
    md("### 12b. E13: perfiles × ejecución (prerregistrado el 21-oct para la corrida del 8-nov)\n\n"
       "Cambio de **reporte**, no de modelo: las mismas posiciones de E12 se liquidan con la convención del torneo (cierre a cierre) "
       "y con la ejecución disponible para quien decide después del cierre de Nueva York (apertura a apertura). "
       "En el tramo de prueba se reportará esta misma tabla, tal como salga (`ev.perfiles_por_ejecucion`, `C.EJECUCIONES_E13`)."),
    code("for a, b in [('2011', '2019'), ('2020', '2023')]:\n"
         "    vv = res[a:b].dropna(subset=['y']); t8 = T.reindex(vv.index)\n"
         "    E = ev.perfiles_por_ejecucion(vv.M1_cal, t8.abs_r_60, t8.sd_r_60, t8)\n"
         "    print(f'--- {a}–{b}'); display(E[['Ret. anual neto %', 'Sharpe', 'Máx. drawdown %', '% días en 0']].round(2))"),
    md("## 13. Tablas del informe no cubiertas arriba (21-oct)\n\n"
       "Para que cada tabla del informe salga de este notebook: estadísticas descriptivas (Tabla 3), valor económico 2011–2019 "
       "(panel B de la Tabla 7) y resultado anual con la referencia de comprar siempre (Tabla 9)."),
    code("d = T[:'2023']\n"
         "desc = pd.DataFrame({'Retorno USD/CLP (pb)': d.r_sig * 1e4, 'Carry del período (pb)': d.carry_periodo * 1e4,\n"
         "                     'Retorno en exceso (pb)': d.rex_sig * 1e4, 'Señal NY': d.ny, 'r_CLP': d.r_clp,\n"
         "                     'Diferencial de tasas (%)': d.carry, 'Volatilidad emergente': d.riesgo}).describe().T\n"
         "display(desc[['count', 'mean', 'std', 'min', 'max']].round(2))\n"
         "print(f'Días con alza en exceso de carry: {d.y.mean():.1%}')"),
    code("vB = res['2011':'2019'].dropna(subset=['y']); tB = T.reindex(vB.index); rB = vB.rex.fillna(0); fB = {}\n"
         "for c in [C.KELLY_C, C.KELLY_C_ROBUSTEZ]:\n"
         "    fB[f'M1 c={c}'] = ev.resumen(ev.backtest(ev.posicion_kelly_utilidad(vB.M1_cal, tB.abs_r_60, tB.sd_r_60, c=c), rB), vB.rex)\n"
         "fB['Señal tamaño fijo'] = ev.resumen(ev.backtest(np.sign(vB.M1_cal - .5), rB), vB.rex)\n"
         "for ref, k in [('Comprar siempre (+1)', 1), ('Comprar siempre (+3)', 3), ('No operar (0)', 0)]:\n"
         "    fB[ref] = ev.resumen(ev.backtest(pd.Series(float(k), index=vB.index), rB), vB.rex)\n"
         "print('Panel B, 2011–2019'); pd.DataFrame(fB).T.round(2)"),
    code("v3 = res['2011':'2023'].dropna(subset=['y']); t3_ = T.reindex(v3.index); r3 = v3.rex.fillna(0)\n"
         "b3 = ev.backtest(ev.posicion_kelly_utilidad(v3.M1_cal, t3_.abs_r_60, t3_.sd_r_60), r3); n3 = b3.neto\n"
         "bh = ev.backtest(pd.Series(1., index=v3.index), r3).neto; yr = n3.index.year\n"
         "sharpe = lambda x: x.mean() / x.std() * np.sqrt(252)   # 'sh' se reutiliza en la sección 10\n"
         "pd.DataFrame({'Retorno neto %': n3.groupby(yr).sum() * 100, 'Sharpe': n3.groupby(yr).apply(sharpe),\n"
         "              '% en 0': (b3.pos == 0).groupby(yr).mean() * 100, '% en ±3': (b3.pos.abs() == 3).groupby(yr).mean() * 100,\n"
         "              'Comprar siempre %': bh.groupby(yr).sum() * 100}).round(2)"),
    md("## 14. Figuras del informe (21-oct)\n\n"
       "Se guardan en `reports/figuras/` como PDF vectorial. Figura 1: curva de resultado frente a las referencias con la exposición "
       "(exigida por las bases). Figura 2: diagrama de confiabilidad. Figura 3: resultado según el tramo del retorno. Figura 4: retorno neto según el costo, con equilibrio y canales."),
    code("from IPython.display import Image\n"
         "rutas = figuras.todas(res, T)\n"
         "for r in rutas: print(r.relative_to(C.RAIZ))\n"
         "figuras.estilo_paper()\n"
         "import matplotlib.pyplot as _plt\n"
         "_plt.rcParams['figure.dpi'] = 110"),
    md("## 15. Decisiones (13, 20 y 21-oct)\n\n- **Modelo operativo: M1** (regla de la escalera: M2 no supera a M1 con Clark-West). M2 se reporta como especificación prerregistrada descartada.\n- **Regla oficial: Kelly discreto por utilidad**, c = ¼ (robustez c = ⅕).\n- **20-oct:** resultado oficial con la convención del torneo; ejecución realista reportada con la misma prominencia (sección 8).\n- **20-oct (E08):** costo de equilibrio ~9–13 pb por unidad; el costo base de 2 pb se mantiene (nivel institucional; en retail solo un CFD se acerca).\n- **20-oct (E09):** diseño de la evaluación formal fijado antes de verla (sección 10); estadístico principal = diferencia de retorno neto.\n- **20-oct (E10):** M1 + cobre COMEX prerregistrado y descartado (CW p = 0,55). LightGBM y momentum descartados por diseño. **M1 queda como modelo final candidato para el 1-nov.**\n- **21-oct (E12):** dos perfiles de costo prerregistrados para la corrida del 8-nov: institucional (0,5 CLP) y retail (2 CLP); el resultado oficial sigue siendo la convención del torneo (2 pb).\n- **21-oct (auditoría, E13):** se prerregistra el reporte de los perfiles con ambas ejecuciones (cierre a cierre y apertura a apertura); se corrige el carry de la ejecución a la apertura (desfasado un día); la descomposición por tramos cobra los costos una sola vez; el DSR se reporta con N = 48, 100 y 200. La regla miope de costos (A5) queda como limitación declarada.\n- Ver `reports/registro_experimentos.csv` y `CHANGELOG.md`."),
]
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, "notebooks/01_modelo_nucleo.ipynb")
print("ok")
