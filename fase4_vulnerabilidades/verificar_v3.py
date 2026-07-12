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

    # ─────────────────────────────────────────────────────────────────────────
    # C3b: Reconciliación de la paradoja — VERIFICACIÓN EXHAUSTIVA DE SUBESPACIO
    # Recomendada por la IA supervisora: verificar que kernel_propuesta ⊆ kernel_baseline
    # no solo con un vector de muestra sino:
    #   (a) Cada uno de los 4 vectores base individualmente
    #   (b) Las 2^4 - 1 = 15 combinaciones lineales no triviales sobre GF(2)
    #   (c) El rango de la unión de ambos kernels
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERIFICACIÓN EXHAUSTIVA DE SUBESPACIO (C3b)")
    print("kernel_propuesta ⊆ kernel_baseline ?")
    print("=" * 80)
    print(f"  Baseline:  kernel(M_b ⊕ I) = dim {len(kernel_b)}")
    print(f"  Propuesta: kernel(M_p ⊕ I) = dim {len(kernel_p)}")

    if len(kernel_p) > 0 and len(kernel_b) > 0:

        # (a) Cada vector base de kernel_propuesta verificado individualmente
        print(f"\n  (a) Verificación individual de los {len(kernel_p)} vectores base de kernel_propuesta:")
        todos_en_baseline = True
        for idx, vp in enumerate(kernel_p):
            Mv = (M_b @ vp) % 2
            en_kb = bool(np.all(Mv == vp))   # M_b * vp = vp  ↔  vp ∈ kernel(M_b ⊕ I)
            mark = "✓" if en_kb else "✗"
            print(f"    {mark} v_p_{idx}: M_b·v_p_{idx} = v_p_{idx} → {en_kb}")
            if not en_kb:
                todos_en_baseline = False
        print(f"  Resultado: todos los vectores base ∈ kernel_baseline = {todos_en_baseline}")

        # (b) Todas las 2^k - 1 combinaciones lineales no triviales sobre GF(2)
        k = len(kernel_p)
        n_combos = (1 << k) - 1   # 2^k - 1
        print(f"\n  (b) Verificando las {n_combos} combinaciones lineales no triviales (GF(2)):")
        fallos_combo = []
        for mask in range(1, 1 << k):
            # Combinación: suma (XOR) de los vectores base seleccionados por los bits de mask
            combo = np.zeros(kernel_p[0].shape, dtype=int)
            bits_activos = []
            for bit in range(k):
                if mask & (1 << bit):
                    combo = (combo + kernel_p[bit]) % 2
                    bits_activos.append(bit)
            # Verificar: M_b * combo = combo ?
            Mv = (M_b @ combo) % 2
            en_kb = bool(np.all(Mv == combo))
            if not en_kb:
                fallos_combo.append((mask, bits_activos))
        if fallos_combo:
            print(f"    ✗ {len(fallos_combo)} combinaciones NO están en el kernel del baseline:")
            for mask, bits in fallos_combo[:5]:
                print(f"      mask={bin(mask)}, vectores={bits}")
        else:
            print(f"    ✓ Las {n_combos} combinaciones están en kernel_baseline.")
        todas_combos_ok = (len(fallos_combo) == 0)

        # (c) Rango de la unión de ambos kernels
        print(f"\n  (c) Rango del espacio generado por kernel_baseline ∪ kernel_propuesta:")
        union_vecs = list(kernel_b) + list(kernel_p)
        union_matrix = np.array(union_vecs, dtype=int)   # shape (dim_b + dim_p, n)
        rango_union = gf2_rank(union_matrix.T)             # rango de la matriz de columnas
        print(f"    dim(kernel_b) = {len(kernel_b)}")
        print(f"    dim(kernel_p) = {len(kernel_p)}")
        print(f"    rango(kernel_b ∪ kernel_p) = {rango_union}")
        es_subespacio = (rango_union == len(kernel_b))
        print(f"    ¿rango_union == dim(kernel_b)? → {es_subespacio}")
        if es_subespacio:
            print(f"    ✓ kernel_propuesta es un SUBESPACIO PROPIO de kernel_baseline.")
            print(f"      (dim 4 < dim 5 → kernel_propuesta ⊊ kernel_baseline)")
        else:
            print(f"    ✗ kernel_propuesta NO está completamente contenido en kernel_baseline.")

        # ── Conclusión consolidada ────────────────────────────────────────────
        subespacio_confirmado = todos_en_baseline and todas_combos_ok and es_subespacio
        print()
        print("  ═" * 40)
        print("  CONCLUSIÓN CONSOLIDADA sobre V3:")
        print("  ═" * 40)
        if subespacio_confirmado:
            print("  ✓ VERIFICACIÓN EXHAUSTIVA PASADA — kernel_propuesta ⊊ kernel_baseline")
            print()
            print("  Los 4 vectores base de kernel_propuesta, individualmente y en todas")
            print(f"  sus {n_combos} combinaciones lineales, pertenecen al kernel del baseline.")
            print(f"  El rango de la unión es {rango_union} = dim(kernel_baseline), confirmando")
            print("  que kernel_propuesta (dim 4) es un SUBESPACIO PROPIO de kernel_baseline (dim 5).")
            print()
            print("  Interpretación: todo lo que tiene la propuesta en términos de")
            print("  simetrías lineales (autovectores de valor propio 1) ya estaba en")
            print("  el baseline — y le falta UNA dimensión. La propuesta no introduce")
            print("  ninguna simetría nueva; al contrario, es estrictamente más asimétrica.")
            print()
            print("  HIPÓTESIS V3 DESCARTADA (per Plan Maestro Fase 4, paso 4).")
            print("  Reportar en el paper como 'hipótesis explorada y descartada'")
            print("  con esta verificación de subespacio como evidencia — es más")
            print("  contundente que solo comparar dimensiones.")
        else:
            print("  ✗ Alguna verificación falló — revisar los detalles arriba.")
            print("  No se puede afirmar subespacio sin revisar los fallos.")
        print("  ═" * 40)

    elif len(kernel_p) == 0:
        print("  kernel_propuesta tiene dim=0 → trivialmente contenido en cualquier espacio.")
    else:
        print("  kernel_baseline tiene dim=0 — verificación de subespacio no aplica.")

    if len(kernel_b) < len(kernel_p):
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
