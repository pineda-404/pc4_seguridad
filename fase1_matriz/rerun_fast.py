import subprocess
import sys
import os

def main():
    base_dir = "/home/pineda/Downloads/Seguridad_Final/PAPER_IEEE/fase1_matriz"
    script = "/home/pineda/Downloads/Seguridad_Final/PAPER_IEEE/fase0_piloto/keccak_milp_ligero.py"

    # 1. Rounds=1, z=1, limit=180s
    cmd_r1 = [
        sys.executable, script,
        "--rounds", "1",
        "--bits", "1",
        "--time_limit", "180",
        "--gap_rel", "0.0",
        "--log_path", os.path.join(base_dir, "logs/resultados_ligero_r1_z1.log")
    ]
    subprocess.run(cmd_r1)

    # 2. Rounds=2, z=1, limit=180s
    cmd_r2 = [
        sys.executable, script,
        "--rounds", "2",
        "--bits", "1",
        "--time_limit", "180",
        "--gap_rel", "0.0",
        "--log_path", os.path.join(base_dir, "logs/resultados_ligero_r2_z1.log")
    ]
    subprocess.run(cmd_r2)

    print("Rerun completed successfully!")

if __name__ == '__main__':
    main()
