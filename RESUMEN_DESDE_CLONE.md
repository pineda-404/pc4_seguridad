# Resumen de Trabajo y Estado Actual (Desde el Clone de Git)

Este archivo sirve para transferir el contexto completo del trabajo realizado en esta sesión de desarrollo de la permutación Keccak modificada con `Σ''_ligero` y la S-box de ASCON `χ'`.

---

## 🛠️ Trabajo Realizado y Correcciones Aplicadas

Desde que se realizó el clone del repositorio, se auditaron y corrigieron sistemáticamente las Fases 0, 1B, 2, 3 y 4 del proyecto para satisfacer las exigencias de la IA supervisora/correctora.

### 1. Corrección C1: Bug G2 en el Script MILP (`keccak_milp_ligero.py`)
* **Problema:** Cuando el solver CBC no encontraba ninguna solución factible (`sol_status == 0`), el script anterior reportaba de forma incorrecta `cota <= 0` (violando el guardrail G2) debido a que PuLP devolvía `0.0` por defecto en la función objetivo.
* **Solución:** Se implementó una verificación explícita de `hay_incumbent = sol_status in (Optimal, IntegerFeasible)`. Ahora, si no hay un incumbent factible, la cota se reporta correctamente como `N/D` (No Determinado) en los JSONs y en la tabla final.

