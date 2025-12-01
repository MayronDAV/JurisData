from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules, exec_statement
import os
from pathlib import Path


hiddenimports = collect_submodules('playwright')

hiddenimports.extend([
    'playwright._impl',
    'playwright.async_api._context_manager',
    'playwright.sync_api._context_manager',
    'playwright._repo_version',
    'playwright.driver',
    'pyee',
    'greenlet',
    'websockets',
])

print(f"[HOOK-PLAYWRIGHT] Módulos ocultos detectados: {len(hiddenimports)}")

datas = []

def collect_playwright_browsers():
    """Coleta os binários dos navegadores do Playwright"""
    browser_datas = []
    
    possible_paths = [
        Path.home() / ".cache" / "ms-playwright",
        Path.home() / "AppData" / "Local" / "ms-playwright",  # Windows
        Path.home() / ".local" / "share" / "playwright",      # Linux
    ]
    
    browsers_path = None
    for path in possible_paths:
        if path.exists():
            browsers_path = path
            print(f"[HOOK-PLAYWRIGHT] Navegadores encontrados em: {browsers_path}")
            break
    
    if browsers_path and browsers_path.exists():
        for browser_dir in browsers_path.iterdir():
            if browser_dir.is_dir():
                dest_path = f"playwright/driver/package/.local-browsers/{browser_dir.name}"

                browser_datas.append((str(browser_dir), dest_path))
                print(f"[HOOK-PLAYWRIGHT]   [+] {browser_dir.name}")
    
    return browser_datas

browser_datas = collect_playwright_browsers()
datas.extend(browser_datas)

try:
    metadata_datas = collect_data_files('playwright')
    datas.extend(metadata_datas)
    print(f"[HOOK-PLAYWRIGHT] Metadados coletados")
except Exception as e:
    print(f"[HOOK-PLAYWRIGHT] Erro ao coletar metadados: {e}")

binaries = []

try:
    code = """
import playwright
import os
print(os.path.dirname(playwright.__file__))
"""
    
    result = exec_statement(code)
    playwright_dir = result.strip()
    
    # Procura por executáveis
    driver_path = Path(playwright_dir) / "driver"
    if driver_path.exists():
        for exe_file in driver_path.rglob("*.exe"):
            binaries.append((str(exe_file), 'playwright/driver'))
            
except Exception as e:
    print(f"[HOOK-PLAYWRIGHT] Erro ao coletar binários: {e}")

print(f"[HOOK-PLAYWRIGHT] Hook concluído: {len(hiddenimports)} imports, {len(datas)} arquivos de dados, {len(binaries)} binários")