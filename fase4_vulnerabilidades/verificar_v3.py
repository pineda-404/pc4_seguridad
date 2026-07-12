#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificación formal de la vulnerabilidad V3 — Análisis de autovectores sobre GF(2).

CORRECCIONES RESPECTO A VERSIÓN ANTERIOR:
  C3a. Orientación fila/columna corregida: la función get_index(x, y, zz) = (x*5+y)*z+zz
       indexa el estado como state[x][y]. Por tanto, al hacer v.reshape((5,5)), la
       dimensión 0 es x y la dimensión 1 es y. Para verificar P[x] (paridad de columna
       = XOR de todas las lanes en una misma columna x) se necesita sum sobre y → axis=1.
  C3b. Se analizan autovectores del baseline (dim=5) para reconciliar la paradoja:
       si dim_baseline > dim_propuesta, el argumento "propuesta más vulnerable" necesita
       justificación adicional o se reporta como hipótesis descartada.
"""

import numpy as np

# ============================================================
# Construcción de matrices lineales
# ============================================================

def build_linear_matrix_proposal(z=1):
    """
    Construye la matriz de transformación lineal para Σ''_ligero + ρ/π sobre GF(2).
    La S-box χ' (ASCON) es NO lineal y no entra en esta matriz — esta es solo la
    parte lineal (θ-ligero + ρ/π) que actúa antes de χ'.
    
    Indexado: get_index(x, y, zz) = (x*5 + y)*z + zz
    → La matriz M tiene shape (25z, 25z).
    → Al hacer v.reshape((5,5)) con z=1, M[row][col] = M[x_out][y_out].
    """
    n = 25 * z
    M = np.zeros((n, n), dtype=int)

    rotation_offsets = [
        [0,  36,  3, 41, 18],
        [1,  44, 10, 45,  2],
        [62,  6, 43, 15, 61],
        [28, 55, 25, 21, 56],
        [27, 20, 39,  8, 14],
    ]

    def get_index(x, y, zz):
        return (x * 5 + y) * z + zz

    for x in range(5):
        for y in range(5):
            x_prime = (x + 3 * y) % 5
            y_prime = y
            shift = rotation_offsets[x][y] % z

            for z_out in range(z):
                z_prime = (z_out - shift) % z
                idx_out = get_index(x_prime, y_prime, z_out)

                # Intra-lane: S[x,y,z'] ⊕ S[x,y,(z'+1)%z] ⊕ S[x,y,(z'+3)%z]
                idx_in0 = get_index(x, y, z_prime)
                idx_in1 = get_index(x, y, (z_prime + 1) % z)
                idx_in3 = get_index(x, y, (z_prime + 3) % z)
                M[idx_out, idx_in0] ^= 1
                M[idx_out, idx_in1] ^= 1
                M[idx_out, idx_in3] ^= 1

                # Paridad de columna P[x, z'] = XOR_{y'=0..4} S[x, y', z']
                for y_idx in range(5):
                    idx_p = get_index(x, y_idx, z_prime)
                    M[idx_out, idx_p] ^= 1

    return M


def build_linear_matrix_baseline(z=1):
    """
    Construye la matriz de transformación lineal para θ estándar de Keccak + ρ/π.
    θ estándar: B[x,y,z'] = S[x,y,z'] ⊕ C[(x-1)%5, z'] ⊕ C[(x+1)%5, (z'-1)%z]
    donde C[x,z'] = XOR_{y=0..4} S[x, y, z'].
    """
    n = 25 * z
    M = np.zeros((n, n), dtype=int)

    rotation_offsets = [
        [0,  36,  3, 41, 18],
        [1,  44, 10, 45,  2],
        [62,  6, 43, 15, 61],
        [28, 55, 25, 21, 56],
        [27, 20, 39,  8, 14],
    ]

    def get_index(x, y, zz):
        return (x * 5 + y) * z + zz

    for x in range(5):
        for y in range(5):
            x_prime = (x + 3 * y) % 5
            y_prime = y
            shift = rotation_offsets[x][y] % z

            for z_out in range(z):
                z_prime = (z_out - shift) % z
                idx_out = get_index(x_prime, y_prime, z_out)

                # S[x, y, z']
                idx_s = get_index(x, y, z_prime)
                M[idx_out, idx_s] ^= 1

                # C[(x-1)%5, z']
                x_minus = (x - 1) % 5
                for y_idx in range(5):
                    M[idx_out, get_index(x_minus, y_idx, z_prime)] ^= 1

                # C[(x+1)%5, (z'-1)%z]
                x_plus = (x + 1) % 5
                z_prev = (z_prime - 1) % z
                for y_idx in range(5):
                    M[idx_out, get_index(x_plus, y_idx, z_prev)] ^= 1

    return M


# ============================================================
# Álgebra lineal sobre GF(2)
# ============================================================

def gf2_rank(A):
    """Computes the rank of a binary matrix A over GF(2)."""
    A_copy = np.copy(A) % 2
    r, c = A_copy.shape
    rank = 0
    for i in range(c):
        pivot = -1
        for j in range(rank, r):
            if A_copy[j, i] == 1:
                pivot = j
                break
        if pivot != -1:
            A_copy[[rank, pivot]] = A_copy[[pivot, rank]]
            for j in range(r):
                if j != rank and A_copy[j, i] == 1:
                    A_copy[j] = (A_copy[j] ^ A_copy[rank]) % 2
            rank += 1
    return rank


def find_gf2_kernel(A):
    """Finds a basis for the nullspace (kernel) of a binary matrix A over GF(2)."""
    A_copy = np.copy(A) % 2
    r, c = A_copy.shape
    rank = 0
    pivot_cols = []
    for i in range(c):
        pivot = -1
        for j in range(rank, r):
            if A_copy[j, i] == 1:
                pivot = j
                break
        if pivot != -1:
            A_copy[[rank, pivot]] = A_copy[[pivot, rank]]
            for j in range(r):
                if j != rank and A_copy[j, i] == 1:
                    A_copy[j] = (A_copy[j] ^ A_copy[rank]) % 2
            pivot_cols.append(i)
            rank += 1

    free_cols = [i for i in range(c) if i not in pivot_cols]
    basis = []
    for f in free_cols:
        v = np.zeros(c, dtype=int)
        v[f] = 1
        for step, p in enumerate(pivot_cols):
            v[p] = A_copy[step, f]
        basis.append(v)
    return basis


# ============================================================
# Análisis de autovectores con orientación corregida
# ============================================================

def analizar_autovector(v, label, z=1):
    """
    Analiza un autovector dado e imprime su estructura.
    
    CORRECCIÓN C3a: el índice es (x*5+y)*z+zz, por lo que al hacer reshape((5,5))
    el array resultante tiene shape [x_index][y_index].
    
    Verificaciones:
    - P[x] = XOR de todas las lanes de la columna x = sum_{y} state[x][y] (mod 2)
      → np.sum(state_2d, axis=1) % 2  (suma sobre y, para cada x)
    - Q[y] = XOR de todas las lanes de la fila y = sum_{x} state[x][y] (mod 2)
      → np.sum(state_2d, axis=0) % 2  (suma sobre x, para cada y)
    """
    print(f"\n  {label}:")
    print(f"  Vector plano: {v.tolist()}")
    if z == 1:
        # Con z=1, reshape a 5×5 directo: state_2d[x][y]
        state_2d = v.reshape((5, 5))
        print(f"  Matriz 5×5 (filas = x, columnas = y):\n{state_2d}")

        # C3a CORRECCIÓN: P[x] (paridad de COLUMNA = XOR sobre y para x fijo)
        # axis=1 suma sobre la dimensión y (columnas en la matriz)
        paridad_columna = np.sum(state_2d, axis=1) % 2  # shape (5,) → P[x] para x=0..4
        # Q[y] (paridad de FILA = XOR sobre x para y fijo)
        # axis=0 suma sobre la dimensión x (filas en la matriz)
        paridad_fila    = np.sum(state_2d, axis=0) % 2  # shape (5,) → Q[y] para y=0..4

        print(f"  P[x] (paridad de columna, sum sobre y para cada x): {paridad_columna.tolist()}")
        print(f"  Q[y] (paridad de fila,    sum sobre x para cada y): {paridad_fila.tolist()}")

        # Diagnóstico de estructura
        cols_uniforme = np.all(state_2d == state_2d[:, [0]], axis=1).all()
        filas_uniforme = np.all(state_2d == state_2d[[0], :], axis=0).all()
        print(f"  ¿Todas las y iguales para cada x? (uniforme por columna): {bool(filas_uniforme)}")
        print(f"  ¿Todos los x iguales para cada y? (uniforme por fila):    {bool(cols_uniforme)}")

        # Verificar si P[x]=0 para todo x (condición de que Σ''_ligero actúa como Intra solo)
        if np.all(paridad_columna == 0):
            print(f"  ✓ P[x]=0 para todo x → la paridad de columna se cancela.")
            print(f"    Esto confirma que Σ''_ligero actúa como solo Intra-lane en este autovector.")
            print(f"    Conclusión: el autovector se propaga con la misma probabilidad que Intra.")
        else:
            print(f"  ✗ P[x]≠0 para algún x → la paridad de columna no se cancela en este vector.")
            print(f"    Esto requiere análisis adicional de la propagación diferencial.")


def main():
    print("=" * 80)
    print("VERIFICADOR DE VULNERABILIDAD V3 — ANÁLISIS CORREGIDO")
    print("CORRECCIONES: orientación fila/columna (C3a), análisis baseline (C3b)")
    print("=" * 80)

    print("\n--- NOTA SOBRE EL INDEXADO ---")
    print("get_index(x, y, zz) = (x*5+y)*z+zz")
    print("→ Al hacer v.reshape((5,5)) con z=1: result[x][y]")
    print("→ P[x] (paridad de columna) = sum_y result[x][y] → np.sum(..., axis=1)")
    print("→ Q[y] (paridad de fila)    = sum_x result[x][y] → np.sum(..., axis=0)")

    # -------------------------
    # 1. Baseline z=1
    # -------------------------
    print("\n" + "=" * 80)
    print("BASELINE (Keccak θ estándar + ρ/π), z=1")
    print("=" * 80)
    M_b = build_linear_matrix_baseline(z=1)
    I = np.eye(25, dtype=int)
    A_b = (M_b ^ I) % 2
    kernel_b = find_gf2_kernel(A_b)
    print(f"Dimensión del kernel de (M_b ⊕ I) = {len(kernel_b)}")

    if len(kernel_b) > 0:
        print(f"\nAutovectores del BASELINE (primeros {min(3,len(kernel_b))}):")
        for idx, v in enumerate(kernel_b[:3]):
            analizar_autovector(v, f"v_b_{idx} (Baseline)", z=1)

    # -------------------------
    # 2. Propuesta z=1
    # -------------------------
    print("\n" + "=" * 80)
    print("PROPUESTA (Σ''_ligero + ρ/π), z=1")
    print("=" * 80)
    M_p = build_linear_matrix_proposal(z=1)
    A_p = (M_p ^ I) % 2
    kernel_p = find_gf2_kernel(A_p)
    print(f"Dimensión del kernel de (M_p ⊕ I) = {len(kernel_p)}")

    if len(kernel_p) > 0:
        print(f"\nAutovectores de la PROPUESTA (primeros {min(3,len(kernel_p))}):")
        for idx, v in enumerate(kernel_p[:3]):
            analizar_autovector(v, f"v_p_{idx} (Propuesta)", z=1)

    # -------------------------
    # C3b: Reconciliación de la paradoja
    # -------------------------
    print("\n" + "=" * 80)
    print("ANÁLISIS COMPARATIVO Y RECONCILIACIÓN DE LA PARADOJA (C3b)")
    print("=" * 80)
    print(f"Baseline:  kernel de (M_b ⊕ I) = dim {len(kernel_b)}")
    print(f"Propuesta: kernel de (M_p ⊕ I) = dim {len(kernel_p)}")

    if len(kernel_b) >= len(kernel_p):
        print("\n⚠ PARADOJA DETECTADA:")
        print(f"  El baseline tiene kernel de dimensión {len(kernel_b)} ≥ {len(kernel_p)} (propuesta).")
        print("  Si 'dimensión del kernel > 0' implica vulnerabilidad, el baseline es igual o más")
        print("  vulnerable que la propuesta por esta métrica.")
        print()
        print("  Investigando si los autovectores del baseline son análogos a los de la propuesta...")

        # Verificar si el kernel de la propuesta es un subespacio del kernel del baseline
        if len(kernel_p) > 0 and len(kernel_b) > 0:
            vp0 = kernel_p[0]
            # Verificar si vp0 está en el kernel del baseline
            Mv = (M_b @ vp0) % 2
            en_kernel_baseline = np.all(Mv == vp0)  # M_b * v = v?
            print(f"  ¿El autovector v_p_0 de la propuesta también es autovector del baseline? {en_kernel_baseline}")

        # Verificar estructura de los autovectores del baseline
        print("\n  Estructura de autovectores del baseline:")
        for idx, v in enumerate(kernel_b[:3]):
            state_2d = v.reshape((5, 5))
            paridad_col = np.sum(state_2d, axis=1) % 2
            peso = np.sum(v)
            print(f"  v_b_{idx}: peso Hamming={peso}, P[x]={paridad_col.tolist()}")

        print()
        print("  CONCLUSIÓN sobre V3:")
        print("  ─────────────────────────────────────────────────────────────────")
        print("  La dimensión del kernel de (M ⊕ I) mide autovectores de la capa")
        print("  lineal completa (Σ''_ligero + ρ/π), no solo de Σ''_ligero.")
        print()
        print("  Que el baseline tenga más autovectores que la propuesta significa")
        print("  que la PROPUESTA tiene MENOS simetrías lineales — lo cual es en")
        print("  principio MEJOR para la seguridad diferencial lineal.")
        print()
        print("  El argumento de V3 tal como estaba escrito ('la propuesta tiene")
        print("  autovectores, por tanto es vulnerable') es incompleto: el baseline")
        print("  también tiene autovectores (y más), por lo que la mera existencia")
        print("  de autovectores no distingue a la propuesta como peor.")
        print()
        print("  DIAGNÓSTICO: La hipótesis V3 tal como se formuló (kernel dim=4")
        print("  como evidencia de vulnerabilidad adicional en la propuesta) NO se")
        print("  sostiene sin explicar por qué los autovectores del baseline (dim=5)")
        print("  no son comparablemente explotables.")
        print()
        print("  RECOMENDACIÓN (per Plan Maestro Fase 4, paso 4):")
        print("  Reportar V3 como 'hipótesis explorada y descartada'. Esto es")
        print("  contenido válido para el paper — muestra due diligence.")
        print("  ─────────────────────────────────────────────────────────────────")
    else:
        print(f"\nLa propuesta tiene kernel de mayor dimensión ({len(kernel_p)}) que el baseline ({len(kernel_b)}).")
        print("En este caso el argumento de V3 podría sostenerse — verificar autovectores arriba.")

    # -------------------------
    # Verificación adicional: ¿propagación con p=1?
    # -------------------------
    print("\n" + "=" * 80)
    print("VERIFICACIÓN ADICIONAL: ¿Hay diferenciales de peso 1 en la capa lineal?")
    print("(una diferencia de un solo bit que se preserva bajo la capa lineal)")
    print("=" * 80)
    for label, M in [("Baseline", M_b), ("Propuesta", M_p)]:
        pesos_uno = []
        for i in range(25):
            e = np.zeros(25, dtype=int)
            e[i] = 1
            Me = (M @ e) % 2
            if np.all(Me == e):
                pesos_uno.append(i)
        print(f"  {label}: bits fijos bajo la capa lineal (M*e=e): {pesos_uno}")
        if pesos_uno:
            print(f"    ⚠ Existen {len(pesos_uno)} bits que se preservan exactamente → trayectoria trivial.")
        else:
            print(f"    ✓ Ningún bit individual se preserva exactamente bajo la capa lineal.")

    print("\n" + "=" * 80)
    print("FIN DEL ANÁLISIS")
    print("=" * 80)


if __name__ == '__main__':
    main()
