import sys
from pathlib import Path

# Adiciona o diretório src ao PYTHONPATH
sys.path.append(str(Path(__file__).parent / "src"))

from main import app

if __name__ == "__main__":
    app.run() 