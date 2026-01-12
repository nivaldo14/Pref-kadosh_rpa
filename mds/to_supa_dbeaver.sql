-- --------------------------------------------------------
-- Servidor:                     127.0.0.1
-- Versão do servidor:           PostgreSQL 17.5 on x86_64-windows, compiled by msvc-19.44.35209, 64-bit
-- OS do Servidor:               
-- HeidiSQL Versão:              12.5.0.6677
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES  */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

-- Copiando estrutura para tabela public.agenda
CREATE TABLE IF NOT EXISTS "agenda" (
	"id" INTEGER NOT NULL DEFAULT 'nextval(''agenda_id_seq''::regclass)',
	"motorista_id" INTEGER NOT NULL,
	"caminhao_id" INTEGER NOT NULL,
	"fertipar_protocolo" VARCHAR(100) NOT NULL,
	"fertipar_pedido" VARCHAR(100) NULL DEFAULT NULL,
	"fertipar_destino" VARCHAR(100) NULL DEFAULT NULL,
	"fertipar_data" VARCHAR(50) NULL DEFAULT NULL,
	"fertipar_qtde" VARCHAR(50) NULL DEFAULT NULL,
	"status" VARCHAR(50) NOT NULL,
	"data_agendamento" TIMESTAMP NOT NULL,
	PRIMARY KEY ("id"),
	UNIQUE INDEX "agenda_fertipar_protocolo_key" ("fertipar_protocolo"),
	CONSTRAINT "agenda_caminhao_id_fkey" FOREIGN KEY ("caminhao_id") REFERENCES "caminhao" ("id") ON UPDATE NO ACTION ON DELETE NO ACTION,
	CONSTRAINT "agenda_motorista_id_fkey" FOREIGN KEY ("motorista_id") REFERENCES "motorista" ("id") ON UPDATE NO ACTION ON DELETE NO ACTION
);

-- Copiando dados para a tabela public.agenda: -1 rows
/*!40000 ALTER TABLE "agenda" DISABLE KEYS */;
/*!40000 ALTER TABLE "agenda" ENABLE KEYS */;

-- Copiando estrutura para tabela public.alembic_version
CREATE TABLE IF NOT EXISTS "alembic_version" (
	"version_num" VARCHAR(32) NOT NULL,
	PRIMARY KEY ("version_num")
);

-- Copiando dados para a tabela public.alembic_version: -1 rows
/*!40000 ALTER TABLE "alembic_version" DISABLE KEYS */;
INSERT INTO "alembic_version" ("version_num") VALUES
	('60d7e36948ff');
/*!40000 ALTER TABLE "alembic_version" ENABLE KEYS */;

-- Copiando estrutura para tabela public.caminhao
CREATE TABLE IF NOT EXISTS "caminhao" (
	"id" INTEGER NOT NULL DEFAULT 'nextval(''caminhao_id_seq''::regclass)',
	"placa" VARCHAR(10) NOT NULL,
	"uf" VARCHAR(2) NOT NULL,
	"tipo_carroceria" VARCHAR(50) NULL DEFAULT NULL,
	"placa_reboque1" VARCHAR(10) NULL DEFAULT NULL,
	"uf1" VARCHAR(2) NULL DEFAULT NULL,
	"placa_reboque2" VARCHAR(10) NULL DEFAULT NULL,
	"uf2" VARCHAR(2) NULL DEFAULT NULL,
	"placa_reboque3" VARCHAR(10) NULL DEFAULT NULL,
	"uf3" VARCHAR(2) NULL DEFAULT NULL,
	PRIMARY KEY ("id"),
	UNIQUE INDEX "caminhao_placa_key" ("placa")
);

-- Copiando dados para a tabela public.caminhao: -1 rows
/*!40000 ALTER TABLE "caminhao" DISABLE KEYS */;
/*!40000 ALTER TABLE "caminhao" ENABLE KEYS */;

