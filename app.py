from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import OperationalError
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
import os
import asyncio # Import asyncio for running async Playwright tasks
import sys
# Adiciona o diretório 'backend' ao sys.path para importações relativas
# Isso é necessário se 'app.py' é executado diretamente de 'front/'
# mas 'rotas.py' está em 'backend/rpa_fertipar/'
# É uma solução temporária, o ideal seria organizar o projeto como um pacote Python
basedir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(basedir, 'backend'))

from rpa_service import scrape_fertipar_data # Import the new scraping function

# A pasta backend e o robô Playwright não serão implantados no Vercel neste momento.
# As linhas de sys.path.append e a importação do robô foram removidas.

import jwt
from datetime import datetime, timedelta
from functools import wraps


import os
from dotenv import load_dotenv

load_dotenv()



app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'supersecretkey_fallback_for_dev')
# Configuração do banco de dados PostgreSQL a partir de variáveis de ambiente
db_user = os.getenv('DB_USER', 'postgres')
db_pass = os.getenv('DB_PASS', 'root')
db_host = os.getenv('DB_HOST', 'localhost')
db_port = os.getenv('DB_PORT', '5432')
db_name = os.getenv('DB_NAME', 'dbkadosh')
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?client_encoding=utf8'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- JWT Decorator ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        elif 'Authorization' in request.headers:
            # Expected format: "Bearer <token>"
            try:
                token = request.headers['Authorization'].split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Formato de token inválido!'}), 401

        if not token:
            return jsonify({'message': 'Token está faltando!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = Usuario.query.get(data['id'])
            if current_user is None:
                return jsonify({'message': 'Usuário do token não encontrado!'}), 404
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'O token expirou!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token inválido!'}), 401

        return f(current_user, *args, **kwargs)
    return decorated

# --- Database Models ---

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    telefone_fixo = db.Column(db.String(20), nullable=True)
    celular = db.Column(db.String(20), nullable=True)
    foto_perfil = db.Column(db.String(200), nullable=True, default='default.jpg') # Default profile pic
    role = db.Column(db.String(20), nullable=False, default='user') # 'admin' or 'user'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ConfiguracaoRobo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url_acesso = db.Column(db.String(255), nullable=False)
    filial = db.Column(db.String(50), nullable=False)
    usuario_site = db.Column(db.String(80), nullable=False)
    senha_site = db.Column(db.String(255), nullable=False) # Store plain text password
    email_retorno = db.Column(db.String(100), nullable=False)
    pagina_raspagem = db.Column(db.String(255), nullable=True)
    contato = db.Column(db.String(100), nullable=True)
    telefone = db.Column(db.String(20), nullable=True)
    head_evento = db.Column(db.Boolean, nullable=False, default=False)
    modo_execucao = db.Column(db.String(20), nullable=False, default='agendado') # 'agendado' ou 'teste'
    tempo_espera_segundos = db.Column(db.Integer, nullable=True, default=30)


class Caminhao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    placa = db.Column(db.String(10), unique=True, nullable=False)
    uf = db.Column(db.String(2), nullable=False)
    tipo_carroceria = db.Column(db.String(50), nullable=True)
    placa_reboque1 = db.Column(db.String(10), nullable=True)
    uf1 = db.Column(db.String(2), nullable=True)
    placa_reboque2 = db.Column(db.String(10), nullable=True)
    uf2 = db.Column(db.String(2), nullable=True)
    placa_reboque3 = db.Column(db.String(10), nullable=True)
    uf3 = db.Column(db.String(2), nullable=True)

class Motorista(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(20), unique=True, nullable=False)
    telefone = db.Column(db.String(20), nullable=True)
    endereco = db.Column(db.String(200), nullable=True)
    cidade = db.Column(db.String(100), nullable=True)
    uf = db.Column(db.String(2), nullable=True)


