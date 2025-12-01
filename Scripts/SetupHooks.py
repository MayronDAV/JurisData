#!/usr/bin/env python3

import os
import sys
from pathlib import Path

def setup_hooks():
    print("Instalando navegadores Playwright...")
    os.system(f"{sys.executable} -m playwright install chromium")
    
    browsers_path = Path.home() / "AppData" / "Local" / "ms-playwright"
    if not browsers_path.exists():
        print("ERRO: Navegadores não foram instalados corretamente")
        print("Execute manualmente: python -m playwright install chromium")
        return False
    
    print(f"✓ Navegadores instalados em: {browsers_path}")
    
    return True

if __name__ == "__main__":
    success = setup_hooks()
    sys.exit(0 if success else 1)