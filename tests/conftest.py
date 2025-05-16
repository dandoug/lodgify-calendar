import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Add the lambda_function directory to sys.path
sys.path.append(str(PROJECT_ROOT / 'lambda_function'))