### 2. Corrección C2: Aritmética y Trazabilidad del Baseline (Fase 2)
* **Script de Baseline:** Se creó el archivo [`keccak_milp_baseline.py`](file:///home/pineda/TuT/trabajo-trabajo/Seguridad_Informatica/PC-04/pc4_seguridad/fase2_milp_completo/keccak_milp_baseline.py) para correr el modelo de Keccak estándar desde cero usando las mismas reglas G1/G2 que la propuesta.
* **Recálculo de Probabilidad ($P_{\text{total}}$):** Se corrigió el cálculo de todas las filas en [`consolidate_results.py`](file:///home/pineda/TuT/trabajo-trabajo/Seguridad_Informatica/PC-04/pc4_seguridad/fase2_milp_completo/consolidate_results.py) usando el valor real de S-boxes activas ($n$) y la probabilidad DDT verificada ($p_{\text{sbox}} = 0.25$).
* **Descubrimiento y Corrección del Óptimo del Baseline ($z=1$):**
  * Al re-correr el baseline de Keccak estándar con $z=1$, el solver certificó optimalidad para **$n=2$ en 2 rondas** (tiempo $5.46$s) y **$n=3$ en 3 rondas** (tiempo $14.85$s).
  * **Explicación Matemática:** A $z=1$ (estado degenerado de 25 bits), los shifts de rotación de $\rho$ son todos nulos (modulo 1). Esto permite que el vector de diferencia de todos unos (`[1, 1, 1, 1, 1]`) en la fila $y=0$ se propague a sí mismo de manera estable en cada ronda (la paridad de columnas $C = [1, 1, 1, 1, 1]$ se anula en la mezcla $\theta \implies D = [0,0,0,0,0]$). En Keccak real ($z=64$), los shifts reales destruyen esta simetría dispersando los bits a diferentes columnas $z$.
  * La discrepancia con la tabla anterior ($n=4$ para 2 rondas) se debe a que los datos originales correspondían a una corrida con $z>1$ o con restricciones de peso de entrada que impedían el vector simétrico.
* Se reescribió [`consolidate_results.py`](file:///home/pineda/TuT/trabajo-trabajo/Seguridad_Informatica/PC-04/pc4_seguridad/fase2_milp_completo/consolidate_results.py) eliminando fallbacks hardcodeados; ahora lee directamente de los JSONs trazables en [`logs_baseline/`](file:///home/pineda/TuT/trabajo-trabajo/Seguridad_Informatica/PC-04/pc4_seguridad/fase2_milp_completo/logs_baseline/).

### 3. Corrección C3: Verificación de Autovectores (Fase 4 - V3)
* **Indexado:** Se corrigió en [`verificar_v3.py`](file:///home/pineda/TuT/trabajo-trabajo/Seguridad_Informatica/PC-04/pc4_seguridad/fase4_vulnerabilidades/verificar_v3.py) el cálculo de la paridad de columnas usando `axis=1` para la matriz reshapeada (orientación fila/columna correcta).
* **Verificación de Subespacio:** Se implementó una verificación exhaustiva en GF(2). Se demostró matemáticamente que los 4 vectores base de la propuesta, junto con sus **15 combinaciones lineales no triviales**, pertenecen al kernel del baseline.
* **Conclusión:** El kernel de la propuesta ($\text{dim } 4$) es un **subespacio propio** del kernel del baseline ($\text{dim } 5$). La propuesta tiene *menos* simetrías lineales que el baseline, por lo que la Hipótesis V3 (vulnerabilidad adicional introducida por la propuesta) queda formalmente **descartada** (se incluirá en el paper como análisis de *due diligence*).

### 4. Corrección C4: Conteo de Compuertas desde la ANF (Fase 3)
* Se modificó [`sbox_analyzer.py`](file:///home/pineda/TuT/trabajo-trabajo/Seguridad_Informatica/PC-04/pc4_seguridad/fase3_sboxes/sbox_analyzer.py) agregando la función `estimate_gates_from_anf` usando la *Fast Mobius Transform* para calcular los coeficientes de la Forma Normal Algebraica (ANF).
* Se verificó que las cotas superiores naive derivadas de la ANF son consistentes y superiores a las compuertas optimizadas (factorizadas) reportadas por la literatura para Keccak, ASCON, PRESENT y GIFT.

---

## 📈 Estado Actual

* **Situación:** Estamos esperando la respuesta final del corrector (IA supervisora) para obtener la aprobación del Gate 2 y poder pasar a la **Fase 5 (Redacción del Paper)**.
* **Archivos modificados y subidos al repositorio local:**
  * [`fase0_piloto/keccak_milp_ligero.py`](file:///home/pineda/TuT/trabajo-trabajo/Seguridad_Informatica/PC-04/pc4_seguridad/fase0_piloto/keccak_milp_ligero.py) (Fix C1 / G2 bug)
  * [`fase2_milp_completo/keccak_milp_baseline.py`](file:///home/pineda/TuT/trabajo-trabajo/Seguridad_Informatica/PC-04/pc4_seguridad/fase2_milp_completo/keccak_milp_baseline.py) (Trazabilidad del baseline)
  * [`fase2_milp_completo/consolidate_results.py`](file:///home/pineda/TuT/trabajo-trabajo/Seguridad_Informatica/PC-04/pc4_seguridad/fase2_milp_completo/consolidate_results.py) (Lectura directa sin fallbacks)
  * [`fase3_sboxes/sbox_analyzer.py`](file:///home/pineda/TuT/trabajo-trabajo/Seguridad_Informatica/PC-04/pc4_seguridad/fase3_sboxes/sbox_analyzer.py) (Conteo ANF de compuertas)
  * [`fase4_vulnerabilidades/verificar_v3.py`](file:///home/pineda/TuT/trabajo-trabajo/Seguridad_Informatica/PC-04/pc4_seguridad/fase4_vulnerabilidades/verificar_v3.py) (Verificación exhaustiva de subespacio)
  * [`REPORTES_FASES.md`](file:///home/pineda/TuT/trabajo-trabajo/Seguridad_Informatica/PC-04/pc4_seguridad/REPORTES_FASES.md) (Reporte de fases v3 consolidado)

---

## 📝 Último Envío a Revisión (Pendiente de Aprobación)

Lo último que le enviamos al corrector para su revisión final y cierre de la Fase 2 consiste en:
1. **El código completo de `keccak_milp_baseline.py`:** Pegado directamente como texto para auditoría, demostrando que no hay trucos ni restricciones de peso ocultas.
2. **El log crudo de CBC para la corrida $r=2, z=1$ (`baseline_r2_z1.log`):** Pegado como texto en la conversación para auditar que el solver certificó optimalidad matemática con $n=2$ de manera transparente.
3. **La explicación analítica del trail degenerado de todos unos (`31 -> 31`) a $z=1$:** Explicando por qué $n=2$ y $n=3$ son los óptimos matemáticos reales en este modelo, resolviendo de raíz la discrepancia con el valor histórico de $n=4$.
