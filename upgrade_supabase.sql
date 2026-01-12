BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 60d7e36948ff

CREATE TABLE caminhao (
    id SERIAL NOT NULL, 
    placa VARCHAR(10) NOT NULL, 
    uf VARCHAR(2) NOT NULL, 
    tipo_carroceria VARCHAR(50), 
    placa_reboque1 VARCHAR(10), 
    uf1 VARCHAR(2), 
    placa_reboque2 VARCHAR(10), 
    uf2 VARCHAR(2), 
    placa_reboque3 VARCHAR(10), 
    uf3 VARCHAR(2), 
    PRIMARY KEY (id), 
    UNIQUE (placa)
);

CREATE TABLE configuracao_robo (
    id SERIAL NOT NULL, 
    url_acesso VARCHAR(255) NOT NULL, 
    filial VARCHAR(50) NOT NULL, 
    usuario_site VARCHAR(80) NOT NULL, 
    senha_site VARCHAR(80) NOT NULL, 
    email_retorno VARCHAR(100) NOT NULL, 
    pagina_raspagem VARCHAR(255), 
    contato VARCHAR(100), 
    telefone VARCHAR(20), 
    head_evento BOOLEAN NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE motorista (
    id SERIAL NOT NULL, 
    nome VARCHAR(100) NOT NULL, 
    cpf VARCHAR(20) NOT NULL, 
    telefone VARCHAR(20), 
    endereco VARCHAR(200), 
    cidade VARCHAR(100), 
    uf VARCHAR(2), 
    PRIMARY KEY (id), 
    UNIQUE (cpf)
);

CREATE TABLE usuario (
    id SERIAL NOT NULL, 
    username VARCHAR(80) NOT NULL, 
    password_hash VARCHAR(128), 
    nome VARCHAR(100) NOT NULL, 
    email VARCHAR(100) NOT NULL, 
    telefone_fixo VARCHAR(20), 
    celular VARCHAR(20), 
    foto_perfil VARCHAR(200), 
    role VARCHAR(20) NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (email), 
    UNIQUE (username)
);

CREATE TABLE agenda (
    id SERIAL NOT NULL, 
    motorista_id INTEGER NOT NULL, 
    caminhao_id INTEGER NOT NULL, 
    fertipar_protocolo VARCHAR(100) NOT NULL, 
    fertipar_pedido VARCHAR(100), 
    fertipar_destino VARCHAR(100), 
    fertipar_data VARCHAR(50), 
    fertipar_qtde VARCHAR(50), 
    status VARCHAR(50) NOT NULL, 
    data_agendamento TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(caminhao_id) REFERENCES caminhao (id), 
    FOREIGN KEY(motorista_id) REFERENCES motorista (id), 
    UNIQUE (fertipar_protocolo)
);

CREATE TABLE cargas_executada (
    id SERIAL NOT NULL, 
    descricao VARCHAR(200) NOT NULL, 
    data VARCHAR(20) NOT NULL, 
    caminhao_id INTEGER, 
    motorista_id INTEGER, 
    PRIMARY KEY (id), 
    FOREIGN KEY(caminhao_id) REFERENCES caminhao (id), 
    FOREIGN KEY(motorista_id) REFERENCES motorista (id)
);

INSERT INTO alembic_version (version_num) VALUES ('60d7e36948ff') RETURNING alembic_version.version_num;

COMMIT;

