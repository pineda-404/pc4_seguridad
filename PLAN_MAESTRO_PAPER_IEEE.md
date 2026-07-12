# Plan Maestro — Paper IEEE: Rediseño Ligero de Keccak (Capa Lineal estilo ASCON) con Verificación Formal MILP

**Rol de cada parte:**
- **Agente de codificación (Antigravity):** ejecuta cada fase exactamente como se especifica, entrega el reporte estandarizado (Sección 6) al final de cada fase, y **se detiene en cada Gate de Decisión** hasta recibir aprobación explícita para continuar.
- **IA supervisora (yo, en esta conversación):** reviso cada entrega, verifico números/lógica, apruebo o rechazo el paso a la siguiente fase, y redacto/reviso el texto final del paper.
- **Regla de oro de todo el proyecto:** ninguna fase avanza a la siguiente sin que su Gate de Decisión haya sido aprobado explícitamente. No hay excepciones por presión de tiempo — si algo no converge, se documenta y se decide la ruta alternativa, no se fuerza.

---

## 1. Contexto condensado (lo que el agente debe saber antes de tocar código)

- **Origen:** Actividad 3 (MILP básico, lanes=5 corregido de 4) → Examen Final "Keccak Modificado" (rediseño con variables dinámicas, Σ'', χ', MILP, vulnerabilidades) → ahora, **Paper IEEE de tema libre**, extendiendo el examen con permiso confirmado del profesor.
- **Lo que ya se demostró en el examen (no repetir, solo referenciar):**
  - `Σ' = intra-lane ⊕ rotr(·,1) ⊕ rotr(·,3)` sola (sin cruce entre filas/columnas) tiene un techo matemático de difusión del 20% — demostrado formalmente (teorema de composición intra-fila) y con simulación.
  - Añadir paridad de columna **y** fila (`Σ''` del examen) arregla la difusión pero cuesta 140z compuertas XOR (2.8× más que θ estándar, 50z) y **es intratable en MILP con CBC**, incluso a z=1, incluso con 30 min y gap 5%.
  - χ' (S-box de ASCON) es afín-equivalente a χ (Keccak): misma DDT máxima (2⁻²), mismo grado algebraico (2), ambas biyectivas. **No es más barata en hardware.**
  - Interacción no explicada: θ+χ' da óptimo n=2 (más débil) vs θ+χ da n=4, con el mismo θ. Pregunta abierta, no extrapolable a Σ''+χ'.
  - Bug crítico de PuLP: `pulp.LpStatus[prob.status] == "Optimal"` da **falsos positivos** cuando CBC para por tiempo con solución factible. Usar siempre `prob.sol_status == pulp.LpSolutionOptimal`.
- **Hipótesis central de ESTE paper (todavía no probada):** `Σ''_ligero = intra-lane + SOLO paridad de columna` (sin paridad de fila) podría ser suficientemente más barato que el `Σ''` del examen como para ser tratable en MILP, a cambio de resolver la vulnerabilidad de difusión solo parcialmente (o de una forma distinta, a verificar).

---

## 2. Principios no negociables (guardrails — aplican a TODAS las fases)

**G1. Verificación de optimalidad correcta, sin excepción.**
Todo script MILP nuevo debe verificar `prob.sol_status == pulp.LpSolutionOptimal`, nunca `pulp.LpStatus[prob.status]` a secas. Incluir este assert al inicio de cada script:
```python
assert hasattr(pulp, 'LpSolutionOptimal'), "Version de PuLP inesperada, verificar API"
```//nolint intencional, mantener como recordatorio en el código, no solo en el reporte.

**G2. Nunca reportar `n=0` ni truncar con `int()` sin verificar el estado.**
Si `sol_status != LpSolutionOptimal`, el valor de `n` se reporta como **cota** (`n ≤ X` si hay solución factible, o `N/D` si no hay ninguna), nunca como si fuera el óptimo. Redondear objetivos casi-enteros con `round()`, no truncar con `int()`.

**G3. No comparar una cota con un óptimo certificado.**
Cualquier tabla comparativa debe marcar explícitamente, por cada celda, si el valor es "Óptimo certificado", "Cota (timeout)" o "Sin solución factible". Una conclusión tipo "A es más costoso que B" **solo es válida si ambos lados de la comparación están certificados como óptimos**.

**G4. No prometer alcance no verificado.**
Cualquier afirmación cuantitativa en el texto del paper (tiempos, número de S-boxes, propiedades de difusión, costo de compuertas) debe tener un archivo de resultado (JSON/CSV/log) que la respalde, referenciado explícitamente. Nada de "se espera que..." en la sección de resultados — eso va en "limitaciones" o "trabajo futuro", claramente etiquetado como no verificado.

**G5. Pilotar antes de comprometerse.**
Ninguna fase que involucre una corrida MILP nueva (config nueva de capa lineal/no lineal) se lanza a escala completa sin antes correr el piloto correspondiente (ver Fase 0) y sin que yo apruebe el Gate de Decisión.

**G6. El agente reporta, no decide el pivote.**
Si un piloto falla (no converge, o converge mal), el agente **reporta los números crudos y se detiene** — no decide por su cuenta seguir insistiendo, ni cambia de diseño sin aprobación.

---

## 3. Fases del proyecto

### FASE 0 — Piloto de tratabilidad (obligatorio, primero que todo)

**Objetivo:** determinar si `Σ''_ligero` (solo paridad de columna) es tratable en MILP, y en qué escala.

**Diseño a implementar:**
```
Σ''_ligero(L[x,y]) = L[x,y] ⊕ rotr(L[x,y],1) ⊕ rotr(L[x,y],3) ⊕ P[x]
donde P[x] = XOR de las 5 lanes de la columna x (paridad de columna, SIN paridad de fila)
```
seguido de ρ/π (simplificado, `x'=(x+3y) mod 5, y'=y`, costo cero — solo wiring) y χ' (S-box de ASCON).

**Corridas exactas a ejecutar (en este orden, deteniéndose si alguna falla gravemente):**

| ID | z | rounds | time_limit | gapRel | Qué decide |
|---|---|---|---|---|---|
| P1 | 1 | 1 | 120s | 0.0 (exacto) | ¿El modelo compila y resuelve el caso trivial? |
| P2 | 1 | 2 | 120s | 0.0 (exacto) | ¿Escala con rondas al mínimo de estado? |
| P3 | 2 | 1 | 180s | 0.0 (exacto) | ¿La simplificación (solo columna) gana tratabilidad real, o solo parece tratable por ser z=1 (caso degenerado de 25 bits)? |

**Importante — por qué P3 usa z=2 y no z=1:** z=1 es el estado más pequeño posible (25 bits totales); cualquier diseño tiende a converger ahí solo por ser trivial, sin que eso demuestre que la simplificación estructural (quitar la paridad de fila) realmente redujo la dificultad del problema. z=2 es el primer punto que permite distinguir "tratable de verdad" de "tratable solo en el caso degenerado".

**Código:** reusar la estructura de `keccak_milp_pulp.py` del proyecto anterior, reemplazando únicamente la construcción de las restricciones de la capa lineal (θ → `Σ''_ligero`). Mantener χ' (ASCON) igual que en el examen. Aplicar G1-G2 desde la primera línea.

**Entregable de Fase 0 (formato exacto en Sección 6):** tabla con las 3 filas (P1, P2, P3), cada una con: tiempo real de resolución, `sol_status` crudo, `n` (o cota, o N/D), número de variables, número de restricciones, y el archivo `.log` crudo de CBC adjunto (no solo el resumen).

**🛑 GATE DE DECISIÓN 0 (yo reviso esto antes de continuar):**
- Si P1, P2 y P3 certifican óptimo → **Rama A** (Fase 1A): proceder con `Σ''_ligero` a escala ampliada.
- Si P1 y P2 certifican pero P3 no → **Rama B** (Fase 1B): el paper se acota honestamente a z=1, se documenta el límite de escalado como hallazgo (no como fracaso).
- Si ni P1 ni P2 certifican en el tiempo dado → **Rama C** (Fase 1C): pivotear la capa lineal a algo genuinamente tratable (candidato: permutación de bits pura estilo PRESENT/GIFT, sin restricciones XOR nuevas para el solver).
- Si el agente detecta cualquier ambigüedad de diseño no cubierta aquí → reporta y espera, no improvisa.

---

### FASE 1A — Ampliación de escala (solo si Gate 0 = Rama A)

Repetir P1-P3 extendiendo la matriz a `z ∈ {1,2,4}` × `rounds ∈ {1,2,3}` (9 corridas), mismo protocolo de `sol_status`, time_limit escalonado (180s para z≤2, 300s para z=4). Reportar igual que Fase 0. Gate de Decisión 1A: aprobar si al menos 6 de 9 certifican óptimo; si no, retroceder a Rama B con lo que sí haya certificado.

### FASE 1B — Acotamiento honesto a z=1 (si Gate 0 = Rama B)

Completar la matriz `z=1 × rounds∈{1,2,3}` únicamente (3 corridas), certificando las que se pueda. El paper declarará explícitamente: *"el diseño propuesto es tratable mediante MILP exacto únicamente en el régimen de estado mínimo (z=1); para z≥2 se reporta como trabajo futuro o se usa una cota no certificada, declarada como tal."* Esto es un resultado legítimo, no un relleno.

### FASE 1C — Pivote de capa lineal (si Gate 0 = Rama C)

No seguir forzando variantes de Σ con paridad cruzada. Evaluar **permutación de bits pura** (sin restricciones XOR densas para el solver) como capa lineal alternativa, inspirada en PRESENT/GIFT en vez de ASCON. Repetir Fase 0 (P1-P3) con este nuevo diseño antes de continuar. Si esto tampoco converge, **detenerse y reportarme** — en ese punto se evalúa seriamente el pivote de tema completo (Opción B, PQC vs. clásico), no como última opción de emergencia sino como decisión informada.

---

### FASE 2 — Matriz MILP formal completa (línea base vs. propuesta)

**Solo se ejecuta tras aprobar Gate 1A o 1B.**

- **Línea base:** reusar exactamente los resultados ya certificados del examen anterior (θ + ρ/π + χ estándar) — no re-correr si ya existen y están certificados con `sol_status` correcto; si no se verificó con `sol_status` en su momento, **re-verificar los logs crudos antes de reusar el número**.
- **Propuesta:** la rama que haya sido aprobada en el Gate 0/1A/1B/1C, a la escala que haya quedado validada.
- Formato de tabla final: exactamente como en el examen (columnas: Exp. ID, rounds, z, variables, restricciones, n, desglose por ronda, P_total, pares necesarios, **`sol_status` crudo**, tiempo).
- **Ninguna celda sin marcar su estado de certificación** (G3).

**Entregable:** CSV/JSON consolidado + tabla en markdown lista para el paper, con nota al pie explícita de qué filas son óptimo certificado vs. cota.

**🛑 GATE DE DECISIÓN 2:** reviso la tabla completa, verifico 2-3 filas al azar contra el log crudo de CBC antes de aprobar.

---

### FASE 3 — Matriz comparativa de S-boxes no lineales (bajo riesgo, independiente del MILP)

**Objetivo:** ampliar la comparación χ vs. χ' con un tercer candidato (PRESENT o GIFT, 4 bits), usando el mismo marco ya validado en el examen (DDT completa, grado algebraico vía ANF/Möbius, biyectividad).

**No requiere resolver MILP — es cálculo directo sobre la tabla de verdad, así que no tiene riesgo de intratabilidad.** Puede ejecutarse en paralelo a la Fase 0/1, no depende de sus resultados.

**Entregable:** tabla con filas = {χ, χ'(ASCON), S-box de PRESENT o GIFT}, columnas = {ancho en bits, biyectiva (sí/no), DDT máxima, grado algebraico, compuertas estimadas (NOT/AND/XOR), fuente de la tabla de verdad citada}.

**🛑 GATE DE DECISIÓN 3:** reviso que los cálculos de DDT/grado algebraico estén hechos con código verificable (no copiados de un paper sin recalcular), igual que se hizo con χ/χ' en el examen.

---

### FASE 4 — Segunda vulnerabilidad (V3), verificación formal obligatoria

**No escribir la V3 candidata (simetría por paridad de columna repetida + ι perturbando una sola lane) sin verificarla matemáticamente primero.**

**Protocolo de verificación exacto:**
1. Formalizar la hipótesis como una propiedad concreta y falsable: ¿existe un par de estados `(S, S')` con `S' = Ronda(S)` tal que la diferencia `S ⊕ S'` sea invariante bajo la ronda completa (subespacio invariante), o tal que dos rondas consecutivas produzcan la misma transformación efectiva (slide)?
2. Implementar una búsqueda/verificación computacional directa (no argumento puramente verbal) — buscar subespacios invariantes de tamaño pequeño por fuerza bruta/álgebra lineal sobre GF(2), dado que la capa lineal es conocida explícitamente.
3. Si se confirma: documentar la vulnerabilidad con la trayectoria/subespacio concreto que la explota, y proponer la corrección (ecuación corregida), igual que exigía el examen.
4. **Si NO se confirma:** no forzarla. Reportarlo como "hipótesis explorada y descartada" (esto también es contenido válido para un paper — mostrar due diligence) y buscar una V3 alternativa con el mismo protocolo de verificación antes de escribir nada.

**🛑 GATE DE DECISIÓN 4:** reviso el código de verificación y los resultados antes de aprobar el texto de la vulnerabilidad para el paper.

---

### FASE 5 — Redacción del paper (estructura IEEE)

Solo empieza cuando Fases 2, 3 y 4 estén aprobadas (pueden solaparse en el tiempo, pero el texto final de cada sección espera su Gate correspondiente).

**Estructura propuesta (formato IEEE de doble columna, ~6-8 páginas):**

1. **Abstract** — resumen de la contribución real: modelo MILP formal para evaluar una capa lineal ligera inspirada en ASCON, con hallazgos honestos sobre tratabilidad computacional y trade-offs de costo/difusión. (Redactar al final, cuando se sepa qué rama del Gate 0 quedó.)
2. **Introducción** — motivación (Keccak/SHA-3, MILP de Mouha et al., lightweight crypto), contribución explícita del paper (en viñetas).
3. **Trabajo relacionado** — Keccak/SHA-3 (Bertoni et al.), Mouha et al. (MILP para S-boxes activas), ASCON (Dobraunig et al., NIST LWC), PRESENT/GIFT si aplica.
4. **Diseño propuesto** — variables dinámicas (de Sección 2 del examen, resumidas), `Σ''_ligero`, χ' (ASCON), justificación de cada decisión con referencia a lo ya demostrado (branch number invariante a rotaciones, afín-equivalencia de χ').
5. **Modelo MILP** — formulación completa (variables, restricciones, linealización), metodología de verificación (`sol_status`, G1-G3 explicados como parte del rigor metodológico del paper — esto es honestamente un punto fuerte a destacar, no un detalle a esconder).
6. **Resultados** — tabla de Fase 2 (línea base vs. propuesta), tabla de Fase 3 (comparación de S-boxes), avalanche test (resultado honesto: mismo número de rondas que línea base para ≥80% difusión, reencuadrado como costo×rondas).
7. **Análisis de seguridad** — V1, V2, V3 (de Fase 4), con ecuaciones corregidas.
8. **Discusión y limitaciones** — declarar explícitamente el alcance real de z según el Gate 0/1 (ej. "tratable solo a z=1" si terminó en Rama B), la pregunta abierta de θ+χ' (Sección 3.4 del contexto), y cualquier cota no certificada.
9. **Conclusiones y trabajo futuro** — incluir explícitamente qué se necesitaría (ej. Gurobi, u otra familia de S-box) para extender los resultados.

**🛑 GATE DE DECISIÓN 5 (por sección, no todo junto):** reviso cada sección del punto 2 en adelante a medida que se redacta, no al final del documento completo — permite corregir dirección temprano.

---

### FASE 6 — Auditoría final

Antes de considerar el paper listo:
- Re-verificar 100% de las cifras cuantitativas del texto contra sus archivos fuente (JSON/CSV/logs).
- Revisar que ninguna tabla mezcle óptimos certificados con cotas sin marcarlo.
- Revisar que ninguna afirmación de la Sección 6 (Resultados) carezca de archivo de respaldo.
- Verificar formato IEEE (referencias, figuras, numeración).

---

## 4. Especificaciones técnicas para el agente

**Estructura de carpetas sugerida:**
```
/paper_keccak/
  /fase0_piloto/          -> P1.py, P2.py, P3.py, logs/, resultados.json
  /fase1_matriz/          -> segun rama (1A, 1B o 1C), scripts + resultados.json
  /fase2_milp_completo/   -> script final, consolidado.csv, logs/
  /fase3_sboxes/          -> ddt_analysis.py, tabla_sboxes.csv
  /fase4_vulnerabilidades/-> verificacion_v3.py, resultados
  /fase5_paper/           -> paper.tex o .md, figuras/
```

**Formato de script MILP (obligatorio en todas las fases con MILP):**
```python
import pulp

def resolver(z, rounds, time_limit, gap_rel=0.0):
    prob = pulp.LpProblem(...)
    # ... construccion del modelo ...
    solver = pulp.PULP_CBC_CMD(msg=True, timeLimit=time_limit, gapRel=gap_rel)
    prob.solve(solver)

    # G1/G2 obligatorio:
    es_optimo = (prob.sol_status == pulp.LpSolutionOptimal)
    n_valor = pulp.value(prob.objective)
    n_reportado = round(n_valor) if (n_valor is not None and es_optimo) else None
    cota = round(n_valor) if (n_valor is not None and not es_optimo) else None

    return {
        "z": z, "rounds": rounds,
        "sol_status_raw": str(prob.sol_status),
        "status_raw": str(prob.status),
        "es_optimo_certificado": es_optimo,
        "n_certificado": n_reportado,
        "cota_no_certificada": cota,
        "tiempo_segundos": ...,
        "num_variables": ...,
        "num_restricciones": ...,
    }
```

**Nunca eliminar el campo `status_raw` aunque no se use para decidir** — sirve para que yo audite si `sol_status` y `status` divergieron (señal del bug de la Sección 3.2 del contexto).

---

## 5. Checklist de entrega por fase (el agente debe marcar esto en cada reporte)

- [ ] ¿Se usó `sol_status`, no `status`, para determinar optimalidad? (G1)
- [ ] ¿Ninguna celda de resultado reporta `n` sin marcar si es óptimo o cota? (G2, G3)
- [ ] ¿Se adjuntó el log crudo de CBC de cada corrida, no solo el resumen? (auditable)
- [ ] ¿Se corrió exactamente la matriz especificada en esta fase, ni más ni menos, sin adelantarse a la siguiente fase sin Gate aprobado? (G5)
- [ ] ¿Alguna corrida arrojó un resultado inesperado o ambiguo? Si sí, reportarlo explícitamente, no omitirlo.

---

## 6. Plantilla de reporte estándar (una por fase, para que yo audite rápido)

```markdown
### Reporte de Fase [N] — [nombre de fase]

**Corridas ejecutadas:**
| ID | z | rounds | time_limit | sol_status_raw | es_optimo | n / cota | tiempo(s) | vars | restr. |
|---|---|---|---|---|---|---|---|---|---|
| ... |

**Archivos adjuntos:** [lista de rutas a logs .json/.csv/.log]

**Hallazgos inesperados o ambiguos:** [texto libre, o "ninguno"]

**Checklist (Sección 5):** [marcado]

**Propuesta de siguiente paso (el agente sugiere, no decide):** [Rama A/B/C, o "esperar aprobación"]
```

---

## 7. Cronograma tentativo (ajustar según calendario real del curso)

| Semana | Actividad |
|---|---|
| 1 | Fase 0 (piloto) + Fase 3 (S-boxes, en paralelo, bajo riesgo) |
| 1-2 | Gate 0 → Fase 1 (rama que corresponda) |
| 2 | Fase 2 (matriz MILP completa) |
| 2-3 | Fase 4 (vulnerabilidad V3) |
| 3-4 | Fase 5 (redacción, sección por sección con Gate 5) |
| 4 | Fase 6 (auditoría final) + entrega |

**Regla de cronograma:** si a mitad de la Semana 1 el Gate 0 cae en Rama C (pivote de capa lineal) y ese pivote también falla, se activa la discusión de pivote de tema completo (Opción B) — esa decisión se toma en la Semana 1, no se pospone.
