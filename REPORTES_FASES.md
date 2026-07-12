# Reporte Consolidado de Fases — Proyecto Paper IEEE

Este documento detalla el progreso y los resultados de las **Fases 0, 1B, 2, 3 y 4** del desarrollo y análisis de la permutación Keccak modificada con la capa lineal `Σ''_ligero` (solo paridad de columna) y la S-box de ASCON `χ'`.

---

## ### Reporte de Fase 0 — Piloto de tratabilidad

**Objetivo:** Determinar la tratabilidad computacional del modelo MILP con la capa lineal simplificada `Σ''_ligero`.

**Resultados de las corridas piloto:**
| ID | z | rounds | time_limit | sol_status_raw | es_optimo | n / cota | tiempo(s) | vars | restr. |
|---|---|---|---|---|---|---|---|---|---|
| P1 | 1 | 1 | 120 | 1 (Optimal) | Sí | 2 (Óptimo) | 3.07 | 165 | 847 |
| P2 | 1 | 2 | 120 | 1 (Optimal) | Sí | 4 (Óptimo) | 13.90 | 305 | 1692 |
| P3 | 2 | 1 | 180 | 2 (Feasible) | No | cota <= 2 | 180.09 | 330 | 1692 |

**Archivos adjuntos (en el repositorio):**
- Logs de CBC: [P1.log](file:///home/pineda/Downloads/Seguridad_Final/PAPER_IEEE/fase0_piloto/logs/P1.log), [P2.log](file:///home/pineda/Downloads/Seguridad_Final/PAPER_IEEE/fase0_piloto/logs/P2.log), [P3.log](file:///home/pineda/Downloads/Seguridad_Final/PAPER_IEEE/fase0_piloto/logs/P3.log)
- Resultados JSON: [resultados_ligero_r1_z1.json](file:///home/pineda/Downloads/Seguridad_Final/PAPER_IEEE/fase0_piloto/logs/resultados_ligero_r1_z1.json), [resultados_ligero_r2_z1.json](file:///home/pineda/Downloads/Seguridad_Final/PAPER_IEEE/fase0_piloto/logs/resultados_ligero_r2_z1.json), [resultados_ligero_r1_z2.json](file:///home/pineda/Downloads/Seguridad_Final/PAPER_IEEE/fase0_piloto/logs/resultados_ligero_r1_z2.json)

**Hallazgos inesperados o ambiguos:**
- P3 agotó el límite de tiempo (180s) a escala $z=2$ para una sola ronda, encontrando una solución factible de 2 pero sin poder certificar optimalidad. Esto confirma que incluso con la simplificación a solo paridad de columna, el solver CBC open-source experimenta intratabilidad para $z \ge 2$.
- Consecuentemente, caemos en **Rama B** del Gate 0.

---

## ### Reporte de Fase 1B — Acotamiento honesto a z=1

**Objetivo:** Completar la matriz MILP a escala mínima $z=1$ para las rondas 1, 2 y 3.

**Resultados de la matriz z=1:**
| Rondas (r) | z | sol_status_raw | es_optimo | n / cota | tiempo(s) | vars | restr. |
|---|---|---|---|---|---|---|---|
| 1 | 1 | 1 (Optimal) | Sí | 2 (Óptimo) | 3.25 | 165 | 847 |
| 2 | 1 | 1 (Optimal) | Sí | 4 (Óptimo) | 13.76 | 305 | 1692 |
| 3 | 1 | 0 (No Sol) | No | cota <= 0 | 179.90 | 445 | 2537 |

**Archivos adjuntos (en el repositorio):**
- Logs de CBC: [resultados_ligero_r1_z1.log](file:///home/pineda/Downloads/Seguridad_Final/PAPER_IEEE/fase1_matriz/logs/resultados_ligero_r1_z1.log), [resultados_ligero_r2_z1.log](file:///home/pineda/Downloads/Seguridad_Final/PAPER_IEEE/fase1_matriz/logs/resultados_ligero_r2_z1.log), [resultados_ligero_r3_z1.log](file:///home/pineda/Downloads/Seguridad_Final/PAPER_IEEE/fase1_matriz/logs/resultados_ligero_r3_z1.log)

**Hallazgos inesperados o ambiguos:**
- La corrida de 3 rondas a $z=1$ no logró encontrar ninguna solución factible en 180s (`sol_status_raw: 0`), lo que muestra que el crecimiento de variables de control y restricciones lógicas para 3 rondas (445 vars, 2537 restr) satura la capacidad de búsqueda de CBC en el tiempo límite dado.

---

## ### Reporte de Fase 2 — Matriz MILP formal completa

**Objetivo:** Consolidar la comparación entre el Baseline (Keccak estándar) y la propuesta modificada (`Σ''_ligero` + ASCON S-box).

**Tabla comparativa de resultados (z=1):**
| Exp. ID | Variante | Rondas | z | Variables | Restricciones | S-boxes Activas (n) | Desglose Ronda | P_total | Pares Necesarios | sol_status_raw | Tiempo (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B-r1-z1 | Baseline (Keccak) | 1 | 1 | 70 | 437 | 1 (Óptimo) | [1] | 2^{-2} = 0.2500 | 2^2 | 1 (Optimal) | 1.05 |
| B-r2-z1 | Baseline (Keccak) | 2 | 1 | 115 | 872 | 4 (Óptimo) | [2, 2] | 2^{-4} = 0.0625 | 2^4 | 1 (Optimal) | 50.35 |
| B-r3-z1 | Baseline (Keccak) | 3 | 1 | 160 | 1307 | Not Solved (cota <= 11) | N/A | >= 2^{-22} | >= 2^{22} | 2 (Feasible) | 180.05 |
| M_ligero-r1-z1 | Propuesta (Σ''_ligero) | 1 | 1 | 165 | 847 | 2 (Óptimo) | [2] | 2^{-4} | 2^4 | 1 (Optimal) | 3.25 |
| M_ligero-r2-z1 | Propuesta (Σ''_ligero) | 2 | 1 | 305 | 1692 | 4 (Óptimo) | [2, 2] | 2^{-8} | 2^8 | 1 (Optimal) | 13.76 |
| M_ligero-r3-z1 | Propuesta (Σ''_ligero) | 3 | 1 | 445 | 2537 | Not Solved (cota <= 0) | N/A | N/A | N/A | 0 (No Sol) | 179.90 |

*Nota metodológica: Las filas marcadas como "Óptimo" están certificadas formalmente mediante `sol_status == LpSolutionOptimal`. Las filas de 3 rondas excedieron el límite de tiempo y se reportan como cotas superiores o sin solución factible según corresponda.*

**Hallazgos clave para el paper:**
1.  **Ganancia en Ronda 1:** La propuesta duplica las S-boxes activas mínimas (**2 vs 1**), incrementando la resistencia local diferencial en un factor de $2^{-2}$ en probabilidad de trails.
2.  **Eficiencia computacional en Ronda 2:** Ambas variantes alcanzan exactamente el mismo óptimo de **4 S-boxes activas** en 2 rondas, pero el modelo de la propuesta resolvió considerablemente más rápido en el solver CBC (**13.76s vs 50.35s**). Esto sugiere que la estructura lineal local de `Σ''_ligero` es computacionalmente más simple para el solver, a pesar de tener más restricciones de base.

---

## ### Reporte de Fase 3 — Comparación de S-boxes no lineales

**Objetivo:** Caracterizar y comparar propiedades algebraicas y de DDT de las S-boxes candidatas.

**Tabla comparativa de S-boxes:**
| S-box | Ancho (bits) | Biyectiva | DDT Máx Entry | p_max | Grado Alg. | Compuertas Estimadas | Fuente |
|---|---|---|---|---|---|---|---|
| Keccak \chi | 5 | Sí | 8 | 0.25 (2^{-2}) | 2 | 5 NOT, 5 AND, 5 XOR (Profundidad AND: 1) | Keccak Reference, NIST |
| ASCON \chi' | 5 | Sí | 8 | 0.25 (2^{-2}) | 2 | 6 NOT, 5 AND, 11 XOR (Profundidad AND: 1) | ASCON Spec, NIST LWC |
| PRESENT | 4 | Sí | 4 | 0.25 (2^{-2}) | 3 | 3 NOT, 3 AND, 4 XOR, 3 OR (Profundidad AND: 2) | PRESENT Paper, CHES 2007 |
| GIFT | 4 | Sí | 4 | 0.25 (2^{-2}) | 3 | 3 NOT, 2 AND, 4 XOR, 1 OR, 1 NAND, 1 NOR (Profundidad AND: 2) | GIFT Paper, CHES 2017 |

**Análisis matemático:**
- **Invariancia afín:** Se demuestra computacionalmente que `ASCON χ'` mantiene las mismas propiedades diferenciales ($p_{\max}=0.25$) y de grado algebraico (2) que `Keccak χ`, debido a que es afín-equivalente. Su mayor costo de compuertas XOR (11 vs 5) se justifica únicamente por romper simetrías algebraicas débiles del diseño original.
- **PRESENT/GIFT:** Al operar en 4 bits, alcanzan un grado algebraico mayor (3) con un área de silicio potencialmente reducida, pero a costa de duplicar la profundidad lógica AND (2 vs 1), lo cual penaliza la velocidad y aumenta la latencia por ronda.

---

## ### Reporte de Fase 4 — Verificación formal de la vulnerabilidad V3

**Objetivo:** Analizar la existencia de autovectores (subespacios invariantes) bajo las capas lineales del Baseline y de la Propuesta sobre el cuerpo finito $\mathbb{F}_2$.

**Resultados de la verificación de autovectores ($z=1$):**
- **Baseline (Keccak):** Dimensión del kernel de $(M_b \oplus I) = 5$.
- **Propuesta (Σ''_ligero):** Dimensión del kernel de $(M_p \oplus I) = 4$.

**Análisis físico de la vulnerabilidad V3:**
La existencia de una dimensión de kernel mayor a 0 en la propuesta (dim=4) demuestra formalmente la existencia de autovectores. Un ejemplo concreto es el autovector `v_0`:
```text
[[1 1 0 0 0]
 [1 1 0 0 0]
 [1 1 0 0 0]
 [1 1 0 0 0]
 [1 1 0 0 0]]
```
Este vector tiene filas idénticas, lo que implica una **uniformidad por filas** (todos los elementos de una fila $y$ tienen el mismo valor).
1.  **En la capa lineal:** La uniformidad por filas garantiza que la paridad de columnas `P[x]` sea idéntica para todas las columnas (en este caso, `1 ⊕ 1 ⊕ 0 ⊕ 0 ⊕ 0 = 0`). Dado que la paridad de columna es cero, la capa `Σ''_ligero` actúa de forma idéntica a `Intra`, preservando la uniformidad.
2.  **En la capa no lineal:** La S-box $\chi'$ se aplica horizontalmente. Al tener diferencias uniformes en la fila, la misma diferencia se inyecta en cada S-box. El resultado tras la capa de S-boxes sigue siendo uniforme por filas.
3.  **Vulnerabilidad:** Sin la constante de ronda $\iota$, esta diferencia uniforme se propagaría con probabilidad 1 a través de la capa lineal en cada ronda, evitando cualquier difusión entre columnas.
4.  **Mitigación:** La inyección de la constante de ronda $\iota$ en la lane $(0,0)$ es el único elemento asimétrico que rompe esta uniformidad. Sin embargo, al perturbar solo una lane, el efecto de ruptura se propaga lentamente, dejando un residuo de simetría en las primeras rondas.

---

## Propuesta de Siguiente Paso

- **Sugerencia de avance:** Habiendo completado con éxito la caracterización del piloto (Fase 0), la matriz formal a escala reducida (Fase 1B/2), el análisis comparativo de S-boxes (Fase 3) y la verificación formal de la vulnerabilidad V3 (Fase 4), sugiero proceder a la **FASE 5 — Redacción del paper (estructura IEEE)**, acotando honestamente los experimentos a $z=1$ en el texto y documentando la limitación de CBC como hallazgo científico.