class CargasExecutada(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    data = db.Column(db.String(20), nullable=False)
    caminhao_id = db.Column(db.Integer, db.ForeignKey('caminhao.id'))
    motorista_id = db.Column(db.Integer, db.ForeignKey('motorista.id'))
    
    caminhao = db.relationship('Caminhao', backref=db.backref('cargas', lazy=True))
    motorista = db.relationship('Motorista', backref=db.backref('cargas', lazy=True))

class Agenda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    motorista_id = db.Column(db.Integer, db.ForeignKey('motorista.id'), nullable=False)
    caminhao_id = db.Column(db.Integer, db.ForeignKey('caminhao.id'), nullable=False)
    
    # Dados do item Fertipar
    fertipar_protocolo = db.Column(db.String(100), nullable=False, unique=True)
    fertipar_pedido = db.Column(db.String(100))
    fertipar_destino = db.Column(db.String(100))
    fertipar_data = db.Column(db.String(50))
    fertipar_qtde = db.Column(db.String(50))
    carga_solicitada = db.Column(db.Numeric(precision=10, scale=2), nullable=True) # Novo campo
    status = db.Column(db.String(50), nullable=False, default='espera')
    data_agendamento = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    motorista = db.relationship('Motorista', backref=db.backref('agendas', lazy=True))
    caminhao = db.relationship('Caminhao', backref=db.backref('agendas', lazy=True))

    def to_dict(self):
        # Dados do Motorista
        motorista_info = self.motorista.nome
        if self.motorista.cpf:
            motorista_info += f" ({self.motorista.cpf})"
        elif self.motorista.telefone:
            motorista_info += f" ({self.motorista.telefone})"

        # Dados do Caminhão
        caminhao_info = f"{self.caminhao.placa} ({self.caminhao.uf})"
        if self.caminhao.tipo_carroceria:
            caminhao_info += f" - {self.caminhao.tipo_carroceria}"
        
        reboques_info = []
        if self.caminhao.placa_reboque1:
            reboques_info.append(f"Reb1: {self.caminhao.placa_reboque1} ({self.caminhao.uf1 or ''})")
        if self.caminhao.placa_reboque2:
            reboques_info.append(f"Reb2: {self.caminhao.placa_reboque2} ({self.caminhao.uf2 or ''})")
        if self.caminhao.placa_reboque3:
            reboques_info.append(f"Reb3: {self.caminhao.placa_reboque3} ({self.caminhao.uf3 or ''})")
        
        if reboques_info:
            caminhao_info += f" | {', '.join(reboques_info)}"

        return {
            'id': self.id,
            'motorista': motorista_info,
            'caminhao': caminhao_info,
            'protocolo': self.fertipar_protocolo,
            'pedido': self.fertipar_pedido,  # Adicionando o campo pedido
            'destino': self.fertipar_destino,
            'status': self.status,
            'data_agendamento': self.data_agendamento.strftime('%d/%m/%Y %H:%M'),
            'carga_solicitada': float(self.carga_solicitada) if self.carga_solicitada else None # Adicionar carga_solicitada
        }

# --- Routes ---

@app.context_processor
def inject_user():
    if 'user_id' in session:
        user = Usuario.query.get(session['user_id'])
        return dict(user=user)
    return dict(user=None)

@app.context_processor
def inject_configuracao_robo():
    # Isso pode retornar None se a tabela estiver vazia, o template precisa lidar com isso.
    config = ConfiguracaoRobo.query.first()
    return dict(configuracao_robo=config)

@app.route('/')
def index():
    return redirect(url_for('cadastros'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Gerar a string de versão
    now = datetime.now()
    app_version = now.strftime("01.%y%m%d%H%M") # %y para ano com 2 dígitos

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = Usuario.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_nome'] = user.nome
            session['user_foto'] = user.foto_perfil
            session['user_role'] = user.role # Store user role in session
            
            # Gerar e armazenar o token JWT na sessão
            token = jwt.encode({
                'id': user.id,
                'exp': datetime.utcnow() + timedelta(hours=24)
            }, app.config['SECRET_KEY'], algorithm="HS256")
            session['jwt_token'] = token

            flash('Login bem-sucedido!', 'success')
            return redirect(url_for('cadastros'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html', app_version=app_version)

@app.route('/logout')
def logout():
    session.clear()
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('login'))

@app.route('/cadastros')
def cadastros():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    tab = request.args.get('tab', 'caminhoes') # Get tab from URL, default to 'caminhoes'
    
    caminhoes = Caminhao.query.all()
    motoristas = Motorista.query.all()
    
    # Otimizado com Eager Loading para reduzir queries em banco de dados remoto
    cargas = CargasExecutada.query.options(
        joinedload(CargasExecutada.caminhao),
        joinedload(CargasExecutada.motorista)
    ).all()
    agendas_em_espera = Agenda.query.filter_by(status='espera').options(
        joinedload(Agenda.caminhao),
        joinedload(Agenda.motorista)
    ).order_by(Agenda.data_agendamento.desc()).all()


    # Carregar tipos de carroceria do arquivo
    try:
        with open(os.path.join(basedir, 'mds', 'tpcarroceira.md'), 'r', encoding='utf-8') as f:
            tipos_carroceria = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        tipos_carroceria = []

    ufs = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']
    
    jwt_token = session.get('jwt_token') # Pega o token da sessão

    return render_template('cadastros.html', 
                           caminhoes=caminhoes, 
                           motoristas=motoristas, 
                           cargas=cargas, 
                           agendas=agendas_em_espera,
                           tipos_carroceria=tipos_carroceria,
                           ufs=ufs,
                           active_tab=tab,
                           jwt_token=jwt_token) # Passa o token para o template

@app.route('/relatorios')
def relatorios():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    active_view = request.args.get('view', 'overview')
    
    context = {
        'active_view': active_view,
        'stats': {},
        'monthly_agendamentos_data': [],
        'monthly_agendamentos_chart_data': {'labels': [], 'data': []},
        'motoristas_ativos_data': [],
        'caminhoes_por_tipo_data': [],
        'caminhoes_por_tipo_chart_data': {'labels': [], 'data': []},
        'top_destinos_data': []
    }

    # Dados para a Visão Geral e Dashboard Operacional
    if active_view == 'overview':
        context['stats']['total_motoristas'] = Motorista.query.count()
        context['stats']['total_caminhoes'] = Caminhao.query.count()
        
        # Agendamentos do mês atual
        hoje = datetime.now()
        primeiro_dia_mes = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        agendamentos_mes_atual_count = Agenda.query.filter(Agenda.data_agendamento >= primeiro_dia_mes).count()
        context['stats']['agendamentos_mes_atual'] = agendamentos_mes_atual_count

        # Agendamentos mensais para o gráfico
        monthly_agendamentos = db.session.query(
            db.func.to_char(Agenda.data_agendamento, 'YYYY-MM').label('mes'),
            db.func.count(Agenda.id).label('total')
        ).group_by('mes').order_by('mes').all()

        labels = [item.mes for item in monthly_agendamentos]
        data = [item.total for item in monthly_agendamentos]
        context['monthly_agendamentos_chart_data'] = {'labels': labels, 'data': data}

        # Caminhões por tipo de carroceria para o gráfico
        caminhoes_por_tipo = db.session.query(
            Caminhao.tipo_carroceria,
            db.func.count(Caminhao.id).label('total')
        ).group_by(Caminhao.tipo_carroceria).all()

        tipo_labels = [item.tipo_carroceria if item.tipo_carroceria else 'Não Definido' for item in caminhoes_por_tipo]
        tipo_data = [item.total for item in caminhoes_por_tipo]
        context['caminhoes_por_tipo_chart_data'] = {'labels': tipo_labels, 'data': tipo_data}

    # Dados para Agendamentos Mensais (se for uma view separada)
    if active_view == 'agendamentos_mensais':
        monthly_agendamentos = db.session.query(
            db.func.to_char(Agenda.data_agendamento, 'YYYY-MM').label('mes'),
            db.func.count(Agenda.id).label('total')
        ).group_by('mes').order_by('mes').all()
        context['monthly_agendamentos_data'] = [{'mes': item.mes, 'total': item.total} for item in monthly_agendamentos]

    # Dados para Motoristas Ativos
    if active_view == 'motoristas_ativos':
        # Motoristas que têm pelo menos um agendamento com status 'espera' ou 'em_andamento'
        motoristas_ativos = db.session.query(
            Motorista.nome,
            Motorista.cpf,
            Motorista.telefone,
            db.func.count(Agenda.id).label('count')
        ).join(Agenda).filter(
            Agenda.status.in_(['espera', 'em_andamento'])
        ).group_by(Motorista.id).order_by(db.func.count(Agenda.id).desc()).all()
        
        context['motoristas_ativos_data'] = [{'nome': m.nome, 'cpf': m.cpf, 'telefone': m.telefone, 'count': m.count} for m in motoristas_ativos]

    # Dados para Caminhões por Tipo
    if active_view == 'caminhoes_por_tipo':
        caminhoes_por_tipo = db.session.query(
            Caminhao.tipo_carroceria,
            db.func.count(Caminhao.id).label('count')
        ).group_by(Caminhao.tipo_carroceria).order_by(db.func.count(Caminhao.id).desc()).all()
        context['caminhoes_por_tipo_data'] = [{'tipo_carroceria': item.tipo_carroceria if item.tipo_carroceria else 'Não Definido', 'count': item.count} for item in caminhoes_por_tipo]

    # Dados para Top Destinos
    if active_view == 'top_destinos':
        top_destinos = db.session.query(
            Agenda.fertipar_destino,
            db.func.count(Agenda.id).label('count')
        ).group_by(Agenda.fertipar_destino).order_by(db.func.count(Agenda.id).desc()).limit(10).all()
        context['top_destinos_data'] = [{'destino': item.fertipar_destino, 'count': item.count} for item in top_destinos]

    return render_template('relatorios.html', **context)

@app.route('/administracao')
def administracao():
    if 'user_id' not in session:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('cadastros'))
    
    # Determine the default tab based on user role
    if session.get('user_role') == 'admin':
        tab = request.args.get('tab', 'configuracoes') # Default to 'configuracoes' for admin
    else:
        tab = request.args.get('tab', 'historico-robo') # Default to 'historico-robo' for non-admin
    
    usuarios = Usuario.query.all()
    configuracao = ConfiguracaoRobo.query.first() # Should only be one
    
    return render_template('administracao.html', usuarios=usuarios, configuracao=configuracao, active_tab=tab)

# --- Usuário Routes ---
@app.route('/add_usuario', methods=['POST'])
def add_usuario():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        flash('Você não tem permissão para realizar esta ação.', 'danger')
        return redirect(url_for('cadastros'))
    
    username = request.form['username']
    password = request.form['password']
    confirm_password = request.form['confirm_password']
    nome = request.form['nome']
    email = request.form['email']
    telefone_fixo = request.form.get('telefone_fixo')
    celular = request.form.get('celular')
    role = request.form['role']
    
    if password != confirm_password:
        flash('As senhas não coincidem.', 'danger')
        return redirect(url_for('administracao'))

    if username and password and nome and email and role:
        novo_usuario = Usuario(username=username, nome=nome, email=email, telefone_fixo=telefone_fixo, celular=celular, role=role)
        novo_usuario.set_password(password)
        db.session.add(novo_usuario)
        db.session.commit()
        flash('Usuário adicionado com sucesso!', 'success')
    else:
        flash('Todos os campos obrigatórios (Nome de Usuário, Senha, Nome Completo, E-mail, Permissão) devem ser preenchidos.', 'danger')
        
    return redirect(url_for('administracao', tab='usuarios'))

@app.route('/delete_usuario/<int:id>')
def delete_usuario(id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        flash('Você não tem permissão para realizar esta ação.', 'danger')
        return redirect(url_for('cadastros'))
    
    usuario = Usuario.query.get_or_404(id)
    if usuario.id == session['user_id']: # Prevent deleting own account
        flash('Você não pode deletar sua própria conta!', 'danger')
        return redirect(url_for('administracao'))
    
    db.session.delete(usuario)
    db.session.commit()
    flash('Usuário deletado com sucesso!', 'success')
    return redirect(url_for('administracao', tab='usuarios'))

@app.route('/edit_usuario/<int:id>', methods=['GET', 'POST'])
def edit_usuario(id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('cadastros'))
    
    usuario = Usuario.query.get_or_404(id)
    if request.method == 'POST':
        usuario.username = request.form['username']
        usuario.nome = request.form['nome']
        usuario.email = request.form['email']
        usuario.telefone_fixo = request.form['telefone_fixo']
        usuario.celular = request.form['celular']
        usuario.role = request.form['role']
        if 'password' in request.form and request.form['password'] != '':
            usuario.set_password(request.form['password'])
        db.session.commit()
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('administracao', tab='usuarios'))
    
    return render_template('edit_usuario.html', usuario=usuario)

# --- Configuração Robô Routes ---
@app.route('/salvar_configuracao_robo', methods=['POST'])
def salvar_configuracao_robo():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        flash('Você não tem permissão para realizar esta ação.', 'danger')
        return redirect(url_for('cadastros'))
    
    config = ConfiguracaoRobo.query.first()
    if not config:
        config = ConfiguracaoRobo()
        db.session.add(config)
    
    config.url_acesso = request.form['url_acesso']
    config.filial = request.form['filial']
    config.usuario_site = request.form['usuario_site']
    config.senha_site = request.form['senha_site'] # Store plain text password
    config.email_retorno = request.form['email_retorno']
    config.pagina_raspagem = request.form.get('pagina_raspagem')
    config.contato = request.form.get('contato')
    config.telefone = request.form.get('telefone')
    config.head_evento = 'head_evento' in request.form
    config.modo_execucao = 'agendado' if 'modo_execucao' in request.form else 'teste'
    config.tempo_espera_segundos = request.form.get('tempo_espera_segundos', 30, type=int)
    
    db.session.commit()
    flash('Configuração do robô salva com sucesso!', 'success')
    return redirect(url_for('administracao', tab='configuracoes'))

# --- Caminhao Routes ---
@app.route('/add_caminhao', methods=['POST'])
def add_caminhao():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    placa = request.form.get('placa')
    uf = request.form.get('uf')
    
    if placa and uf:
        novo_caminhao = Caminhao(
            placa=placa, 
            uf=uf,
            tipo_carroceria=request.form.get('tipo_carroceria'),
            placa_reboque1=request.form.get('placa_reboque1'),
            uf1=request.form.get('uf1'),
            placa_reboque2=request.form.get('placa_reboque2'),
            uf2=request.form.get('uf2'),
            placa_reboque3=request.form.get('placa_reboque3'),
            uf3=request.form.get('uf3')
        )
        db.session.add(novo_caminhao)
        db.session.commit()
        flash('Caminhão adicionado com sucesso!', 'success')
    else:
        flash('Campos obrigatórios (Placa, UF) não foram preenchidos.', 'danger')
        
    return redirect(url_for('cadastros', tab='caminhoes'))

@app.route('/delete_caminhao/<int:id>')
def delete_caminhao(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    caminhao = Caminhao.query.get_or_404(id)
    db.session.delete(caminhao)
    db.session.commit()
    flash('Caminhão deletado com sucesso!', 'success')
    return redirect(url_for('cadastros', tab='caminhoes'))

@app.route('/edit_caminhao/<int:id>', methods=['GET', 'POST'])
def edit_caminhao(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    caminhao = Caminhao.query.get_or_404(id)
    if request.method == 'POST':
        caminhao.placa = request.form.get('placa')
        caminhao.uf = request.form.get('uf')
        caminhao.tipo_carroceria = request.form.get('tipo_carroceria')
        caminhao.placa_reboque1 = request.form.get('placa_reboque1')
        caminhao.uf1 = request.form.get('uf1')
        caminhao.placa_reboque2 = request.form.get('placa_reboque2')
        caminhao.uf2 = request.form.get('uf2')
        caminhao.placa_reboque3 = request.form.get('placa_reboque3')
        caminhao.uf3 = request.form.get('uf3')
        db.session.commit()
        flash('Caminhão atualizado com sucesso!', 'success')
        return redirect(url_for('cadastros', tab='caminhoes'))
    
    try:
        with open(os.path.join(basedir, 'mds', 'tpcarroceira.md'), 'r', encoding='utf-8') as f:
            tipos_carroceria = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        tipos_carroceria = []
    ufs = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']
    
    return render_template('edit_caminhao.html', caminhao=caminhao, tipos_carroceria=tipos_carroceria, ufs=ufs)

# --- Motorista Routes ---
@app.route('/add_motorista', methods=['POST'])
def add_motorista():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    nome = request.form.get('nome')
    cpf = request.form.get('cpf')
    if nome and cpf:
        novo_motorista = Motorista(
            nome=nome, 
            cpf=cpf,
            telefone=request.form.get('telefone'),
            endereco=request.form.get('endereco'),
            cidade=request.form.get('cidade'),
            uf=request.form.get('uf')
        )
        db.session.add(novo_motorista)
        db.session.commit()
        flash('Motorista adicionado com sucesso!', 'success')
    else:
        flash('Campos Nome e CPF são obrigatórios.', 'danger')
    return redirect(url_for('cadastros', tab='motoristas'))

@app.route('/delete_motorista/<int:id>')
def delete_motorista(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    motorista = Motorista.query.get_or_404(id)
    db.session.delete(motorista)
    db.session.commit()
    flash('Motorista deletado com sucesso!', 'success')
    return redirect(url_for('cadastros', tab='motoristas'))

@app.route('/edit_motorista/<int:id>', methods=['GET', 'POST'])
def edit_motorista(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    motorista = Motorista.query.get_or_404(id)
    if request.method == 'POST':
        motorista.nome = request.form.get('nome')
        motorista.cpf = request.form.get('cpf')
        motorista.telefone = request.form.get('telefone')
        motorista.endereco = request.form.get('endereco')
        motorista.cidade = request.form.get('cidade')
        motorista.uf = request.form.get('uf')
        db.session.commit()
        flash('Motorista atualizado com sucesso!', 'success')
        return redirect(url_for('cadastros', tab='motoristas'))
    
    ufs = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']
    return render_template('edit_motorista.html', motorista=motorista, ufs=ufs)
    
# --- Cargas Routes ---
@app.route('/add_carga', methods=['POST'])
def add_carga():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    descricao = request.form.get('descricao')
    data = request.form.get('data')
    caminhao_id = request.form.get('caminhao_id')
    motorista_id = request.form.get('motorista_id')

    if descricao and data and caminhao_id and motorista_id:
        nova_carga = CargasExecutada(
            descricao=descricao, 
            data=data, 
            caminhao_id=caminhao_id, 
            motorista_id=motorista_id
        )
        db.session.add(nova_carga)
        db.session.commit()
        flash('Carga adicionada com sucesso!', 'success')
    else:
        flash('Todos os campos são obrigatórios.', 'danger')
        
    return redirect(url_for('cadastros', tab='cargas'))

# --- Agenda Routes ---
@app.route('/agendar', methods=['POST'])
@token_required
def agendar(current_user):
    data = request.get_json()
    motorista_id = data.get('motorista_id')
    caminhao_id = data.get('caminhao_id')
    fertipar_item = data.get('fertipar_item')
    carga_solicitada = data.get('carga_solicitada') # Captura o novo campo

    if not all([motorista_id, caminhao_id, fertipar_item]):
        return jsonify({'success': False, 'message': 'Todos os campos são obrigatórios: Motorista, Caminhão e Item Fertipar.'}), 400

    # Verificar se já existe uma agenda para este motorista com status 'espera'
    existing_agenda_motorista = Agenda.query.filter_by(
        motorista_id=motorista_id,
        status='espera'
    ).first()
    if existing_agenda_motorista:
        return jsonify({'success': False, 'message': 'Este motorista já possui uma agenda em espera. Não é possível criar outra.'}), 409

    # Verificar se já existe uma agenda para este protocolo (mantém a validação existente)
    protocolo = fertipar_item.get('Protocolo')
    if Agenda.query.filter_by(fertipar_protocolo=protocolo).first():
        return jsonify({'success': False, 'message': f'Já existe um agendamento para o protocolo {protocolo}.'}), 409


    try:
        nova_agenda = Agenda(
            motorista_id=motorista_id,
            caminhao_id=caminhao_id,
            fertipar_protocolo=protocolo,
            fertipar_pedido=fertipar_item.get('Pedido'),
            fertipar_destino=fertipar_item.get('Destino'),
            fertipar_data=fertipar_item.get('Data'),
            fertipar_qtde=fertipar_item.get('Qtde.'),
            carga_solicitada=carga_solicitada # Salva o novo campo
        )
        db.session.add(nova_agenda)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Agendamento criado com sucesso!', 'agenda': nova_agenda.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro ao salvar no banco de dados: {str(e)}'}), 500


@app.route('/api/agenda/<int:agenda_id>', methods=['DELETE'])
@token_required
def delete_agenda_api(current_user, agenda_id):
    agenda = Agenda.query.get(agenda_id)
    if not agenda:
        return jsonify({"success": False, "message": "Agenda não encontrada"}), 404
    
    try:
        db.session.delete(agenda)
        db.session.commit()
        return jsonify({"success": True, "message": "Agenda cancelada com sucesso"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Erro ao cancelar agenda: {str(e)}"}), 500


@app.route('/delete_carga/<int:id>')
def delete_carga(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    carga = CargasExecutada.query.get_or_404(id)
    db.session.delete(carga)
    db.session.commit()
    flash('Carga deletada com sucesso!', 'success')
    return redirect(url_for('cadastros', tab='cargas'))

# --- API Login Route ---
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Usuário e senha são necessários'}), 400

    username = data['username']
    password = data['password']

    user = Usuario.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({'message': 'Credenciais inválidas!'}), 401

    token = jwt.encode({
        'id': user.id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm="HS256")

    return jsonify({
        'token': token,
        'user': {
            'nome': user.nome,
            'role': user.role,
            'foto_perfil': user.foto_perfil
        }
    })

# --- API Routes ---
@app.route('/api/motoristas', methods=['GET'])
def get_motoristas():
    motoristas = Motorista.query.all()
    motoristas_data = [{"id": m.id, "nome": m.nome, "cpf": m.cpf, "telefone": m.telefone} for m in motoristas]
    return jsonify(motoristas_data)

@app.route('/api/caminhoes', methods=['GET'])
def get_caminhoes():
    caminhoes = Caminhao.query.all()
    caminhoes_data = [{"id": c.id, "placa": c.placa, "uf": c.uf, "tipo_carroceria": c.tipo_carroceria} for c in caminhoes]
    return jsonify(caminhoes_data)

@app.route('/api/scrape_fertipar_data', methods=['GET'])
def api_scrape_fertipar_data():
    configuracao = ConfiguracaoRobo.query.first()
    if not configuracao:
        return jsonify({
            "success": False,
            "message": "Configuração do robô não encontrada. Por favor, configure o robô na página de administração."
        }), 404

    try:
        # No decryption needed, password is plain text
        scraped_data, error_message = asyncio.run(scrape_fertipar_data(configuracao))
        
        if error_message:
            # Trata a condição de "site bloqueado" como um status informativo, não um erro.
            if error_message == "Dados Não coletados, site já bloqueado!":
                return jsonify({
                    "success": True, 
                    "data": [],
                    "message": error_message
                })
            else:
                # Outros erros são erros reais do servidor/raspagem.
                return jsonify({"success": False, "message": error_message}), 500
        
        elif scraped_data:
            return jsonify({"success": True, "data": scraped_data})
        else:
            return jsonify({
                "success": True,
                "data": [],
                "message": "Nenhum dado encontrado para os filtros aplicados."
            })

    except Exception as e:
        app.logger.error(f"Erro na api_scrape_fertipar_data: {e}")
        return jsonify({
            "success": False, 
            "message": f"Não foi possível buscar os dados da Fertipar. Verifique a configuração do robô e se o site está acessível. Erro: {str(e)}"
        }), 500

@app.route('/api/agendas_em_espera', methods=['GET'])
def api_agendas_em_espera():
    agendas = Agenda.query.filter_by(status='espera').order_by(Agenda.data_agendamento.desc()).all()
    return jsonify([agenda.to_dict() for agenda in agendas])

@app.route('/api/teste_robo_config', methods=['POST'])
@token_required
def teste_robo_config(current_user):
    try:
        # Recebe os dados JSON do corpo da requisição
        request_data = request.get_json()
        select_data_from_frontend = request_data.get('select_data')

        # Busca a configuração do robô no banco de dados
        configuracao_db = ConfiguracaoRobo.query.first()
        if not configuracao_db:
            return jsonify({'success': False, 'message': 'Configuração do robô não encontrada.'}), 404

        # Converte o objeto ConfiguracaoRobo para um dicionário
        config_data = {
            'url_acesso': configuracao_db.url_acesso,
            'filial': configuracao_db.filial,
            'usuario_site': configuracao_db.usuario_site,
            'senha_site': configuracao_db.get_senha_site(), # Decrypt password for testing output
            'email_retorno': configuracao_db.email_retorno,
            'pagina_raspagem': configuracao_db.pagina_raspagem,
            'contato': configuracao_db.contato,
            'telefone': configuracao_db.telefone,
            'head_evento': configuracao_db.head_evento,
            'tempo_espera_segundos': configuracao_db.tempo_espera_segundos,
            'modo_execucao': configuracao_db.modo_execucao
        }

        # Unifica os dois JSONs em um único objeto para impressão
        unified_json = {
            'configuracao_robo': config_data,
            'dados_formulario': select_data_from_frontend
        }

        # Imprime o JSON unificado no console do servidor Flask
        print("\n--- JSON UNIFICADO DE DADOS PARA ANÁLISE ---")
        print(json.dumps(unified_json, indent=2))
        print("---------------------------------------------")

        return jsonify({'success': True, 'message': 'JSON unificado de dados impresso no console do servidor.'})

    except Exception as e:
        print(f"Erro ao testar a configuração do robô: {e}")
        return jsonify({'success': False, 'message': f'Erro interno do servidor: {str(e)}'}), 500

@app.route('/dashboard_decisao')
def dashboard_decisao():
    if 'user_id' not in session:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('login'))
    
    # KPIs Gerais
    total_motoristas = Motorista.query.count()
    total_caminhoes = Caminhao.query.count()
    total_agendamentos = Agenda.query.count()

    # Agendamentos por Mês (Atual e Anterior)
    hoje = datetime.now()
    
    # Mês atual
    primeiro_dia_mes_atual = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    agendamentos_mes_atual = Agenda.query.filter(Agenda.data_agendamento >= primeiro_dia_mes_atual).count()

    # Mês anterior
    primeiro_dia_mes_anterior = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    agendamentos_mes_anterior = Agenda.query.filter(
        Agenda.data_agendamento >= primeiro_dia_mes_anterior,
        Agenda.data_agendamento < primeiro_dia_mes_atual
    ).count()

    # Tendência (Mês atual vs Mês anterior)
    tendencia_agendamentos = 0
    if agendamentos_mes_anterior > 0:
        tendencia_agendamentos = ((agendamentos_mes_atual - agendamentos_mes_anterior) / agendamentos_mes_anterior) * 100

    # Top 5 Motoristas por Agendamentos
    top_motoristas = db.session.query(
        Motorista.nome,
        db.func.count(Agenda.id).label('total_agendamentos')
    ).join(Agenda).group_by(Motorista.nome).order_by(db.func.count(Agenda.id).desc()).limit(5).all()

    # Top 5 Destinos por Agendamentos
    top_destinos = db.session.query(
        Agenda.fertipar_destino,
        db.func.count(Agenda.id).label('total_agendamentos')
    ).group_by(Agenda.fertipar_destino).order_by(db.func.count(Agenda.id).desc()).limit(5).all()

    # Agendamentos nos últimos 12 meses para gráfico de tendência
    data_12_meses_atras = (hoje - timedelta(days=365)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    agendamentos_ultimos_12_meses = db.session.query(
        db.func.to_char(Agenda.data_agendamento, 'YYYY-MM').label('mes'),
        db.func.count(Agenda.id).label('total')
    ).filter(Agenda.data_agendamento >= data_12_meses_atras).group_by('mes').order_by('mes').all()

    agendamentos_12m_labels = [item.mes for item in agendamentos_ultimos_12_meses]
    agendamentos_12m_data = [item.total for item in agendamentos_ultimos_12_meses]

    context = {
        'total_motoristas': total_motoristas,
        'total_caminhoes': total_caminhoes,
        'total_agendamentos': total_agendamentos,
        'agendamentos_mes_atual': agendamentos_mes_atual,
        'agendamentos_mes_anterior': agendamentos_mes_anterior,
        'tendencia_agendamentos': round(tendencia_agendamentos, 2),
        'top_motoristas': top_motoristas,
        'top_destinos': top_destinos,
        'agendamentos_12m_labels': agendamentos_12m_labels,
        'agendamentos_12m_data': agendamentos_12m_data
    }
    
    return render_template('dashboard_decisao.html', **context)

