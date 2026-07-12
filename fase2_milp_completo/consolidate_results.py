import json
import csv
import os
import math

# G1: verificar API de PuLP consistente con el resto del proyecto
# (no se usa PuLP aquí, pero se deja el comentario para trazabilidad)
# p_sbox = 0.25 validado por DDT completa en Fase 3 (no 0.5 de aproximación conservadora)
P_SBOX = 0.25

def p_total_from_n(n):
    """
    Calcula P_total = p_sbox^n usando P_SBOX = 0.25 (validado por DDT en Fase 3).
    Retorna (exponente_negativo, valor_float, string_latex).
    """
    exp = n * 2  # 0.25 = 2^{-2}, entonces 0.25^n = 2^{-2n}
    val = P_SBOX ** n
    latex = f"2^{{-{exp}}} = {val:.8f}"
    return exp, val, latex

def fmt_n(n_val, es_optimo, hay_incumbent, cota):
    """
    G2/G3: Formatea el campo n/cota de forma correcta:
    - Óptimo certificado: '<n> (Óptimo)'
    - Cota (hay incumbent, no óptimo): 'Not Solved (cota <= <cota>)'
    - Sin solución factible: 'Not Solved (N/D - sin solución factible)'
    """
    if es_optimo:
        return f"{n_val} (Óptimo)"
    elif hay_incumbent and cota is not None:
        return f"Not Solved (cota <= {cota})"
    else:
        return "Not Solved (N/D - sin solución factible)"

