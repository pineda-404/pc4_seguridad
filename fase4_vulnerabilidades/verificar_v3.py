import numpy as np

def build_linear_matrix_proposal(z=1):
    # State size: 5 * 5 * z
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

    # We want to find the output bit as a linear combination of input bits.
    # Chi_input[x_prime, y_prime, z_out] = SigmaOut[x, y, z_prime]
    # where x_prime = (x + 3*y)%5, y_prime = y, z_prime = (z_out - shift)%z
    # And SigmaOut[x, y, z_prime] = Intra[x, y, z_prime] ^ P[x, z_prime]
    # where Intra[x, y, z_prime] = S[x, y, z_prime] ^ S[x, y, (z_prime + 1)%z] ^ S[x, y, (z_prime + 3)%z]
    # and P[x, z_prime] = sum_{y_idx=0..4} S[x, y_idx, z_prime]
    
    for x in range(5):
        for y in range(5):
            x_prime = (x + 3 * y) % 5
            y_prime = y
            shift = rotation_offsets[x][y] % z
            
            for z_out in range(z):
                z_prime = (z_out - shift) % z
                idx_out = get_index(x_prime, y_prime, z_out)
                
                # SigmaOut[x, y, z_prime] consists of:
                # 1. Intra[x, y, z_prime]
                idx_in0 = get_index(x, y, z_prime)
                idx_in1 = get_index(x, y, (z_prime + 1) % z)
                idx_in3 = get_index(x, y, (z_prime + 3) % z)
                
                M[idx_out, idx_in0] ^= 1
                M[idx_out, idx_in1] ^= 1
                M[idx_out, idx_in3] ^= 1
                
                # 2. P[x, z_prime]
                for y_idx in range(5):
                    idx_p = get_index(x, y_idx, z_prime)
                    M[idx_out, idx_p] ^= 1
                    
    return M

def build_linear_matrix_baseline(z=1):
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

    # Baseline: B[x, y, z_out] = S[x, y, z_out] ^ D[x, z_out]
    # where D[x, z_out] = C[(x-1)%5, z_out] ^ C[(x+1)%5, (z_out-1)%z]
    # and C[x, z_out] = sum_{y_idx=0..4} S[x, y_idx, z_out]
    # Then Chi_input[x_prime, y_prime, z_out] = B[x, y, z_prime]
    # where x_prime = (x + 3*y)%5, y_prime = y, z_prime = (z_out - shift)%z
    
    for x in range(5):
        for y in range(5):
            x_prime = (x + 3 * y) % 5
            y_prime = y
            shift = rotation_offsets[x][y] % z
            
            for z_out in range(z):
                z_prime = (z_out - shift) % z
                idx_out = get_index(x_prime, y_prime, z_out)
                
                # B[x, y, z_prime] = S[x, y, z_prime] ^ D[x, z_prime]
                # S[x, y, z_prime]
                idx_s = get_index(x, y, z_prime)
                M[idx_out, idx_s] ^= 1
                
                # D[x, z_prime] = C[(x-1)%5, z_prime] ^ C[(x+1)%5, (z_prime-1)%z]
                # C[(x-1)%5, z_prime]
                x_minus = (x - 1) % 5
                for y_idx in range(5):
                    M[idx_out, get_index(x_minus, y_idx, z_prime)] ^= 1
                    
                # C[(x+1)%5, (z_prime-1)%z]
                x_plus = (x + 1) % 5
                z_prev = (z_prime - 1) % z
                for y_idx in range(5):
                    M[idx_out, get_index(x_plus, y_idx, z_prev)] ^= 1
                    
    return M

def gf2_rank(A):
    """Computes the rank of a binary matrix A over GF(2)."""
    A_copy = np.copy(A) % 2
    r, c = A_copy.shape
    rank = 0
    for i in range(c):
        # Find pivot
        pivot = -1
        for j in range(rank, r):
            if A_copy[j, i] == 1:
                pivot = j
                break
        if pivot != -1:
            # Swap rows
            A_copy[[rank, pivot]] = A_copy[[pivot, rank]]
            # Eliminate below and above
            for j in range(r):
                if j != rank and A_copy[j, i] == 1:
                    A_copy[j] = (A_copy[j] ^ A_copy[rank]) % 2
            rank += 1
    return rank

def find_gf2_kernel(A):
    """Finds a basis for the nullspace (kernel) of a binary matrix A over GF(2)."""
    # A is mxn. We want to find x such that Ax = 0.
    A_copy = np.copy(A) % 2
    r, c = A_copy.shape
    # Bring to row echelon form
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

def main():
    print("=" * 80)
    print("VERIFICADOR DE VULNERABILIDAD V3 — ANÁLISIS DE AUTOVECTORES SOBRE GF(2)")
    print("=" * 80)
    
    # 1. Baseline z=1
    M_b = build_linear_matrix_baseline(z=1)
    # Check eigenvectors (eigenvalue 1) -> nullspace of M_b ^ I
    I = np.eye(25, dtype=int)
    A_b = (M_b ^ I) % 2
    kernel_b = find_gf2_kernel(A_b)
    print(f"Baseline (z=1): dimensión del kernel (M_b ^ I) = {len(kernel_b)}")
    
    # 2. Proposal z=1
    M_p = build_linear_matrix_proposal(z=1)
    A_p = (M_p ^ I) % 2
    kernel_p = find_gf2_kernel(A_p)
    print(f"Propuesta Σ''_ligero (z=1): dimensión del kernel (M_p ^ I) = {len(kernel_p)}")
    
    if len(kernel_p) > 0:
        print("\n¡Autovectores encontrados en la propuesta! Ejemplos:")
        for idx, v in enumerate(kernel_p[:3]):
            print(f"  v_{idx}: {v.tolist()}")
            # Let's interpret the state
            # A 25-bit vector, reshaped to 5x5
            state_2d = v.reshape((5, 5))
            print(f"  Representación 5x5:\n{state_2d}")
            # Check row/column sums
            col_sums = np.sum(state_2d, axis=0) % 2
            row_sums = np.sum(state_2d, axis=1) % 2
            print(f"    Suma de columnas: {col_sums}")
            print(f"    Suma de filas:    {row_sums}")
            
    print("=" * 80)

if __name__ == '__main__':
    main()
