# Plano de Migração do Banco de Dados: SQLite para PostgreSQL

Este documento descreve os passos para migrar o banco de dados da aplicação de SQLite para PostgreSQL.

## 1. Backup do Banco de Dados Atual

Antes de qualquer alteração, é fundamental criar um backup do arquivo de banco de dados existente (`front/database.db`). Isso garante que os dados originais possam ser restaurados em caso de problemas.

```bash
# Exemplo de comando para backup
copy front\database.db front\database.db.backup
```

## 2. Análise do Esquema Atual

O esquema do banco de dados é definido pelos modelos (Models) no arquivo `front/app.py`. É necessário analisar esses modelos para entender a estrutura de cada tabela, incluindo colunas, tipos de dados e relacionamentos (chaves estrangeiras).

## 3. Configuração do PostgreSQL

Será necessário instalar e configurar um servidor PostgreSQL. Após a instalação, execute os seguintes passos:

1.  **Criar o Banco de Dados**: Crie um novo banco de dados chamado `dbkadosh`.
2.  **Criar um Usuário (Role)**: Crie um usuário e uma senha para a aplicação acessar o banco de dados. Conceda a este usuário as permissões necessárias sobre o banco de dados `dbkadosh`.

## 4. Atualização da Configuração da Aplicação

A aplicação Flask precisa ser reconfigurada para se conectar ao novo banco de dados PostgreSQL.

1.  **Instalar o Driver do Banco de Dados**: Adicione a biblioteca `psycopg2-binary` ao arquivo `requirements.txt` do projeto e instale-a no ambiente virtual.

    ```bash
    # Exemplo de comando para instalar
    pip install psycopg2-binary
    ```

2.  **Atualizar a URI de Conexão**: No arquivo `front/app.py`, a variável `SQLALCHEMY_DATABASE_URI` deve ser alterada para o formato do PostgreSQL. É altamente recomendado o uso de variáveis de ambiente para armazenar as credenciais, em vez de escrevê-las diretamente no código.

    ```python
    # Exemplo de alteração em app.py
    # Substituir a linha do SQLite por:
    db_user = os.getenv('DB_USER', 'seu_usuario')
    db_pass = os.getenv('DB_PASS', 'sua_senha')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_name = os.getenv('DB_NAME', 'dbkadosh')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_pass}@{db_host}/{db_name}'
    ```

## 5. Recriação do Esquema no PostgreSQL

Como o projeto já utiliza o Flask-Migrate, podemos usá-lo para criar as tabelas no PostgreSQL. O histórico de migrações atual é para SQLite, então a abordagem mais segura é gerar um novo.

1.  **(Backup Opcional)** Faça um backup da pasta `front/migrations`.
2.  **Reiniciar o Histórico de Migração**:
    *   Delete a pasta `front/migrations`.
    *   Execute `flask db init` para criar um novo repositório de migrações.
    *   Execute `flask db migrate -m "Initial migration for PostgreSQL"` para gerar um novo script de migração baseado nos modelos existentes.
    *   Execute `flask db upgrade` para aplicar a migração e criar as tabelas no banco de dados PostgreSQL `dbkadosh`.

## 6. Migração dos Dados

Esta é a etapa mais crítica. A transferência de dados pode ser feita de duas formas principais:

### Opção A: Script de Migração Manual

Escrever um script Python que:
1.  Conecte-se ao banco de dados SQLite antigo.
2.  Conecte-se ao novo banco de dados PostgreSQL.
3.  Leia os dados de cada tabela do SQLite.
4.  Insira os dados na tabela correspondente no PostgreSQL, respeitando a ordem correta para não violar as chaves estrangeiras (geralmente, tabelas de usuários primeiro, depois tabelas que dependem delas).

### Opção B: Ferramenta de Migração (Recomendado)

Utilizar uma ferramenta especializada como o **pgloader**. Com um único comando, o `pgloader` pode migrar o esquema e os dados, fazendo a conversão de tipos de dados automaticamente.

1.  **Instalar o pgloader**: Siga as instruções de instalação para o seu sistema operacional.
2.  **Executar a Migração**: Execute o comando a seguir (ajuste os caminhos e credenciais):

    ```bash
    pgloader sqlite:///C:/caminho/completo/para/front/database.db postgresql://seu_usuario:sua_senha@localhost/dbkadosh
    ```

## 7. Testes e Validação

Após a migração dos dados, é crucial:
1.  **Testar a Aplicação**: Inicie a aplicação e teste todas as funcionalidades para garantir que ela opera corretamente com o PostgreSQL.
2.  **Validar os Dados**: Execute consultas SQL no novo banco de dados para confirmar que os dados foram migrados corretamente e com integridade.

## 8. Implantação Final

Uma vez que a aplicação esteja totalmente testada e validada, a nova versão, configurada para usar o PostgreSQL, pode ser implantada no ambiente de produção.
