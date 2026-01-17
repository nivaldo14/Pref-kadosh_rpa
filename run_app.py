# from app import app
# import os
# import sys

# # Adiciona o diretório raiz do projeto ao PATH do Python
# # Isso é importante para que módulos como 'backend.rpa_service' sejam encontrados
# # quando o PyInstaller reestrutura o aplicativo.
# project_root = os.path.abspath(os.path.dirname(__file__))
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)

# # Garante que o aplicativo Flask seja executado em modo de produção/desenvolvimento
# # dependendo do uso. Para um executável, geralmente queremos debug=False.
# # As variáveis de ambiente do .env serão carregadas pelo `python-dotenv` dentro de `app.py`.
# if __name__ == '__main__':
#     # Define o host para 0.0.0.0 para que possa ser acessível externamente na rede local
#     # (se o firewall permitir), ou 127.0.0.1 para acesso local apenas.
#     # Para uma aplicação de desktop, 127.0.0.1 é geralmente o padrão.
#     # A porta padrão do Flask é 5000.
#     app.run(host='127.0.0.1', port=5000, debug=False)
# run_app.py
from app import app

if __name__ == "__main__":
    # Executando em modo de depuração (debug=True).
    # Isso fará com que o servidor reinicie automaticamente após as alterações no código
    # e mostrará um traceback detalhado no navegador para erros.
    app.run(debug=True)
