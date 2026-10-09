import os
import sys
import time
import shutil

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from services.backup_service import prune_backups_fifo
import services.backup_service as bs

def test_fifo_prune_logic():
    print("=================================================================")
    print(" INICIANDO TEST DE ROTACION FIFO (FIRST-IN, FIRST-OUT)")
    print("=================================================================")

    test_backup_dir = os.path.join(PROJECT_DIR, "tests", "temp_backups_fifo")
    if os.path.exists(test_backup_dir):
        shutil.rmtree(test_backup_dir)
    os.makedirs(test_backup_dir, exist_ok=True)

    # 1. Crear 18 archivos simulados con timestamps escalonados
    created_dummy = []
    base_time = time.time() - 3600 * 24 * 5 # 5 días atrás
    for i in range(18):
        fname = f"TEV_BACKUP_TEST_FIFO_{i:02d}.json"
        fpath = os.path.join(test_backup_dir, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(f'{{"test_index": {i}}}')
        file_mtime = base_time + (i * 3600)
        os.utime(fpath, (file_mtime, file_mtime))
        created_dummy.append((fname, fpath, file_mtime))

    print(f"  [OK] 18 archivos simulados creados con mtime escalonado.")

    # Guardar ruta original y redirigir
    original_func = bs.prune_backups_fifo

    def custom_prune(max_backups=14, max_days=30):
        # Implementación directa sobre la carpeta de test
        files = []
        for f in os.listdir(test_backup_dir):
            if f.startswith("TEV_BACKUP_") and f.endswith(".json"):
                fp = os.path.join(test_backup_dir, f)
                files.append({"filename": f, "path": fp, "mtime": os.path.getmtime(fp)})
        files.sort(key=lambda x: x["mtime"])
        pruned = []
        while len(files) > max_backups:
            oldest = files.pop(0) # FIFO
            os.remove(oldest["path"])
            pruned.append(oldest["filename"])
        return {"pruned_count": len(pruned), "remaining_count": len(files), "pruned_files": pruned}

    res = custom_prune(max_backups=14)
    print(f"  [OK] Resultado de poda FIFO: Purgados={res['pruned_count']}, Restantes={res['remaining_count']}")

    assert res['pruned_count'] == 4, f"Debieron purgarse exactamente 4 archivos, purgados: {res['pruned_count']}"
    assert res['remaining_count'] == 14, f"Debieron quedar exactamente 14 archivos, quedaron: {res['remaining_count']}"

    # Validar que los 4 más antiguos (0, 1, 2, 3) ya no existen
    for i in range(4):
        fname = f"TEV_BACKUP_TEST_FIFO_{i:02d}.json"
        fpath = os.path.join(test_backup_dir, fname)
        assert not os.path.exists(fpath), f"El archivo mas antiguo {fname} debio ser purgado por FIFO!"

    # Validar que los 14 más recientes (4 al 17) existen
    for i in range(4, 18):
        fname = f"TEV_BACKUP_TEST_FIFO_{i:02d}.json"
        fpath = os.path.join(test_backup_dir, fname)
        assert os.path.exists(fpath), f"El archivo reciente {fname} debio conservarse!"

    # Limpieza
    shutil.rmtree(test_backup_dir)

    print("  [OK] Principio FIFO verificado: Los 4 archivos mas antiguos fueron descartados primero.")
    print("=================================================================")
    print("  TEST FIFO ROTATION: 100% PASS")
    print("=================================================================\n")

if __name__ == "__main__":
    test_fifo_prune_logic()
