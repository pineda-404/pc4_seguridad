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
    base_dir = "/home/pineda/Downloads/Seguridad_Final/PAPER_IEEE/fase1_matriz"
    script = "/home/pineda/Downloads/Seguridad_Final/PAPER_IEEE/fase0_piloto/keccak_milp_ligero.py"

    # Ensure logs directory exists
    os.makedirs(os.path.join(base_dir, "logs"), exist_ok=True)

    print("======================================================================")
    print("EJECUTANDO FASE 1B — MATRIZ Z=1 × RONDAS={1,2,3}")
    print("======================================================================")

    # We already have rounds=1, z=1 and rounds=2, z=1 from Fase 0, but let's re-run them
    # in the fase1_matriz folder to have a clean, self-contained set of results.
    
    # 1. Rounds=1, z=1, limit=180s
    cmd_r1 = [
        sys.executable, script,
        "--rounds", "1",
        "--bits", "1",
        "--time_limit", "180",
        "--gap_rel", "0.0",
        "--log_path", os.path.join(base_dir, "logs/resultados_ligero_r1_z1.log")
    ]
    run_cmd(cmd_r1)

    # 2. Rounds=2, z=1, limit=180s
    cmd_r2 = [
        sys.executable, script,
        "--rounds", "2",
        "--bits", "1",
        "--time_limit", "180",
        "--gap_rel", "0.0",
        "--log_path", os.path.join(base_dir, "logs/resultados_ligero_r2_z1.log")
    ]
    run_cmd(cmd_r2)

    # 3. Rounds=3, z=1, limit=180s
    cmd_r3 = [
        sys.executable, script,
        "--rounds", "3",
        "--bits", "1",
        "--time_limit", "180",
        "--gap_rel", "0.0",
        "--log_path", os.path.join(base_dir, "logs/resultados_ligero_r3_z1.log")
    ]
    run_cmd(cmd_r3)

    # Print summary table
    print("\n" + "=" * 80)
    print("RESUMEN FASE 1B (z=1)")
    print("=" * 80)

    rows = []
    for r in [1, 2, 3]:
        json_path = os.path.join(base_dir, f"logs/resultados_ligero_r{r}_z1.json")
        if os.path.exists(json_path):
            with open(json_path, "r") as f:
                data = json.load(f)
            es_optimo = data.get("es_optimo_certificado")
            n = data.get("n_certificado")
            cota = data.get("cota_no_certificada")
            
            n_cota_str = f"{n} (Óptimo)" if es_optimo else (f"cota <= {cota}" if cota is not None else "N/D")
            
            rows.append({
                "rounds": r,
                "sol_status_raw": data.get("sol_status_raw"),
                "es_optimo": "Sí" if es_optimo else "No",
                "n_cota": n_cota_str,
                "tiempo": data.get("tiempo_segundos"),
                "vars": data.get("num_variables"),
                "restr": data.get("num_restricciones")
            })
        else:
            rows.append({
                "rounds": r,
                "sol_status_raw": "N/D", "es_optimo": "N/D", "n_cota": "N/D",
                "tiempo": "N/D", "vars": "N/D", "restr": "N/D"
            })

    # Print markdown table
    print("| Rondas (r) | z | sol_status_raw | es_optimo | n / cota | tiempo(s) | vars | restr. |")
    print("|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['rounds']} | 1 | {r['sol_status_raw']} | {r['es_optimo']} | {r['n_cota']} | {r['tiempo']} | {r['vars']} | {r['restr']} |")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
