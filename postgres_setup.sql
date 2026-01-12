-- Script de Configuração do Banco de Dados PostgreSQL para o KadoshBot
-- Versão do PostgreSQL: 17.5
-- Codificação: UTF-8

-- Garante que o cliente esteja usando a codificação correta
SET client_encoding = 'UTF8';

-- Tabela de Usuários
-- Armazena as informações de login e perfil dos usuários do sistema.
CREATE TABLE IF NOT EXISTS usuario (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL, -- Aumentado para acomodar hashes mais longos como scrypt
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    telefone_fixo VARCHAR(20),
    celular VARCHAR(20),
    foto_perfil VARCHAR(200) DEFAULT 'default.jpg',
    role VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user'))
);

-- Tabela de Configuração do Robô
-- Armazena as configurações para o robô de web scraping.
CREATE TABLE IF NOT EXISTS configuracao_robo (
    id SERIAL PRIMARY KEY,
    url_acesso VARCHAR(255) NOT NULL,
    filial VARCHAR(50) NOT NULL,
    usuario_site VARCHAR(80) NOT NULL,
    senha_site VARCHAR(80) NOT NULL,
    email_retorno VARCHAR(100) NOT NULL,
    pagina_raspagem VARCHAR(255),
    contato VARCHAR(100),
    telefone VARCHAR(20),
    head_evento BOOLEAN NOT NULL DEFAULT TRUE
);

-- Tabela de Caminhões
-- Cadastro de todos os caminhões e seus reboques.
CREATE TABLE IF NOT EXISTS caminhao (
    id SERIAL PRIMARY KEY,
    placa VARCHAR(10) UNIQUE NOT NULL,
    uf VARCHAR(2) NOT NULL,
    tipo_carroceria VARCHAR(50),
    placa_reboque1 VARCHAR(10),
    uf1 VARCHAR(2),
    placa_reboque2 VARCHAR(10),
    uf2 VARCHAR(2),
    placa_reboque3 VARCHAR(10),
    uf3 VARCHAR(2)
);

-- Tabela de Motoristas
-- Cadastro dos motoristas.
CREATE TABLE IF NOT EXISTS motorista (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    cpf VARCHAR(20) UNIQUE NOT NULL,
    telefone VARCHAR(20),
    endereco VARCHAR(200),
    cidade VARCHAR(100),
    uf VARCHAR(2)
);

-- Tabela de Cargas Executadas
-- Histórico de cargas que já foram concluídas.
CREATE TABLE IF NOT EXISTS cargas_executada (
    id SERIAL PRIMARY KEY,
    descricao VARCHAR(200) NOT NULL,
    data VARCHAR(20) NOT NULL,
    caminhao_id INTEGER REFERENCES caminhao(id),
    motorista_id INTEGER REFERENCES motorista(id)
);

-- Tabela de Agenda
-- Gerencia os agendamentos de carga, vinculando motorista, caminhão e os dados da carga da Fertipar.
CREATE TABLE IF NOT EXISTS agenda (
    id SERIAL PRIMARY KEY,
    motorista_id INTEGER NOT NULL REFERENCES motorista(id),
    caminhao_id INTEGER NOT NULL REFERENCES caminhao(id),
    fertipar_protocolo VARCHAR(100) UNIQUE NOT NULL,
    fertipar_pedido VARCHAR(100),
    fertipar_destino VARCHAR(100),
    fertipar_data VARCHAR(50),
    fertipar_qtde VARCHAR(50),
    status VARCHAR(50) NOT NULL DEFAULT 'espera',
    data_agendamento TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP)
);

-- --- INSERTS ---

-- Insere o usuário administrador padrão com a senha 'admin'
-- O hash foi gerado com werkzeug.security.generate_password_hash('admin')
INSERT INTO usuario (username, password_hash, nome, email, role) 
VALUES ('admin', 'scrypt:32768:8:1$DWAYBvxH9VykP1jR$a70b5d55ea0ff04897aab447a8c79a5dd44740320a096b87ab19de017ef250fd17189d4965d4fc0ec6053b64ae1b2da8302c7e4ade1bf7de3a8062775fb56ea5', 'Administrador do Sistema', 'admin@kadosh.com', 'admin')
ON CONFLICT (username) DO NOTHING;

-- Insere uma configuração padrão para o robô (exemplo)
INSERT INTO configuracao_robo (url_acesso, filial, usuario_site, senha_site, email_retorno, pagina_raspagem, head_evento)
VALUES ('http://example.com/login', 'N/A', 'usuario', 'senha', 'retorno@example.com', 'http://example.com/cotacoes', TRUE)
ON CONFLICT (id) DO NOTHING;


-- --- ÍNDICES ---

-- Índices para chaves estrangeiras para otimizar as consultas
CREATE INDEX IF NOT EXISTS idx_cargas_executada_caminhao_id ON cargas_executada(caminhao_id);
CREATE INDEX IF NOT EXISTS idx_cargas_executada_motorista_id ON cargas_executada(motorista_id);
CREATE INDEX IF NOT EXISTS idx_agenda_motorista_id ON agenda(motorista_id);
CREATE INDEX IF NOT EXISTS idx_agenda_caminhao_id ON agenda(caminhao_id);

-- Índice para o status da agenda, para buscas rápidas de agendamentos em espera
CREATE INDEX IF NOT EXISTS idx_agenda_status ON agenda(status);


-- --- Comentários Finais ---
-- O script está pronto. Copie e cole todo o conteúdo em uma janela de query no DBeaver
-- e execute para criar a estrutura do banco de dados e inserir os dados iniciais.
-- Lembre-se de configurar a conexão no DBeaver com as credenciais corretas do seu banco de dados PostgreSQL.