-- Copiando estrutura para tabela public.cargas_executada
CREATE TABLE IF NOT EXISTS "cargas_executada" (
	"id" INTEGER NOT NULL DEFAULT 'nextval(''cargas_executada_id_seq''::regclass)',
	"descricao" VARCHAR(200) NOT NULL,
	"data" VARCHAR(20) NOT NULL,
	"caminhao_id" INTEGER NULL DEFAULT NULL,
	"motorista_id" INTEGER NULL DEFAULT NULL,
	PRIMARY KEY ("id"),
	CONSTRAINT "cargas_executada_caminhao_id_fkey" FOREIGN KEY ("caminhao_id") REFERENCES "caminhao" ("id") ON UPDATE NO ACTION ON DELETE NO ACTION,
	CONSTRAINT "cargas_executada_motorista_id_fkey" FOREIGN KEY ("motorista_id") REFERENCES "motorista" ("id") ON UPDATE NO ACTION ON DELETE NO ACTION
);

-- Copiando dados para a tabela public.cargas_executada: -1 rows
/*!40000 ALTER TABLE "cargas_executada" DISABLE KEYS */;
/*!40000 ALTER TABLE "cargas_executada" ENABLE KEYS */;

-- Copiando estrutura para tabela public.configuracao_robo
CREATE TABLE IF NOT EXISTS "configuracao_robo" (
	"id" INTEGER NOT NULL DEFAULT 'nextval(''configuracao_robo_id_seq''::regclass)',
	"url_acesso" VARCHAR(255) NOT NULL,
	"filial" VARCHAR(50) NOT NULL,
	"usuario_site" VARCHAR(80) NOT NULL,
	"senha_site" VARCHAR(80) NOT NULL,
	"email_retorno" VARCHAR(100) NOT NULL,
	"pagina_raspagem" VARCHAR(255) NULL DEFAULT NULL,
	"contato" VARCHAR(100) NULL DEFAULT NULL,
	"telefone" VARCHAR(20) NULL DEFAULT NULL,
	"head_evento" BOOLEAN NOT NULL,
	PRIMARY KEY ("id")
);

-- Copiando dados para a tabela public.configuracao_robo: -1 rows
/*!40000 ALTER TABLE "configuracao_robo" DISABLE KEYS */;
/*!40000 ALTER TABLE "configuracao_robo" ENABLE KEYS */;

-- Copiando estrutura para tabela public.motorista
CREATE TABLE IF NOT EXISTS "motorista" (
	"id" INTEGER NOT NULL DEFAULT 'nextval(''motorista_id_seq''::regclass)',
	"nome" VARCHAR(100) NOT NULL,
	"cpf" VARCHAR(20) NOT NULL,
	"telefone" VARCHAR(20) NULL DEFAULT NULL,
	"endereco" VARCHAR(200) NULL DEFAULT NULL,
	"cidade" VARCHAR(100) NULL DEFAULT NULL,
	"uf" VARCHAR(2) NULL DEFAULT NULL,
	PRIMARY KEY ("id"),
	UNIQUE INDEX "motorista_cpf_key" ("cpf")
);

-- Copiando dados para a tabela public.motorista: -1 rows
/*!40000 ALTER TABLE "motorista" DISABLE KEYS */;
/*!40000 ALTER TABLE "motorista" ENABLE KEYS */;

-- Copiando estrutura para tabela public.usuario
CREATE TABLE IF NOT EXISTS "usuario" (
	"id" INTEGER NOT NULL DEFAULT 'nextval(''usuario_id_seq''::regclass)',
	"username" VARCHAR(80) NOT NULL,
	"password_hash" VARCHAR(128) NULL DEFAULT NULL,
	"nome" VARCHAR(100) NOT NULL,
	"email" VARCHAR(100) NOT NULL,
	"telefone_fixo" VARCHAR(20) NULL DEFAULT NULL,
	"celular" VARCHAR(20) NULL DEFAULT NULL,
	"foto_perfil" VARCHAR(200) NULL DEFAULT NULL,
	"role" VARCHAR(20) NOT NULL,
	PRIMARY KEY ("id"),
	UNIQUE INDEX "usuario_email_key" ("email"),
	UNIQUE INDEX "usuario_username_key" ("username")
);

-- Copiando dados para a tabela public.usuario: -1 rows
/*!40000 ALTER TABLE "usuario" DISABLE KEYS */;
/*!40000 ALTER TABLE "usuario" ENABLE KEYS */;

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;

