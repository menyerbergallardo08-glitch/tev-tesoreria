# ==============================================================================
# TEV AUXILIARY TOOL — NOT FOR PRIMARY RELEASE SYNC
# Este script es una herramienta auxiliar de contingencia.
# El mecanismo oficial y recomendado para el release definitivo es Git nativo.
# ==============================================================================
import os
import sys
import json
import base64
import urllib.request
import urllib.error

REPO_OWNER = 'menyerbergallardo08-glitch'
REPO_NAME = 'tev-tesoreria'
BRANCH = 'main'

DEFAULT_FILES = [
    'main.py',
    'models.py',
    'database.py',
    'init_db.py',
    'requirements.txt',
    'Procfile',
    'render.yaml',
    '.gitignore',
    '.env.example',
    'core/__init__.py',
    'core/config.py',
    'core/security.py',
    'core/seniat.py',
    'core/bcv.py',
    'core/audit.py',
    'schemas/__init__.py',
    'schemas/sales.py',
    'schemas/expenses.py',
    'schemas/cxc.py',
    'schemas/accounts.py',
    'schemas/users.py',
    'schemas/cash_close.py',
    'schemas/system.py',
    'services/__init__.py',
    'services/sales_service.py',
    'services/expense_service.py',
    'services/cxc_service.py',
    'services/account_service.py',
    'services/backup_service.py',
    'routers/__init__.py',
    'routers/auth.py',
    'routers/sales.py',
    'routers/expenses.py',
    'routers/cxc.py',
    'routers/accounts.py',
    'routers/cash_close.py',
    'routers/categories.py',
    'routers/transfers.py',
    'routers/audit.py',
    'routers/system.py',
    'static/index.html',
    'static/alpine.min.js',
    'static/js/app.js',
    'static/js/api/client.js',
    'static/js/utils/formatters.js',
    'static/js/utils/toast.js',
    'static/js/utils/bankRules.js',
    'static/js/state/store.js',
    'static/js/modules/pos.js',
    'static/js/modules/expenses.js',
    'static/js/modules/cxc.js',
    'static/js/modules/accounts.js',
    '.github/workflows/ci.yml',
    'tests/test_financial_regression.py',
    'tests/test_qa_suite.py',
    'PRODUCTION_ROLLBACK_PLAN.md',
    'MANUAL_CAJERA.md',
    'MANUAL_ADMINISTRADORA.md',
    'MANUAL_DIRECTIVO.md'
]

def get_file_sha(token: str, file_path: str):
    url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{file_path}?ref={BRANCH}'
    req = urllib.request.Request(url, headers={
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'TEV-Sync-Bot'
    })
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('sha')
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise

def upload_file(token: str, file_path: str, commit_message: str) -> bool:
    if not os.path.exists(file_path):
        print(f'[-] Archivo local no encontrado: {file_path}')
        return False
    with open(file_path, 'rb') as f:
        content_bytes = f.read()
    b64_content = base64.b64encode(content_bytes).decode('utf-8')
    sha = get_file_sha(token, file_path)
    payload = {
        'message': commit_message,
        'content': b64_content,
        'branch': BRANCH
    }
    if sha:
        payload['sha'] = sha
    url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{file_path}'
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='PUT', headers={
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
        'User-Agent': 'TEV-Sync-Bot'
    })
    try:
        with urllib.request.urlopen(req) as resp:
            res_data = json.loads(resp.read().decode('utf-8'))
            c_sha = res_data.get('commit', {}).get('sha', '')[:7]
            print(f'[+] Sincronizado con exito: {file_path} -> Commit {c_sha}')
            return True
    except urllib.error.HTTPError as e:
        err = e.read().decode('utf-8')
        print(f'[!] Error al subir {file_path}: {err}')
        return False

def main():
    if len(sys.argv) > 1:
        print('[ERROR DE SEGURIDAD] Paso de tokens/secretos por argumentos de línea de comandos está prohibido.')
        print('[i] Configure la variable de entorno GITHUB_TOKEN antes de ejecutar este script.')
        sys.exit(1)

    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if not token or not token.strip():
        print('[!] GITHUB AUTHENTICATION = NOT AVAILABLE')
        print('[i] Para sincronizar, defina la variable de entorno GITHUB_TOKEN en su terminal.')
        print('    PowerShell: $env:GITHUB_TOKEN="tu_token" ; python sync_github.py')
        sys.exit(1)

    target_files = DEFAULT_FILES
    print(f'Iniciando sincronizacion segura de {len(target_files)} archivos con {REPO_OWNER}/{REPO_NAME} ({BRANCH})...')
    success_count = 0
    for f in target_files:
        if upload_file(token.strip(), f, f'TEV v2.1.0 Modular: {f}'):
            success_count += 1

    print(f'Sincronizacion completada: {success_count}/{len(target_files)} archivos.')

if __name__ == '__main__':
    main()
