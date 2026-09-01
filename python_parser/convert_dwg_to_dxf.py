"""Conversión batch DWG -> DXF con ODA File Converter (Open Design Alliance).

Uso:
    python convert_dwg_to_dxf.py <carpeta_dwg> <carpeta_dxf_salida> [version]

Ejemplo:
    python convert_dwg_to_dxf.py "../DWG/2017_67" "cad_files/dxf/2017_67" ACAD2018

Versiones aceptadas (parámetro "version"): ACAD9..ACAD2018, ACAD2019, etc.
El ejecutable se busca en "C:\\Program Files\\ODA\\ODAFileConverter <ver>\\"
o en la variable de entorno ODA_FILE_CONVERTER.
"""

import glob
import os
import subprocess
import sys


def find_converter():
    env = os.environ.get("ODA_FILE_CONVERTER")
    if env and os.path.isfile(env):
        return env
    base = r"C:\Program Files\ODA"
    if os.path.isdir(base):
        matches = sorted(glob.glob(os.path.join(base, "ODAFileConverter*", "ODAFileConverter.exe")))
        if matches:
            return matches[-1]
    raise SystemExit(
        "No se encontró ODAFileConverter.exe. Instálalo (winget install ODA.ODAFileConverter) "
        "o define la variable ODA_FILE_CONVERTER."
    )


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    folder_in = sys.argv[1]
    folder_out = sys.argv[2]
    version = sys.argv[3] if len(sys.argv) > 3 else "ACAD2018"
    if not os.path.isdir(folder_in):
        raise SystemExit(f"No existe la carpeta de entrada: {folder_in}")
    os.makedirs(folder_out, exist_ok=True)
    exe = find_converter()
    cmd = [exe, folder_in, folder_out, version, "DXF", "0", "0", "*.DWG"]
    print("Ejecutando:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=os.path.dirname(exe))
    if proc.returncode != 0:
        raise SystemExit(f"ODAFileConverter finalizó con código {proc.returncode}")
    dxfs = glob.glob(os.path.join(folder_out, "*.dxf"))
    print(f"Conversión terminada: {len(dxfs)} DXF en {folder_out}")


if __name__ == "__main__":
    main()