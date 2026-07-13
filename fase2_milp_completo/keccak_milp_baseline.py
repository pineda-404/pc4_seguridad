#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modelo MILP para el Baseline: Keccak estándar (θ + ρ/π + χ).
Usa exactamente el mismo patrón G1/G2 que keccak_milp_ligero.py.

Propósito: generar los archivos JSON/log trazables del baseline para
que consolidate_results.py no dependa de JSONs externos ni de fallbacks
hardcodeados — cierra el hueco de trazabilidad señalado en la auditoría.
"""

import sys
import time
import math
import csv
import json
import argparse
import os
import pulp

# G1: Assert que la API de PuLP tiene LpSolutionOptimal
assert hasattr(pulp, 'LpSolutionOptimal'), "Version de PuLP inesperada, verificar API"

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds",     type=int,   default=1)
    parser.add_argument("--bits",       type=int,   default=1)
    parser.add_argument("--time_limit", type=int,   default=120)
    parser.add_argument("--gap_rel",    type=float, default=0.0)
    parser.add_argument("--log_path",   type=str,   default="logs_baseline/default.log")
    parser.add_argument("--solver",     type=str,   default="cbc")
    return parser.parse_args()

# ─── Primitivas MILP ──────────────────────────────────────────────────────────

def add_xor(prob, a, b, c):
    prob += c <= a + b
    prob += a <= b + c
    prob += b <= a + c
    prob += a + b + c <= 2

def add_xor_n(prob, inputs, output, new_temp_var_fn):
    if len(inputs) == 0:
        prob += output == 0
        return
    current = inputs[0]
    for i in range(1, len(inputs)):
        temp = new_temp_var_fn()
        add_xor(prob, current, inputs[i], temp)
        current = temp
    prob += output == current

def add_not_and(prob, a, b, t):
    """t <= a + b (Correct differential model for AND gate)"""
    prob += t <= a + b

def add_or(prob, inputs, output):
    if len(inputs) == 0:
        prob += output == 0
        return
    for inp in inputs:
        prob += output >= inp
    prob += output <= sum(inputs)

# ─── Construcción del modelo Keccak baseline ──────────────────────────────────

def build_baseline(prob, S, rounds, lanes, bits, new_temp_var):
    """
    Modelo MILP para Keccak estándar: θ + ρ/π + χ.

    θ estándar:
      C[x, z]    = XOR_{y=0..4} S[x, y, z]
      D[x, z]    = C[(x-1)%5, z] ⊕ C[(x+1)%5, (z-1)%z]
      B[x, y, z] = S[x, y, z] ⊕ D[x, z]

    ρ/π:
      Chi_input[(x+3y)%5, y, z_out] = B[x, y, (z_out - shift) % z]

    χ estándar (Keccak):
      out[i] = in[i] ⊕ ((~in[(i+1)%5]) & in[(i+2)%5])
    """
    rotation_offsets = [
        [0,  36,  3, 41, 18],
        [1,  44, 10, 45,  2],
        [62,  6, 43, 15, 61],
        [28, 55, 25, 21, 56],
        [27, 20, 39,  8, 14],
    ]

    C         = {}   # paridad de columna
    D         = {}   # mezcla de columnas vecinas
    Theta_out = {}   # salida de θ
    Chi_input = {}   # entrada a χ (después de ρ/π)
    T_and     = {}   # NOT-AND de χ
    Chi_active = {}  # actividad de S-box

    for r in range(rounds):
        # Crear variables
        for x in range(lanes):
            for z in range(bits):
                C[(r, x, z)] = pulp.LpVariable(f"C_{r}_{x}_{z}", cat="Binary")
                D[(r, x, z)] = pulp.LpVariable(f"D_{r}_{x}_{z}", cat="Binary")
                for y in range(lanes):
                    Theta_out[(r, x, y, z)] = pulp.LpVariable(f"Theta_{r}_{x}_{y}_{z}", cat="Binary")
                    Chi_input[(r, x, y, z)] = pulp.LpVariable(f"ChiIn_{r}_{x}_{y}_{z}", cat="Binary")
                    T_and[(r, x, y, z)]     = pulp.LpVariable(f"Tand_{r}_{x}_{y}_{z}",  cat="Binary")

        for y in range(lanes):
            for z in range(bits):
                Chi_active[(r, y, z)] = pulp.LpVariable(f"Chi_active_{r}_{y}_{z}", cat="Binary")

    print(f"  Variables intermedias (baseline): "
          f"{len(C)+len(D)+len(Theta_out)+len(Chi_input)+len(T_and)+len(Chi_active)}")

    for r in range(rounds):
        print(f"  [Ronda {r}] Construyendo θ + ρ/π + χ (baseline) …")

        # ── θ Parte A: paridad de columna C[x, z] ────────────────────────────
        for x in range(lanes):
            for z in range(bits):
                col = [S[(r, x, y, z)] for y in range(lanes)]
                add_xor_n(prob, col, C[(r, x, z)], new_temp_var)

        # ── θ Parte B: mezcla de columnas D[x, z] ────────────────────────────
        for x in range(lanes):
            for z in range(bits):
                # D[x,z] = C[(x-1)%5, z] ⊕ C[(x+1)%5, (z-1)%z]
                c_left  = C[(r, (x - 1) % lanes, z)]
                c_right = C[(r, (x + 1) % lanes, (z - 1) % bits)]
                add_xor(prob, c_left, c_right, D[(r, x, z)])

        # ── θ Parte C: Theta_out[x,y,z] = S[x,y,z] ⊕ D[x,z] ────────────────
        for x in range(lanes):
            for y in range(lanes):
                for z in range(bits):
                    add_xor(prob, S[(r, x, y, z)], D[(r, x, z)], Theta_out[(r, x, y, z)])

        # ── ρ + π ─────────────────────────────────────────────────────────────
        for x in range(lanes):
            for y in range(lanes):
                x_prime = (x + 3 * y) % lanes
                y_prime = y
                shift   = rotation_offsets[x][y] % bits
                for z in range(bits):
                    z_prime = (z - shift) % bits
                    prob += Chi_input[(r, x_prime, y_prime, z)] == Theta_out[(r, x, y, z_prime)]

        # ── χ estándar ────────────────────────────────────────────────────────
        for y_lane in range(lanes):
            for z in range(bits):
                x_in = [Chi_input[(r, i, y_lane, z)] for i in range(lanes)]

                # T_and[i] = (~x_in[(i+1)%5]) & x_in[(i+2)%5]
                for i in range(lanes):
                    add_not_and(prob,
                                x_in[(i + 1) % lanes],
                                x_in[(i + 2) % lanes],
                                T_and[(r, i, y_lane, z)])

                # S[r+1, i, y, z] = x_in[i] ⊕ T_and[i]
                for i in range(lanes):
                    add_xor(prob, x_in[i], T_and[(r, i, y_lane, z)], S[(r + 1, i, y_lane, z)])

                # Actividad de S-box: OR de los bits de entrada
                add_or(prob, x_in, Chi_active[(r, y_lane, z)])

    return Chi_active

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    args       = parse_args()
    rounds     = args.rounds
    bits       = args.bits
    time_limit = args.time_limit
    gap_rel    = args.gap_rel
    log_path   = args.log_path
    lanes      = 5

    log_dir = os.path.dirname(log_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    print("=" * 70)
    print("MODELO MILP PARA KECCAK — VARIANTE: BASELINE (θ + ρ/π + χ)")
    print(f"  lanes={lanes}, rounds={rounds}, bits(z)={bits}")
    print("=" * 70)
    print(f"  S-boxes/ronda: {lanes * bits} (lanes × bits)")
    print(f"  Solver:        {args.solver}")
    print(f"  Tiempo límite: {time_limit} s")
    print(f"  Gap:           {gap_rel}")
    print(f"  Log del solver: {log_path}")
    print("=" * 70)

    prob = pulp.LpProblem("Keccak_MILP_Baseline", pulp.LpMinimize)

    # Variables de estado
    S = {}
    for r in range(rounds + 1):
        for x in range(lanes):
            for y in range(lanes):
                for z in range(bits):
                    S[(r, x, y, z)] = pulp.LpVariable(f"S_{r}_{x}_{y}_{z}", cat="Binary")

    print(f"  Variables de estado S: {len(S)}")

    temp_counter = [0]
    XOR_temp = {}

    def new_temp_var():
        temp_counter[0] += 1
        v = pulp.LpVariable(f"XOR_tmp_{temp_counter[0]}", cat="Binary")
        XOR_temp[temp_counter[0]] = v
        return v

    # No-trivialidad
    initial_vars = [S[(0, x, y, z)] for x in range(lanes) for y in range(lanes) for z in range(bits)]
    prob += sum(initial_vars) >= 1, "noTrivialEntrada"
    final_vars   = [S[(rounds, x, y, z)] for x in range(lanes) for y in range(lanes) for z in range(bits)]
    prob += sum(final_vars)   >= 1, "noTrivialSalida"

    Chi_active = build_baseline(prob, S, rounds, lanes, bits, new_temp_var)

    total_vars        = len(S) + len(XOR_temp)
    total_constraints = len(prob.constraints)
    print(f"\n  Variables totales (PuLP): {total_vars}")
    print(f"  Restricciones totales:   {total_constraints}")

    # Objetivo: minimizar S-boxes activas
    objetivo_vars = [Chi_active[(r, y, z)]
                     for r in range(rounds)
                     for y in range(lanes)
                     for z in range(bits)]
    prob += sum(objetivo_vars)

    print(f"\n>>> Resolviendo con {args.solver.upper()} …")
    t0 = time.time()
    if args.solver.lower() == "cbc":
        solver = pulp.PULP_CBC_CMD(msg=True, timeLimit=time_limit, gapRel=gap_rel, logPath=log_path)
    else:
        solver = pulp.PULP_CBC_CMD(msg=True, timeLimit=time_limit, gapRel=gap_rel, logPath=log_path)
    prob.solve(solver)
    elapsed = time.time() - t0

    # ─── G1/G2: verificación correcta de optimalidad y cota ──────────────────
    # sol_status == LpSolutionOptimal(=1) : óptimo certificado
    # sol_status == LpSolutionIntegerFeasible(=2): incumbent, no óptimo → cota válida
    # sol_status == 0 (No Sol): sin incumbent → sin cota → N/D
    es_optimo    = (prob.sol_status == pulp.LpSolutionOptimal)
    hay_incumbent = (prob.sol_status in (pulp.LpSolutionOptimal, pulp.LpSolutionIntegerFeasible))
    status_str   = pulp.LpStatus[prob.status]
    n_valor      = pulp.value(prob.objective)

    n_reportado = round(n_valor) if (n_valor is not None and es_optimo)                             else None
    cota        = round(n_valor) if (n_valor is not None and hay_incumbent and not es_optimo) else None

    print("\n" + "=" * 70)
    print("RESULTADOS (BASELINE)")
    print("=" * 70)
    print(f"  Estado solver:   {status_str}")
    print(f"  SolStatus crudo: {prob.sol_status}")
    print(f"  Tiempo:          {elapsed:.2f} s")
    if es_optimo:
        print(f"  S-boxes activas (ÓPTIMO CERTIFICADO): {n_reportado}")
    elif hay_incumbent:
        print(f"  S-boxes activas (COTA, no certificada): <= {cota}")
    else:
        print("  S-boxes activas: N/D (sin solución factible encontrada)")
    print("=" * 70)

    # Desglose por ronda
    detalle_por_ronda = []
    if es_optimo:
        for r_idx in range(rounds):
            count = sum(
                1 for y in range(lanes) for z in range(bits)
                if (val := pulp.value(Chi_active[(r_idx, y, z)])) is not None and val > 0.5
            )
            detalle_por_ronda.append(count)
    else:
        detalle_por_ronda = None

    # P_total con p_sbox = 0.25 (DDT-verificada en Fase 3)
    p_sbox     = 0.25
    n_final    = n_reportado if es_optimo else cota  # None si No Sol
    prob_total = (p_sbox ** n_final) if n_final is not None else None
    log2_pares = math.log2(1.0 / prob_total) if prob_total else None

    resultado = {
        "variante":              "Baseline (Keccak θ + ρ/π + χ)",
        "z":                     bits,
        "rounds":                rounds,
        "sol_status_raw":        str(prob.sol_status),
        "status_raw":            str(prob.status),        # campo de auditoría: nunca eliminar
        "es_optimo_certificado": es_optimo,
        "hay_incumbent":         hay_incumbent,
        "n_certificado":         n_reportado,
        "cota_no_certificada":   cota,                    # None cuando No Sol
        "tiempo_segundos":       round(elapsed, 4),
        "num_variables":         total_vars,
        "num_restricciones":     total_constraints,
        "detalle_por_ronda":     detalle_por_ronda,
        "p_sbox":                p_sbox,
        "p_total":               prob_total,
        "log2_pares":            log2_pares,
    }

    base_name = f"resultados_keccak_baseline_r{rounds}_z{bits}"
    out_path  = os.path.join(os.path.dirname(log_path), base_name)

    with open(out_path + ".json", "w") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    print(f"  → {out_path}.json")

    with open(out_path + ".csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(resultado.keys())
        writer.writerow(resultado.values())
    print(f"  → {out_path}.csv")

if __name__ == "__main__":
    main()
