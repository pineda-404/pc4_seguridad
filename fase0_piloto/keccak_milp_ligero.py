#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modelo MILP para la variante propuesta: Σ''_ligero (solo paridad de columna) + ASCON S-box (χ').
"""

import sys
import time
import math
import csv
import json
import argparse
import os
import pulp

# G1: Assert that LpSolutionOptimal exists
assert hasattr(pulp, 'LpSolutionOptimal'), "Version de PuLP inesperada, verificar API"

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--bits", type=int, default=1)
    parser.add_argument("--time_limit", type=int, default=120)
    parser.add_argument("--gap_rel", type=float, default=0.0)
    parser.add_argument("--log_path", type=str, default="logs/default.log")
    parser.add_argument("--solver", type=str, default="cbc")
    return parser.parse_args()

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
    prob += t <= b
    prob += t + a <= 1
    prob += t - b + a >= 0

def add_or(prob, inputs, output):
    if len(inputs) == 0:
        prob += output == 0
        return
    for inp in inputs:
        prob += output >= inp
    prob += output <= sum(inputs)

def build_ligero(prob, S, rounds, lanes, bits, new_temp_var):
    """Modelo Σ''_ligero + ASCON S-box."""
    rotation_offsets = [
        [0,  36,  3, 41, 18],
        [1,  44, 10, 45,  2],
        [62,  6, 43, 15, 61],
        [28, 55, 25, 21, 56],
        [27, 20, 39,  8, 14],
    ]

    Intra   = {}
    P       = {}
    SigmaOut = {}
    A_pre  = {}
    T_and  = {}
    Chi_input  = {}
    Chi_active = {}

    for r in range(rounds):
        for x in range(lanes):
            for z in range(bits):
                P[(r, x, z)] = pulp.LpVariable("P_{}_{}_{}".format(r, x, z), cat="Binary")
                for y in range(lanes):
                    Intra[(r, x, y, z)] = pulp.LpVariable("Intra_{}_{}_{}_{}".format(r, x, y, z), cat="Binary")
                    SigmaOut[(r, x, y, z)] = pulp.LpVariable("SigOut_{}_{}_{}_{}".format(r, x, y, z), cat="Binary")
                    Chi_input[(r, x, y, z)] = pulp.LpVariable("ChiIn_{}_{}_{}_{}".format(r, x, y, z), cat="Binary")

        for y in range(lanes):
            for z in range(bits):
                Chi_active[(r, y, z)] = pulp.LpVariable("Chi_active_{}_{}_{}".format(r, y, z), cat="Binary")
                for i in range(lanes):
                    A_pre[(r, i, y, z)]   = pulp.LpVariable("Apre_{}_{}_{}_{}".format(r, i, y, z), cat="Binary")
                    T_and[(r, i, y, z)]   = pulp.LpVariable("Tand_{}_{}_{}_{}".format(r, i, y, z), cat="Binary")

    nvars_extra = len(Intra) + len(P) + len(SigmaOut) + len(Chi_input) + len(Chi_active) + len(A_pre) + len(T_and)
    print("  Variables intermedias (Σ''_ligero): {}".format(nvars_extra))

    for r in range(rounds):
        print("  [Ronda {}] Construyendo Σ''_ligero + rho + pi + chi' (ASCON) …".format(r))

        # Sigma''_ligero Parte A: Intra-lane
        for x in range(lanes):
            for y in range(lanes):
                for z in range(bits):
                    inp0 = S[(r, x, y, z)]
                    inp1 = S[(r, x, y, (z + 1) % bits)]
                    inp3 = S[(r, x, y, (z + 3) % bits)]
                    add_xor_n(prob, [inp0, inp1, inp3], Intra[(r, x, y, z)], new_temp_var)

        # Sigma''_ligero Parte B: Paridad de columnas (P[x], sin Q[y])
        for x in range(lanes):
            for z in range(bits):
                col_inputs = [S[(r, x, y, z)] for y in range(lanes)]
                add_xor_n(prob, col_inputs, P[(r, x, z)], new_temp_var)

        # Sigma''_ligero Parte C: Combinación final (Intra[x,y] ⊕ P[x])
        for x in range(lanes):
            for y in range(lanes):
                for z in range(bits):
                    add_xor(prob, Intra[(r, x, y, z)], P[(r, x, z)], SigmaOut[(r, x, y, z)])

        # Rho + Pi
        for x in range(lanes):
            for y in range(lanes):
                x_prime = (x + 3 * y) % lanes
                y_prime = y
                shift = rotation_offsets[x][y] % bits
                for z in range(bits):
                    z_prime = (z - shift) % bits
                    prob += Chi_input[(r, x_prime, y_prime, z)] == SigmaOut[(r, x, y, z_prime)]

        # S-box ASCON (bit-sliced)
        for y_lane in range(lanes):
            for z in range(bits):
                x_in = [Chi_input[(r, i, y_lane, z)] for i in range(lanes)]

                # Pre-mix
                add_xor(prob, x_in[0], x_in[4], A_pre[(r, 0, y_lane, z)])
                prob += A_pre[(r, 1, y_lane, z)] == x_in[1]
                add_xor(prob, x_in[2], x_in[1], A_pre[(r, 2, y_lane, z)])
                prob += A_pre[(r, 3, y_lane, z)] == x_in[3]
                add_xor(prob, x_in[4], x_in[3], A_pre[(r, 4, y_lane, z)])

                # NOT-AND
                for i in range(lanes):
                    add_not_and(prob, A_pre[(r, i, y_lane, z)], A_pre[(r, (i + 1) % lanes, y_lane, z)], T_and[(r, i, y_lane, z)])

                # Post-mix y salida
                add_xor_n(prob, [A_pre[(r, 0, y_lane, z)], T_and[(r, 1, y_lane, z)], A_pre[(r, 4, y_lane, z)], T_and[(r, 0, y_lane, z)]], S[(r + 1, 0, y_lane, z)], new_temp_var)
                add_xor_n(prob, [A_pre[(r, 1, y_lane, z)], T_and[(r, 2, y_lane, z)], A_pre[(r, 0, y_lane, z)], T_and[(r, 1, y_lane, z)]], S[(r + 1, 1, y_lane, z)], new_temp_var)
                add_xor(prob, A_pre[(r, 2, y_lane, z)], T_and[(r, 3, y_lane, z)], S[(r + 1, 2, y_lane, z)])
                add_xor_n(prob, [A_pre[(r, 3, y_lane, z)], T_and[(r, 4, y_lane, z)], A_pre[(r, 2, y_lane, z)], T_and[(r, 3, y_lane, z)]], S[(r + 1, 3, y_lane, z)], new_temp_var)
                add_xor(prob, A_pre[(r, 4, y_lane, z)], T_and[(r, 0, y_lane, z)], S[(r + 1, 4, y_lane, z)])

                # Actividad S-box
                input_bits = [Chi_input[(r, i, y_lane, z)] for i in range(lanes)]
                add_or(prob, input_bits, Chi_active[(r, y_lane, z)])

    return Chi_active

def main():
    args = parse_args()
    rounds = args.rounds
    bits = args.bits
    time_limit = args.time_limit
    gap_rel = args.gap_rel
    log_path = args.log_path
    lanes = 5

    # Ensure logs dir exists
    log_dir = os.path.dirname(log_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    print("=" * 70)
    print("MODELO MILP PARA KECCAK — VARIANTE: SIGMA_LIGERO")
    print("  lanes={}, rounds={}, bits(z)={}".format(lanes, rounds, bits))
    print("=" * 70)
    print("  S-boxes/ronda: {} (lanes × bits)".format(lanes * bits))
    print("  Solver:        {}".format(args.solver))
    print("  Tiempo límite: {} s".format(time_limit))
    print("  Gap de búsqueda: {}".format(gap_rel))
    print("  Log del solver: {}".format(log_path))
    print("=" * 70)

    prob = pulp.LpProblem("Keccak_MILP_Ligero", pulp.LpMinimize)

    # Variables de estado
    S = {}
    for r in range(rounds + 1):
        for x in range(lanes):
            for y in range(lanes):
                for z in range(bits):
                    S[(r, x, y, z)] = pulp.LpVariable("S_{}_{}_{}_{}".format(r, x, y, z), cat="Binary")

    print("  Variables de estado S: {}".format(len(S)))

    temp_counter = [0]
    XOR_temp = {}

    def new_temp_var():
        temp_counter[0] += 1
        v = pulp.LpVariable("XOR_tmp_{}".format(temp_counter[0]), cat="Binary")
        XOR_temp[temp_counter[0]] = v
        return v

    # Restricción de no-trivialidad
    initial_vars = [S[(0, x, y, z)] for x in range(lanes) for y in range(lanes) for z in range(bits)]
    prob += sum(initial_vars) >= 1, "noTrivialEntrada"

    final_vars = [S[(rounds, x, y, z)] for x in range(lanes) for y in range(lanes) for z in range(bits)]
    prob += sum(final_vars) >= 1, "noTrivialSalida"

    # Construir restricciones
    Chi_active = build_ligero(prob, S, rounds, lanes, bits, new_temp_var)

    total_vars = len(S) + len(XOR_temp)
    total_constraints = len(prob.constraints)
    print("\n  Variables totales (PuLP): {}".format(total_vars))
    print("  Restricciones totales:   {}".format(total_constraints))

    # Objetivo
    objetivo_vars = [Chi_active[(r, y, z)] for r in range(rounds) for y in range(lanes) for z in range(bits)]
    prob += sum(objetivo_vars)

    # Resolver con logPath de manera explícita
    print("\n>>> Resolviendo con {} …".format(args.solver.upper()))
    
    t0 = time.time()
    if args.solver.lower() == "cbc":
        solver = pulp.PULP_CBC_CMD(msg=True, timeLimit=time_limit, gapRel=gap_rel, logPath=log_path)
    elif args.solver.lower() == "gurobi":
        solver = pulp.GUROBI_CMD(msg=True, timeLimit=time_limit, logPath=log_path)
    else:
        solver = pulp.PULP_CBC_CMD(msg=True, timeLimit=time_limit, gapRel=gap_rel, logPath=log_path)

    prob.solve(solver)
    elapsed = time.time() - t0

    # G1/G2 Check
    es_optimo = (prob.sol_status == pulp.LpSolutionOptimal)
    status_str = pulp.LpStatus[prob.status]
    n_valor = pulp.value(prob.objective)

    n_reportado = round(n_valor) if (n_valor is not None and es_optimo) else None
    cota = round(n_valor) if (n_valor is not None and not es_optimo) else None

    print("\n" + "=" * 70)
    print("RESULTADOS")
    print("=" * 70)
    print("  Estado solver:   {}".format(status_str))
    print("  SolStatus crudo: {}".format(prob.sol_status))
    print("  Tiempo:          {:.2f} s".format(elapsed))
    print("  S-boxes activas: {}".format(n_reportado))
    print("  Cota superior:   {}".format(cota))
    print("=" * 70)

    detalle_por_ronda = []
    if es_optimo:
        for r_idx in range(rounds):
            count = 0
            for y in range(lanes):
                for z_idx in range(bits):
                    val = pulp.value(Chi_active[(r_idx, y, z_idx)])
                    if val is not None and val > 0.5:
                        count += 1
            detalle_por_ronda.append(count)
    else:
        detalle_por_ronda = None

    p_sbox = 0.25
    n_final = n_reportado if es_optimo else cota
    prob_total = (p_sbox ** n_final) if n_final is not None else None
    pares_necesarios = (1.0 / prob_total) if prob_total else None
    log2_pares = math.log2(pares_necesarios) if pares_necesarios and pares_necesarios > 0 else None

    resultado = {
        "z":                    bits,
        "rounds":               rounds,
        "sol_status_raw":       str(prob.sol_status),
        "status_raw":           str(prob.status),
        "es_optimo_certificado": es_optimo,
        "n_certificado":        n_reportado,
        "cota_no_certificada":  cota,
        "tiempo_segundos":      round(elapsed, 4),
        "num_variables":        total_vars,
        "num_restricciones":    total_constraints,
        "detalle_por_ronda":    detalle_por_ronda,
        "p_total":              prob_total,
        "log2_pares":           log2_pares,
    }

    base_name = "resultados_ligero_r{}_z{}".format(rounds, bits)
    out_path = os.path.join(os.path.dirname(log_path), base_name)

    with open(out_path + ".json", "w") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    print("  → {}".format(out_path + ".json"))

    with open(out_path + ".csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(resultado.keys())
        writer.writerow(resultado.values())
    print("  → {}".format(out_path + ".csv"))

if __name__ == "__main__":
    main()
