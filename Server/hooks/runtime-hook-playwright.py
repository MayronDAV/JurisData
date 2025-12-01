import sys
import os
import tempfile
import shutil
import atexit
from pathlib import Path

def setup_playwright_for_pyinstaller(): 
    if not getattr(sys, 'frozen', False):
        return
    
    print("[RUNTIME-HOOK] Configurando Playwright para PyInstaller...")
    
    if hasattr(sys, '_MEIPASS'):
        base_dir = Path(sys._MEIPASS)
        print(f"[RUNTIME-HOOK] Modo: onefile, Base: {base_dir}")
    else:
        base_dir = Path(sys.executable).parent
        print(f"[RUNTIME-HOOK] Modo: onedir, Base: {base_dir}")
    
    possible_browser_paths = [
        base_dir / "playwright" / "driver" / "package" / ".local-browsers",
        base_dir / ".local-browsers",
        base_dir / "browsers",
    ]
    
    browsers_source_path = None
    for path in possible_browser_paths:
        if path.exists():
            browsers_source_path = path
            print(f"[RUNTIME-HOOK] Navegadores encontrados em: {browsers_source_path}")
            break
    
    if not browsers_source_path:
        print("[RUNTIME-HOOK] AVISO: Navegadores não encontrados no executável")
        return

    temp_browsers_dir = Path(tempfile.gettempdir()) / f"playwright_browsers_{os.getpid()}"

    if temp_browsers_dir.exists():
        shutil.rmtree(temp_browsers_dir, ignore_errors=True)

    print(f"[RUNTIME-HOOK] Copiando navegadores para: {temp_browsers_dir}")
    
    try:
        shutil.copytree(browsers_source_path, temp_browsers_dir)
        print(f"[RUNTIME-HOOK] ✓ Navegadores copiados com sucesso")

        chromium_found = False
        for item in temp_browsers_dir.rglob("chrome.exe"):
            if item.exists():
                chromium_found = True
                print(f"[RUNTIME-HOOK] ✓ Chromium encontrado: {item}")
                break
        
        if not chromium_found:
            print("[RUNTIME-HOOK] AVISO: Chromium não encontrado após cópia")
            
    except Exception as e:
        print(f"[RUNTIME-HOOK] ERRO ao copiar navegadores: {e}")
        return
    
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(temp_browsers_dir)
    print(f"[RUNTIME-HOOK] PLAYWRIGHT_BROWSERS_PATH = {temp_browsers_dir}")
    
    os.environ["PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS"] = "1"
    os.environ["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "1"
    
    def cleanup_temp_browsers():
        """Limpa diretório temporário ao sair"""
        if temp_browsers_dir.exists():
            try:
                shutil.rmtree(temp_browsers_dir, ignore_errors=True)
                print(f"[RUNTIME-HOOK] Diretório temporário removido: {temp_browsers_dir}")
            except:
                pass
    
    atexit.register(cleanup_temp_browsers)

    original_import = __builtins__.__import__
    
    def patched_import(name, *args, **kwargs):
        if name == 'playwright' or name.startswith('playwright.'):
            result = original_import(name, *args, **kwargs)
            
            if name == 'playwright._impl':
                try:
                    from playwright._impl import _get_driver_env
                    original_get_driver_env = _get_driver_env
                    
                    def patched_get_driver_env():
                        env = original_get_driver_env()
                        env['PLAYWRIGHT_BROWSERS_PATH'] = str(temp_browsers_dir)
                        return env
                    
                    _get_driver_env = patched_get_driver_env
                except:
                    pass
            
            return result
        return original_import(name, *args, **kwargs)
    
    __builtins__.__import__ = patched_import
    
    print("[RUNTIME-HOOK] ✓ Configuração do Playwright concluída")

setup_playwright_for_pyinstaller()