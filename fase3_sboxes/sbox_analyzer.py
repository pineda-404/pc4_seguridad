import numpy as np

def fast_mobius_transform(tt):
    """
    Computes the ANF coefficients of a Boolean function using the Fast Mobius Transform.
    tt: a 1D numpy array of size 2^n containing the truth table (binary values).
    """
    anf = np.copy(tt)
    n = int(np.log2(len(tt)))
    for i in range(n):
        step = 1 << i
        for j in range(0, len(tt), 2 * step):
            for k in range(step):
                anf[j + step + k] ^= anf[j + k]
    return anf

def get_algebraic_degree(anf):
    """
    Gets the algebraic degree of a Boolean function from its ANF coefficients.
    anf: a 1D numpy array of size 2^n containing the ANF coefficients.
    """
    n = int(np.log2(len(anf)))
    max_deg = 0
    for i in range(len(anf)):
        if anf[i] == 1:
            # Count the number of set bits in binary representation of i
            deg = bin(i).count('1')
            if deg > max_deg:
                max_deg = deg
    return max_deg

def compute_sbox_properties(name, bits, lut_fn):
    size = 1 << bits
    lut = [lut_fn(x) for x in range(size)]

    # Check biyective
    is_biyective = (len(set(lut)) == size)

    # Compute DDT
    ddt = np.zeros((size, size), dtype=int)
    for delta_in in range(size):
        for x in range(size):
            delta_out = lut[x] ^ lut[x ^ delta_in]
            ddt[delta_in, delta_out] += 1

    # Max diff probability
    max_entry = 0
    for i in range(1, size): # skip zero input difference
        for j in range(size):
            if ddt[i, j] > max_entry:
                max_entry = ddt[i, j]
    p_max = max_entry / size

    # Compute algebraic degree
    # For each coordinate function (bit of the output)
    coordinate_degrees = []
    for bit in range(bits):
        tt = np.zeros(size, dtype=int)
        for x in range(size):
            tt[x] = (lut[x] >> bit) & 1
        anf = fast_mobius_transform(tt)
        deg = get_algebraic_degree(anf)
        coordinate_degrees.append(deg)
    alg_degree = max(coordinate_degrees)

    return {
        "Nombre": name,
        "Ancho (bits)": bits,
        "Biyectiva": "Sí" if is_biyective else "No",
        "DDT máx entry": max_entry,
        "p_max": f"{p_max} (2^{{{int(np.log2(p_max))}}})",
        "Grado algebraico": alg_degree
    }

# LUT functions
def keccak_chi_lut(x):
    # 5-bit S-box of Keccak Chi
    # Input is 5 bits: x0, x1, x2, x3, x4
    bits = [(x >> i) & 1 for i in range(5)]
    out = [0]*5
    for i in range(5):
        out[i] = bits[i] ^ ((1 ^ bits[(i+1)%5]) & bits[(i+2)%5])
    val = 0
    for i in range(5):
        val |= (out[i] << i)
    return val

ASCON_LUT = [
    4, 11, 31, 20, 26, 21, 9, 2, 27, 5, 8, 18, 29, 3, 6, 28,
    30, 19, 7, 14, 0, 13, 17, 24, 16, 12, 1, 25, 22, 10, 15, 23
]
def ascon_lut_fn(x):
    return ASCON_LUT[x]

PRESENT_LUT = [12, 5, 6, 11, 9, 0, 10, 13, 3, 14, 15, 8, 4, 7, 1, 2]
def present_lut_fn(x):
    return PRESENT_LUT[x]

GIFT_LUT = [1, 10, 4, 12, 6, 15, 3, 9, 2, 13, 11, 7, 14, 0, 5, 8]
def gift_lut_fn(x):
    return GIFT_LUT[x]

def main():
    print("=" * 80)
    print("ANALIZADOR DE S-BOXES (FASE 3)")
    print("=" * 80)

    results = []
    results.append(compute_sbox_properties("Keccak \chi", 5, keccak_chi_lut))
    results.append(compute_sbox_properties("ASCON \chi'", 5, ascon_lut_fn))
    results.append(compute_sbox_properties("PRESENT", 4, present_lut_fn))
    results.append(compute_sbox_properties("GIFT", 4, gift_lut_fn))

    # Add gate count estimates manually from standard literature
    gate_counts = {
        "Keccak \chi": "5 NOT, 5 AND, 5 XOR (Profundidad AND: 1)",
        "ASCON \chi'": "6 NOT, 5 AND, 11 XOR (Profundidad AND: 1)",
        "PRESENT": "3 NOT, 3 AND, 4 XOR, 3 OR (Profundidad AND: 2)",
        "GIFT": "3 NOT, 2 AND, 4 XOR, 1 OR, 1 NAND, 1 NOR (Profundidad AND: 2)"
    }
    
    sources = {
        "Keccak \chi": "Keccak Reference, NIST",
        "ASCON \chi'": "ASCON Spec, NIST LWC",
        "PRESENT": "PRESENT Paper, CHES 2007",
        "GIFT": "GIFT Paper, CHES 2017"
    }

    print("| S-box | Ancho (bits) | Biyectiva | DDT Máx Entry | p_max | Grado Alg. | Compuertas Estimadas | Fuente |")
    print("|---|---|---|---|---|---|---|---|")
    for r in results:
        name = r["Nombre"]
        print(f"| {name} | {r['Ancho (bits)']} | {r['Biyectiva']} | {r['DDT máx entry']} | {r['p_max']} | {r['Grado algebraico']} | {gate_counts[name]} | {sources[name]} |")
    print("=" * 80)

if __name__ == "__main__":
    main()
