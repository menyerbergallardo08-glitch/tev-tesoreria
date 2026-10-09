"""
Runner unificado de pruebas y auditoría de cobertura.
Valida el umbral mínimo del 85% sobre services/ y routers/.
"""

import sys
import subprocess
import shutil

# Garantizar salida UTF-8 en consola de Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

MIN_COVERAGE_THRESHOLD = 85


def check_dependencies():
    """Verifica que pytest y pytest-cov estén instalados en el entorno actual."""
    missing = []
    for pkg in ["pytest", "pytest_cov"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg.replace("_", "-"))
    
    if missing:
        print("[!] Faltan dependencias para ejecutar la suite:")
        print(f"    Ejecuta: python -m pip install {' '.join(missing)}")
        sys.exit(1)


def run_test_suite():
    print("=" * 75)
    print(">> INICIANDO AUDITORIA UNIFICADA DE PRUEBAS Y COBERTURA (PYTEST-COV)")
    print(f">> Modulos objetivo: services/ | routers/")
    print(f">> Umbral minimo exigido: {MIN_COVERAGE_THRESHOLD}%")
    print("=" * 75)

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests",
        "--cov=services",
        "--cov=routers",
        "--cov-report=term-missing",
        f"--cov-fail-under={MIN_COVERAGE_THRESHOLD}",
        "-v",
    ]

    result = subprocess.run(cmd)

    print("\n" + "=" * 75)
    if result.returncode == 0:
        print(f"[OK] SUITE COMPLETADA CON EXITO: Pruebas en verde y cobertura >= {MIN_COVERAGE_THRESHOLD}%.")
        print("     Reporte HTML interactivo disponible en: coverage_html/index.html")
        print("=" * 75)
    else:
        print(f"[ERROR] FALLO EN LA VALIDACION:")
        print(f"        - Ocurrio un fallo en uno o mas tests, O")
        print(f"        - La cobertura sobre services/ y routers/ no alcanzo el {MIN_COVERAGE_THRESHOLD}%.")
        print("=" * 75)

    sys.exit(result.returncode)


if __name__ == "__main__":
    check_dependencies()
    run_test_suite()
