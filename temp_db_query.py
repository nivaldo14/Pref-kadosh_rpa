import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

db_user = os.getenv('DB_USER', 'postgres')
db_pass = os.getenv('DB_PASS', 'root')
db_host = os.getenv('DB_HOST', 'localhost')
db_port = os.getenv('DB_PORT', '5432')
db_name = os.getenv('DB_NAME', 'dbkadosh')

try:
    conn = psycopg2.connect(
        dbname=db_name,
        user=db_user,
        password=db_pass,
        host=db_host,
        port=db_port
    )
    cur = conn.cursor()

    query = "SELECT id, url_acesso, contato, telefone, head_evento, tempo_espera_segundos, modo_execucao, senha_site_encrypted FROM configuracao_robo;"
    cur.execute(query)

    rows = cur.fetchall()

    if not rows:
        print("Nenhuma configuração de robô encontrada.")
    else:
        for row in rows:
            print(f"ID: {row[0]}")
            print(f"URL Acesso: {row[1]}")
            print(f"Contato: {row[2]}")
            print(f"Telefone: {row[3]}")
            print(f"Head Evento: {row[4]}")
            print(f"Tempo Espera Segundos: {row[5]}")
            print(f"Modo Execução: {row[6]}")
            print(f"Senha Site Encrypted: {row[7]}")
            print("-" * 30)

    cur.close()
    conn.close()

except psycopg2.Error as e:
    print(f"Erro ao conectar ou consultar o banco de dados: {e}")
except Exception as e:
    print(f"Ocorreu um erro inesperado: {e}")
