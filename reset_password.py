import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configuração mínima do Flask App ---
app = Flask(__name__)

# Configuração do banco de dados a partir das mesmas variáveis de ambiente
db_user = os.getenv('DB_USER', 'postgres')
db_pass = os.getenv('DB_PASS', 'root')
db_host = os.getenv('DB_HOST', 'localhost')
db_port = os.getenv('DB_PORT', '5432')
db_name = os.getenv('DB_NAME', 'dbkadosh')

# Garante que estamos usando o nome de banco correto que foi corrigido
if db_name != 'dbkadosh':
    print("ERRO: O nome do banco de dados no seu arquivo .env está incorreto. Corrija para 'dbkadosh'.")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?client_encoding=utf8'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db = SQLAlchemy(app)

    # --- Definição do Modelo de Usuário (cópia da estrutura existente) ---
    class Usuario(db.Model):
        __tablename__ = 'usuario'
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True, nullable=False)
        password_hash = db.Column(db.String(256))

        def set_password(self, password):
            self.password_hash = generate_password_hash(password)

    # --- Lógica de Redefinição de Senha ---
    try:
        with app.app_context():
            print("Conectando ao banco de dados para redefinir a senha...")
            
            # Tenta encontrar o usuário 'admin'
            admin_user = db.session.query(Usuario).filter_by(username='admin').first()

            if admin_user:
                print(f"Usuário '{admin_user.username}' encontrado. Redefinindo a senha...")
                admin_user.set_password('admin')
                db.session.commit()
                print("---")
                print("Senha do usuário 'admin' foi redefinida com sucesso para 'admin'.")
                print("Pode tentar fazer o login na aplicação agora.")
                print("---")
            else:
                print("ERRO: Usuário 'admin' não foi encontrado no banco de dados.")

    except Exception as e:
        print(f"Ocorreu um erro ao tentar conectar ao banco ou redefinir a senha: {e}")
        print("Verifique se as credenciais no seu arquivo .env estão corretas.")