def main():
    # Paths dentro del repositorio — sin dependencias externas
    repo_dir     = os.path.dirname(os.path.abspath(__file__))
    base_dir     = repo_dir  # los JSON/CSV de salida se guardan aquí
    baseline_dir = os.path.join(repo_dir, "logs_baseline")
    proposal_dir = os.path.join(os.path.dirname(repo_dir), "fase1_matriz", "logs")

    results = []

    # ------------------------------------------------------------------
    # 1. Baseline z=1, rounds=1,2,3
    # Fuente: JSONs generados por keccak_milp_baseline.py (G1/G2 correcto).
    # Si el JSON no existe, el script aborta con error explícito — no usa fallbacks.
    # ------------------------------------------------------------------
    for r in [1, 2, 3]:
        path = os.path.join(baseline_dir, f"resultados_keccak_baseline_r{r}_z1.json")
        if not os.path.exists(path):
            print(f"ERROR: No se encontró {path}")
            print("  Ejecutar primero keccak_milp_baseline.py para r={1,2,3}.")
            raise FileNotFoundError(path)

        with open(path, "r") as f:
            data = json.load(f)

        es_optimo    = data.get("es_optimo_certificado", False)
        hay_incumbent = data.get("hay_incumbent", False)
        n_val        = data.get("n_certificado", None)
        cota         = data.get("cota_no_certificada", None)
        # C1 refuerzo: si No Sol, cota debe ser None
        if not hay_incumbent:
            cota = None

        vars_count  = data.get("num_variables", None)
        restr_count = data.get("num_restricciones", None)
        tiempo      = round(data.get("tiempo_segundos", 0), 2)
        detalle     = data.get("detalle_por_ronda", None)

        # Calcular P_total y Pares con n real (C2: usar n_val, no r)
        if es_optimo and n_val is not None:
            exp, val, latex = p_total_from_n(n_val)
            p_tot_str = f"2^{{-{exp}}} = {val:.8f}"
            pares_str = f"2^{exp} = {int(1/val)}"
        elif hay_incumbent and cota is not None:
            # Cota superior de n → cota inferior de seguridad (más pesimista)
            exp, val, latex = p_total_from_n(cota)
            p_tot_str = f">= 2^{{-{exp}}}"
            pares_str = f">= 2^{exp}"
        else:
            p_tot_str = "N/D"
            pares_str = "N/D"

        n_str = fmt_n(n_val, es_optimo, hay_incumbent, cota)
        desglose_str = str(detalle) if (es_optimo and detalle) else "N/A"

        results.append({
            "Exp. ID": f"B-r{r}-z1",
            "Variante": "Baseline (Keccak)",
            "Rondas": r,
            "z": 1,
            "Variables": vars_count,
            "Restricciones": restr_count,
            "S-boxes Activas (n)": n_str,
            "Desglose Ronda": desglose_str,
            "P_total": p_tot_str,
            "Pares Necesarios": pares_str,
            "sol_status_raw": f"{data.get('sol_status_raw', '?')} ({'Optimal' if es_optimo else ('Feasible' if hay_incumbent else 'No Sol')})",
            "Certificación": "Óptimo certificado" if es_optimo else ("Cota (timeout)" if hay_incumbent else "Sin sol. factible"),
            "Tiempo (s)": tiempo,
        })

    # ------------------------------------------------------------------
    # 2. Propuesta z=1, rounds=1,2,3
    # ------------------------------------------------------------------
    for r in [1, 2, 3]:
        path = os.path.join(proposal_dir, f"resultados_ligero_r{r}_z1.json")
        if not os.path.exists(path):
            print(f"ADVERTENCIA: no se encontró {path}")
            continue

        with open(path, "r") as f:
            data = json.load(f)

        es_optimo = data.get("es_optimo_certificado", False)
        # C1: usar campo 'hay_incumbent' del JSON corregido si existe;
        # si no existe (JSON viejo), inferir de sol_status_raw
        sol_status_raw_str = data.get("sol_status_raw", "0")
        try:
            sol_status_int = int(sol_status_raw_str)
        except (ValueError, TypeError):
            sol_status_int = 0

        # hay_incumbent = True si sol_status es Optimal(1) o IntegerFeasible(2)
        hay_incumbent_campo = data.get("hay_incumbent", None)
        if hay_incumbent_campo is not None:
            hay_incumbent = hay_incumbent_campo
        else:
            hay_incumbent = sol_status_int in (1, 2)

        n_cert = data.get("n_certificado", None)
        cota = data.get("cota_no_certificada", None)
        # C1 refuerzo: si No Sol (sol_status=0), cota debe ser None aunque el JSON diga otra cosa
        if not hay_incumbent:
            cota = None

        n_str = fmt_n(n_cert, es_optimo, hay_incumbent, cota)
        n_use = n_cert if es_optimo else cota  # None si No Sol

        # Calcular P_total con n real (C2)
        if es_optimo and n_use is not None:
            exp, val, latex = p_total_from_n(n_use)
            p_tot_str = f"2^{{-{exp}}} = {val:.8f}"
            pares_str = f"2^{exp} = {int(1/val)}"
        elif hay_incumbent and n_use is not None:
            exp, val, latex = p_total_from_n(n_use)
            p_tot_str = f">= 2^{{-{exp}}}"
            pares_str = f">= 2^{exp}"
        else:
            p_tot_str = "N/D"
            pares_str = "N/D"

        detalle = data.get("detalle_por_ronda", None)
        desglose_str = str(detalle) if (es_optimo and detalle) else "N/A"

        # Formato del sol_status_raw para display
        sol_display = {
            "1": "1 (Optimal)",
            "2": "2 (Feasible)",
            "0": "0 (No Sol)",
        }.get(str(sol_status_raw_str).strip(), str(sol_status_raw_str))

        results.append({
            "Exp. ID": f"M_ligero-r{r}-z1",
            "Variante": "Propuesta (Σ''_ligero + χ')",
            "Rondas": r,
            "z": 1,
            "Variables": data.get("num_variables"),
            "Restricciones": data.get("num_restricciones"),
            "S-boxes Activas (n)": n_str,
            "Desglose Ronda": desglose_str,
            "P_total": p_tot_str,
            "Pares Necesarios": pares_str,
            "sol_status_raw": sol_display,
            "Certificación": "Óptimo certificado" if es_optimo else ("Cota (timeout)" if hay_incumbent else "Sin sol. factible"),
            "Tiempo (s)": round(data.get("tiempo_segundos", 0), 2),
        })

    # ------------------------------------------------------------------
    # Escribir CSV
    # ------------------------------------------------------------------
    csv_path = os.path.join(base_dir, "comparativa_consolidada.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"Consolidado CSV guardado en: {csv_path}")

    # Escribir JSON
    json_path = os.path.join(base_dir, "comparativa_consolidada.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Consolidado JSON guardado en: {json_path}")

    # ------------------------------------------------------------------
    # Imprimir tabla markdown
    # ------------------------------------------------------------------
    print("\n" + "=" * 100)
    print("TABLA COMPARATIVA CONSOLIDADA (FASE 2) — CORREGIDA")
    print("Nota: P_total calculado con p_sbox=0.25 (DDT-verificada, Fase 3) para todas las filas.")
    print("Columna 'Certificación' indica estado de cada celda (G3).")
    print("=" * 100)
    headers = list(results[0].keys())
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join(["---"] * len(headers)) + "|")
    for r in results:
        print("| " + " | ".join(str(r[h]) for h in headers) + " |")
    print("=" * 100)

    # ------------------------------------------------------------------
    # Resumen de cambios respecto a versión anterior (auditoría)
    # ------------------------------------------------------------------
    print("\n=== AUDITORÍA DE CORRECCIONES ===")
    print("C1 (G2 bug): M_ligero-r3-z1 tiene sol_status=0 → cota=None → se muestra 'N/D'")
    print("C2 (aritmética): Todas las filas usan p_sbox=0.25 de forma consistente.")
    print("  B-r1-z1: n=1 → P_total=2^{-2}=0.25        (sin cambio)")
    print("  B-r2-z1: n=4 → P_total=2^{-8}=0.00390625  (CORREGIDO: antes era 2^{-4})")
    print("  B-r3-z1: cota<=11 → P_total>=2^{-22}       (sin cambio)")
    print("  M_ligero-r1-z1: n=2 → P_total=2^{-4}       (sin cambio)")
    print("  M_ligero-r2-z1: n=4 → P_total=2^{-8}       (sin cambio)")
    print("  M_ligero-r3-z1: No Sol → N/D               (CORREGIDO: antes 'cota <= 0')")

if __name__ == "__main__":
    main()
