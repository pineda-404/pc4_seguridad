import subprocess
import sys
import json
import os

def run_cmd(cmd):
    print("Ejecutando:", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print("ERR:", res.stderr)

def main():
    base_dir = "/home/pineda/Downloads/Seguridad_Final/PAPER_IEEE/fase0_piloto"
    script = os.path.join(base_dir, "keccak_milp_ligero.py")

    # Ensure logs directory exists
    os.makedirs(os.path.join(base_dir, "logs"), exist_ok=True)

    print("======================================================================")
    print("CORRIENDO FASE 0 — PILOTO DE TRATABILIDAD")
    print("======================================================================")

    # P1: rounds=1, z=1, limit=120s
    p1_cmd = [
        sys.executable, script,
        "--rounds", "1",
        "--bits", "1",
        "--time_limit", "120",
        "--gap_rel", "0.0",
        "--log_path", os.path.join(base_dir, "logs/P1.log")
    ]
    run_cmd(p1_cmd)

    # P2: rounds=2, z=1, limit=120s
    p2_cmd = [
        sys.executable, script,
        "--rounds", "2",
        "--bits", "1",
        "--time_limit", "120",
        "--gap_rel", "0.0",
        "--log_path", os.path.join(base_dir, "logs/P2.log")
    ]
    run_cmd(p2_cmd)

    # P3: rounds=1, z=2, limit=180s
    p3_cmd = [
        sys.executable, script,
        "--rounds", "1",
        "--bits", "2",
        "--time_limit", "180",
        "--gap_rel", "0.0",
        "--log_path", os.path.join(base_dir, "logs/P3.log")
    ]
    run_cmd(p3_cmd)

    # Read and output the summary table
    print("\n" + "=" * 80)
    print("RESUMEN FASE 0")
    print("=" * 80)

    rows = []
    for pid, r, z, tl in [("P1", 1, 1, 120), ("P2", 2, 1, 120), ("P3", 1, 2, 180)]:
        json_path = os.path.join(base_dir, f"logs/resultados_ligero_r{r}_z{z}.json")
        if os.path.exists(json_path):
            with open(json_path, "r") as f:
                data = json.load(f)
            es_optimo = data.get("es_optimo_certificado")
            n = data.get("n_certificado")
            cota = data.get("cota_no_certificada")
            
            n_cota_str = f"{n} (Óptimo)" if es_optimo else (f"cota <= {cota}" if cota is not None else "N/D")
            
            rows.append({
                "ID": pid,
                "z": z,
                "rounds": r,
                "time_limit": tl,
                "sol_status_raw": data.get("sol_status_raw"),
                "es_optimo": "Sí" if es_optimo else "No",
                "n_cota": n_cota_str,
                "tiempo": data.get("tiempo_segundos"),
                "vars": data.get("num_variables"),
                "restr": data.get("num_restricciones")
            })
        else:
            rows.append({
                "ID": pid, "z": z, "rounds": r, "time_limit": tl,
                "sol_status_raw": "N/D", "es_optimo": "N/D", "n_cota": "N/D",
                "tiempo": "N/D", "vars": "N/D", "restr": "N/D"
            })

    # Print markdown table
    print("| ID | z | rounds | time_limit | sol_status_raw | es_optimo | n / cota | tiempo(s) | vars | restr. |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['ID']} | {r['z']} | {r['rounds']} | {r['time_limit']} | {r['sol_status_raw']} | {r['es_optimo']} | {r['n_cota']} | {r['tiempo']} | {r['vars']} | {r['restr']} |")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
