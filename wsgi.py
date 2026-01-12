import sys
import os

# Adicione o diretório raiz do projeto ao sys.path
# Isso é importante para que o Flask possa encontrar 'app.py'
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir)) # front_postgres
sys.path.insert(0, project_root)

# A pasta 'backend' não será implantada no Vercel neste momento.
# A linha sys.path.insert para 'backend' foi removida.

from app import app as application # Importa sua aplicação Flask
