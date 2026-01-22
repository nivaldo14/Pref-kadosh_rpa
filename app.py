from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, extract
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import OperationalError
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
import os
import asyncio
import sys
import base64
import traceback
import json

basedir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(basedir, 'backend'))

from rpa_service import scrape_fertipar_data, monitor_agendamento_status
from rpa_task_processor import process_agendamento_main_task

from datetime import datetime, timedelta, timezone
from functools import wraps

from dotenv import load_dotenv

load_dotenv()

# --- DEBUGGING ---
print("--- Checking Environment Variables ---")
print(f"DB_USER from env: {os.getenv('DB_USER')}")
print(f"DB_HOST from env: {os.getenv('DB_HOST')}")
print(f"DB_NAME from env: {os.getenv('DB_NAME')}")
print("------------------------------------")
# --- END DEBUGGING ---

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'supersecretkey_fallback_for_dev')
db_user = os.getenv('DB_USER', 'postgres')
db_pass = os.getenv('DB_PASS', 'root')
db_host = os.getenv('DB_HOST', 'localhost')
db_port = os.getenv('DB_PORT', '5432')
db_name = os.getenv('DB_NAME', 'dbkadosh')
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?client_encoding=utf8'
print(f"DEBUG DB URI: {app.config['SQLALCHEMY_DATABASE_URI']}") # Added this line
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

APP_VERSION = datetime.now(timezone.utc).strftime("1.0.%y%m%d%H%M")

db = SQLAlchemy(app)
migrate = Migrate(app, db)


# --- Authentication Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify(error="Não autorizado"), 401
            flash('Você precisa estar logado para ver esta página.', 'warning')
            return redirect(url_for('login'))
        
        user = db.session.get(Usuario, session['user_id'])
        if user is None:
            session.pop('user_id', None)
            if request.path.startswith('/api/'):
                return jsonify(error="Sessão inválida"), 401
            flash('Sessão de usuário inválida. Faça login novamente.', 'warning')
            return redirect(url_for('login'))

        g.user = user
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'): return jsonify(error="Não autorizado"), 401
            flash('Você precisa estar logado para ver esta página.', 'warning')
            return redirect(url_for('login'))
        
        user = db.session.get(Usuario, session['user_id'])
        if user is None:
            session.pop('user_id', None)
            if request.path.startswith('/api/'): return jsonify(error="Sessão inválida"), 401
            flash('Sessão de usuário inválida. Faça login novamente.', 'warning')
            return redirect(url_for('login'))

        if user.role not in ['admin', 'dev']:
            if request.path.startswith('/api/'): return jsonify(error="Permissão de administrador necessária"), 403
            flash('Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('dashboard'))
        
        g.user = user
        return f(*args, **kwargs)
    return decorated_function

def dev_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'): return jsonify(error="Não autorizado"), 401
            flash('Você precisa estar logado para ver esta página.', 'warning')
            return redirect(url_for('login'))
        
        user = db.session.get(Usuario, session['user_id'])
        if user is None:
            session.pop('user_id', None)
            if request.path.startswith('/api/'): return jsonify(error="Sessão inválida"), 401
            flash('Sessão de usuário inválida. Faça login novamente.', 'warning')
            return redirect(url_for('login'))

        if user.role != 'dev':
            if request.path.startswith('/api/'): return jsonify(error="Permissão de desenvolvedor necessária"), 403
            flash('Você não tem permissão para executar esta ação.', 'danger')
            return redirect(request.referrer or url_for('dashboard'))
        
        g.user = user
        return f(*args, **kwargs)
    return decorated_function



# --- Database Models ---
class Usuario(db.Model):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    telefone_fixo = db.Column(db.String(20))
    celular = db.Column(db.String(20))
    foto_perfil = db.Column(db.String(200), default='default.jpg')
    role = db.Column(db.String(20), nullable=False, default='user')
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Motorista(db.Model):
    __tablename__ = 'motorista'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(20), unique=True, nullable=False)
    telefone = db.Column(db.String(20))
    endereco = db.Column(db.String(200))
    cidade = db.Column(db.String(100))
    uf = db.Column(db.String(2))

class Caminhao(db.Model):
    __tablename__ = 'caminhao'
    id = db.Column(db.Integer, primary_key=True)
    placa = db.Column(db.String(10), unique=True, nullable=False)
    uf = db.Column(db.String(2), nullable=False)
    tipo_carroceria = db.Column(db.String(50))
    placa_reboque1 = db.Column(db.String(10))
    uf1 = db.Column(db.String(2))
    placa_reboque2 = db.Column(db.String(10))
    uf2 = db.Column(db.String(2))
    placa_reboque3 = db.Column(db.String(10))
    uf3 = db.Column(db.String(2))

class Agenda(db.Model):
    # ... (columns are the same)
    id = db.Column(db.Integer, primary_key=True)
    motorista_id = db.Column(db.Integer, db.ForeignKey('motorista.id'), nullable=False)
    caminhao_id = db.Column(db.Integer, db.ForeignKey('caminhao.id'), nullable=False)
    fertipar_protocolo = db.Column(db.String(100), nullable=False, unique=True)
    fertipar_pedido = db.Column(db.String(100))
    fertipar_destino = db.Column(db.String(100))
    fertipar_data = db.Column(db.String(50))
    fertipar_qtde = db.Column(db.String(50))
    fertipar_embalagem = db.Column(db.String(100), nullable=True)
    carga_solicitada = db.Column(db.Numeric(precision=10, scale=2), nullable=True)
    status = db.Column(db.String(50), nullable=False, default='espera')
    data_agendamento = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    motorista = db.relationship('Motorista', backref=db.backref('agendas', lazy=True))
    caminhao = db.relationship('Caminhao', backref=db.backref('agendas', lazy=True))

    def to_dict(self, for_socket=False):
        motorista_info = self.motorista.nome
        if self.motorista.cpf:
            motorista_info += f" ({self.motorista.cpf})"
        elif self.motorista.telefone:
            motorista_info += f" ({self.motorista.telefone})"
            
        caminhao_obj = self.caminhao
        reboques_list = []
        if caminhao_obj.placa_reboque1:
            reboques_list.append(f"Reb1: {caminhao_obj.placa_reboque1} ({caminhao_obj.uf1 or ''})")
        if caminhao_obj.placa_reboque2:
            reboques_list.append(f"Reb2: {caminhao_obj.placa_reboque2} ({caminhao_obj.uf2 or ''})")
        if caminhao_obj.placa_reboque3:
            reboques_list.append(f"Reb3: {caminhao_obj.placa_reboque3} ({caminhao_obj.uf3 or ''})")

        caminhao_data = {
            "placa": f"{caminhao_obj.placa} ({caminhao_obj.uf})",
            "tipo_carroceria": caminhao_obj.tipo_carroceria,
            "reboques": reboques_list
        }
        
        # For UI rendering in the table, we need a simple string.
        # For the DADOSBOT JSON, we use the structured object.
        caminhao_display = f"{caminhao_data['placa']}"
        if caminhao_data['tipo_carroceria']:
            caminhao_display += f" - {caminhao_data['tipo_carroceria']}"
        if caminhao_data['reboques']:
            caminhao_display += f" | {', '.join(caminhao_data['reboques'])}"

        return {
            'id': self.id,
            'motorista': motorista_info,
            'caminhao': caminhao_display if for_socket else caminhao_data,
            'protocolo': self.fertipar_protocolo,
            'pedido': self.fertipar_pedido,
            'destino': self.fertipar_destino,
            'status': self.status,
            'data_agendamento': self.data_agendamento.strftime('%d/%m/%Y %H:%M'),
            'carga_solicitada': float(self.carga_solicitada) if self.carga_solicitada else None
        }



class ConfiguracaoRobo(db.Model):
    __tablename__ = 'configuracao_robo'
    id = db.Column(db.Integer, primary_key=True)
    url_acesso = db.Column(db.String(255), nullable=False)
    filial = db.Column(db.String(50), nullable=False)
    usuario_site = db.Column(db.String(80), nullable=False)
    # Coluna para armazenar a senha de forma 'criptografada' (codificada em base64)
    senha_site_encrypted = db.Column(db.String(255), nullable=True)
    email_retorno = db.Column(db.String(100), nullable=False)
    pagina_raspagem = db.Column(db.String(255), nullable=True)
    contato = db.Column(db.String(100), nullable=True)
    telefone = db.Column(db.String(20), nullable=True)
    head_evento = db.Column(db.Boolean(), nullable=False, default=False)
    modo_execucao = db.Column(db.String(20), nullable=False, default='teste')
    tempo_espera_segundos = db.Column(db.Integer, nullable=False, default=30)

    def set_senha_site(self, password):
        """Codifica a senha em base64 antes de salvar."""
        if password:
            self.senha_site_encrypted = base64.b64encode(password.encode('utf-8')).decode('utf-8')

    @property
    def senha_site(self):
        """Decodifica a senha de base64 para uso pelo robô."""
        if self.senha_site_encrypted:
            return base64.b64decode(self.senha_site_encrypted).decode('utf-8')
        return None

    # O método check_senha_site não é mais necessário, pois não estamos usando hashes.

class RpaSessao(db.Model):
    __tablename__ = 'rpa_sessao'
    id = db.Column(db.Integer, primary_key=True, default=1)
    storage_state = db.Column(JSONB)
    last_updated = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        db.CheckConstraint('id = 1', name='single_row_check'),
    )

# --- Routes ---
@app.route('/teste')
def teste():
    return "Teste OK"

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        try:
            user = db.session.get(Usuario, session.get('user_id'))
            if user:
                return redirect(url_for('dashboard'))
            else:
                session.pop('user_id', None)
        except Exception as e:
            with open("flask_error.log", "w") as f:
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write("Error during GET /login (session check):\n")
                traceback.print_exc(file=f)
            traceback.print_exc()
            flash("Ocorreu um erro interno. O administrador foi notificado.", "danger")
            return render_template('login.html', app_version=APP_VERSION, user=None)

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        try:
            user = Usuario.query.filter_by(username=username).first()
            if user and user.check_password(password):
                session['user_id'] = user.id
                flash('Login bem-sucedido!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Usuário ou senha inválidos.', 'danger')
        except Exception as e:
            with open("flask_error.log", "w") as f:
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write("Error during POST /login (login attempt):\n")
                traceback.print_exc(file=f)
            traceback.print_exc()
            flash("Ocorreu um erro interno durante o login. O administrador foi notificado.", "danger")
        
        return redirect(url_for('login'))
    
    # Para requisições GET
    return render_template('login.html', app_version=APP_VERSION, user=None)

@app.route('/dashboard')
@login_required
def dashboard():
    user = g.user

    # Basic KPIs
    total_motoristas = db.session.query(func.count(Motorista.id)).scalar()
    total_caminhoes = db.session.query(func.count(Caminhao.id)).scalar()
    total_agendamentos = db.session.query(func.count(Agenda.id)).scalar()

    # Monthly KPIs
    today = datetime.now(timezone.utc)
    # Current month
    first_day_current_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # To get next month, add 32 days to current date and then replace day with 1.
    next_month_estimate = first_day_current_month + timedelta(days=32)
    first_day_next_month = next_month_estimate.replace(day=1)
    
    agendamentos_mes_atual = db.session.query(func.count(Agenda.id)).filter(
        Agenda.data_agendamento >= first_day_current_month,
        Agenda.data_agendamento < first_day_next_month
    ).scalar()

    # Previous month
    first_day_previous_month = (first_day_current_month - timedelta(days=1)).replace(day=1)
    
    agendamentos_mes_anterior = db.session.query(func.count(Agenda.id)).filter(
        Agenda.data_agendamento >= first_day_previous_month,
        Agenda.data_agendamento < first_day_current_month
    ).scalar()

    # Trend calculation
    tendencia_agendamentos = 0
    if agendamentos_mes_anterior > 0:
        tendencia_agendamentos = ((agendamentos_mes_atual - agendamentos_mes_anterior) / agendamentos_mes_anterior) * 100
    elif agendamentos_mes_atual > 0:
        tendencia_agendamentos = 100

    # Top 5 Motoristas
    top_motoristas = db.session.query(
        Motorista.nome,
        func.count(Agenda.id).label('total_agendamentos')
    ).join(Agenda, Agenda.motorista_id == Motorista.id)\
     .group_by(Motorista.id)\
     .order_by(func.count(Agenda.id).desc())\
     .limit(5).all()

    # Top 5 Destinos
    top_destinos = db.session.query(
        Agenda.fertipar_destino,
        func.count(Agenda.id).label('total_agendamentos')
    ).filter(Agenda.fertipar_destino.isnot(None))\
     .group_by(Agenda.fertipar_destino)\
     .order_by(func.count(Agenda.id).desc())\
     .limit(5).all()

    # Last 12 months chart data
    agendamentos_12m_labels = []
    agendamentos_12m_data = []
    current_month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    for i in range(12):
        # Calculate the start and end for the month in the iteration
        temp_date = today
        for _ in range(i):
            temp_date = (temp_date.replace(day=1) - timedelta(days=1))
        start_of_month = temp_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


        next_month_estimate = start_of_month + timedelta(days=32)
        end_of_month = next_month_estimate.replace(day=1)

        count = db.session.query(func.count(Agenda.id)).filter(
            Agenda.data_agendamento >= start_of_month,
            Agenda.data_agendamento < end_of_month
        ).scalar()
        
        agendamentos_12m_labels.insert(0, start_of_month.strftime('%m/%Y'))
        agendamentos_12m_data.insert(0, count)

    # Get distinct years for the new summary dropdown
    years_query = db.session.query(extract('year', Agenda.data_agendamento)).distinct().order_by(extract('year', Agenda.data_agendamento).desc())
    available_years = [y[0] for y in years_query.all() if y[0] is not None]


    return render_template(
        'dashboard_decisao.html',
        user=user,
        total_motoristas=total_motoristas,
        total_caminhoes=total_caminhoes,
        total_agendamentos=total_agendamentos,
        agendamentos_mes_atual=agendamentos_mes_atual,
        agendamentos_mes_anterior=agendamentos_mes_anterior,
        tendencia_agendamentos=tendencia_agendamentos,
        top_motoristas=top_motoristas,
        top_destinos=top_destinos,
        agendamentos_12m_labels=agendamentos_12m_labels,
        agendamentos_12m_data=agendamentos_12m_data,
        available_years=available_years
    )

@app.route('/api/resumo_agendamento/<int:year>')
@login_required
def resumo_agendamento(year):
    """
    Provides a summary of schedules for a given year, grouped by month,
    destination city, and packaging.
    """
    try:
        summary_query = db.session.query(
            extract('month', Agenda.data_agendamento).label('mes'),
            Agenda.fertipar_destino.label('cidade'),
            Agenda.fertipar_embalagem.label('embalagem'),
            func.sum(Agenda.carga_solicitada).label('total_carga_solicitada'),
            func.count(Agenda.id).label('total_agendamentos')
        ).filter(extract('year', Agenda.data_agendamento) == year)\
         .group_by('mes', 'cidade', 'embalagem')\
         .order_by('mes', 'cidade', 'embalagem')\
         .all()

        summary_list = [
            {
                "mes": row.mes,
                "cidade": row.cidade,
                "embalagem": row.embalagem,
                "total_carga_solicitada": float(row.total_carga_solicitada) if row.total_carga_solicitada else 0,
                "total_agendamentos": row.total_agendamentos
            } for row in summary_query
        ]
        
        return jsonify(success=True, data=summary_list)

    except OperationalError as e:
        # This might happen if the migration for 'fertipar_embalagem' hasn't been run
        db.session.rollback()
        print(f"ERROR in resumo_agendamento: {e}")
        return jsonify(success=False, message="Erro de banco de dados. A coluna 'fertipar_embalagem' pode não existir. Execute as migrações."), 500
    except Exception as e:
        db.session.rollback()
        print(f"ERROR in resumo_agendamento: {e}")
        return jsonify(success=False, message="Ocorreu um erro ao gerar o resumo."), 500

    
@app.route('/cadastros', methods=['GET'])
@login_required
def cadastros():
    user = g.user
    
    # Data for the forms and tables
    caminhoes = Caminhao.query.order_by(Caminhao.placa).all()
    motoristas = Motorista.query.order_by(Motorista.nome).all()
    
    # Data for dropdowns
    ufs = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']
    tipos_carroceria = ['Cavalo Mecânico', 'Cavalo Mecânico Trucado', 'Toco', 'Truck', 'Bitruck', 'Carreta 2 eixos', 'Carreta 3 eixos', 'Carreta Cavalo Trucado', 'Bitrem', 'Rodotrem']
    
    # Determine active tab
    active_tab = request.args.get('tab', 'caminhoes')

    return render_template('cadastros.html', 
                           user=user,
                           caminhoes=caminhoes,
                           motoristas=motoristas,
                           ufs=ufs,
                           tipos_carroceria=tipos_carroceria,
                                                       active_tab=active_tab)

@app.route('/api/agendas_executadas', methods=['GET'])
@login_required
def get_agendas_executadas():
    try:
        ano = request.args.get('ano', type=int)
        mes = request.args.get('mes', type=int)

        if not ano or not mes:
            return jsonify(success=False, message="Parâmetros 'ano' e 'mes' são obrigatórios."), 400

        # Query agendas, joining with Motorista and Caminhao to get related data
        agendas = db.session.query(
            Agenda, Motorista, Caminhao
        ).join(Motorista, Agenda.motorista_id == Motorista.id
        ).join(Caminhao, Agenda.caminhao_id == Caminhao.id
        ).filter(
            func.extract('year', Agenda.data_agendamento) == ano,
            func.extract('month', Agenda.data_agendamento) == mes
        ).order_by(Agenda.data_agendamento.desc()).all()

        # Format data for JSON response
        results = []
        for agenda, motorista, caminhao in agendas:
            results.append({
                'id': agenda.id,
                'data_agendamento': agenda.data_agendamento.strftime('%d/%m/%Y %H:%M'),
                'motorista_nome': motorista.nome,
                'caminhao_placa': caminhao.placa,
                'fertipar_protocolo': agenda.fertipar_protocolo,
                'fertipar_pedido': agenda.fertipar_pedido,
                'fertipar_destino': agenda.fertipar_destino,
                'peso_carregar': str(agenda.carga_solicitada), # Convert Decimal to string
                'status': agenda.status
            })

        return jsonify(success=True, agendas=results)

    except Exception as e:
        app.logger.error(f"Erro ao buscar agendas executadas: {e}")
        return jsonify(success=False, message="Erro interno ao buscar agendas."), 500

@app.route('/add_caminhao', methods=['POST'])
@login_required
def add_caminhao():
    try:
        new_caminhao = Caminhao(
            placa=request.form['placa'].upper(),
            uf=request.form['uf'],
            tipo_carroceria=request.form.get('tipo_carroceria'),
            placa_reboque1=request.form.get('placa_reboque1', '').upper(),
            uf1=request.form.get('uf1'),
            placa_reboque2=request.form.get('placa_reboque2', '').upper(),
            uf2=request.form.get('uf2'),
            placa_reboque3=request.form.get('placa_reboque3', '').upper(),
            uf3=request.form.get('uf3')
        )
        db.session.add(new_caminhao)
        db.session.commit()
        flash('Caminhão adicionado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao adicionar caminhão: {e}', 'danger')
        
    return redirect(url_for('cadastros', tab='caminhoes'))

@app.route('/add_motorista', methods=['POST'])
@login_required
def add_motorista():
    try:
        new_motorista = Motorista(
            nome=request.form['nome'],
            cpf=request.form['cpf'],
            telefone=request.form.get('telefone'),
            endereco=request.form.get('endereco'),
            cidade=request.form.get('cidade'),
            uf=request.form.get('uf')
        )
        db.session.add(new_motorista)
        db.session.commit()
        flash('Motorista adicionado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao adicionar motorista: {e}', 'danger')

    return redirect(url_for('cadastros', tab='motoristas'))

@app.route('/edit_caminhao/<int:id>')
def edit_caminhao(id):
    flash('Funcionalidade de edição de caminhão ainda não implementada.', 'info')
    return redirect(url_for('cadastros', tab='caminhoes'))

@app.route('/delete_caminhao/<int:id>')
@login_required
def delete_caminhao(id):
    try:
        caminhao = db.session.get(Caminhao, id)
        if caminhao:
            db.session.delete(caminhao)
            db.session.commit()
            flash('Caminhão excluído com sucesso.', 'success')
        else:
            flash('Caminhão não encontrado.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Não foi possível excluir o caminhão, pois ele pode estar associado a uma agenda. Erro: {e}', 'danger')
    return redirect(url_for('cadastros', tab='caminhoes'))


@app.route('/edit_motorista/<int:id>')
def edit_motorista(id):
    flash('Funcionalidade de edição de motorista ainda não implementada.', 'info')
    return redirect(url_for('cadastros', tab='motoristas'))

@app.route('/delete_motorista/<int:id>')
@login_required
def delete_motorista(id):
    try:
        motorista = db.session.get(Motorista, id)
        if motorista:
            db.session.delete(motorista)
            db.session.commit()
            flash('Motorista excluído com sucesso.', 'success')
        else:
            flash('Motorista não encontrado.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Não foi possível excluir o motorista, pois ele pode estar associado a uma agenda. Erro: {e}', 'danger')
    return redirect(url_for('cadastros', tab='motoristas'))

@app.route('/delete_carga/<int:id>')
def delete_carga(id):
    flash('Funcionalidade de exclusão de carga ainda não implementada.', 'info')
    return redirect(url_for('cadastros', tab='cargas'))

@app.route('/api/teste_robo_config', methods=['POST'])
def teste_robo_config():
    return jsonify(success=True, message="Endpoint de teste do robô chamado, mas não implementado.")

@app.route('/administracao')
@login_required
def administracao():
    user = g.user
    active_tab = request.args.get('active_tab', None)
    
    usuarios = db.session.query(Usuario).filter(Usuario.role != 'dev').order_by(Usuario.username).all()
    configuracao = db.session.query(ConfiguracaoRobo).first()
    if not configuracao:
        configuracao = ConfiguracaoRobo(url_acesso='', filial='', usuario_site='', email_retorno='')
        # Note: senha_site_hash is not set here, it must be set via the form
        db.session.add(configuracao)
        db.session.commit()

    return render_template('administracao.html', 
                           user=user,
                           usuarios=usuarios,
                           configuracao=configuracao,
                           session=session,
                           active_tab=active_tab)

@app.route('/add_usuario', methods=['POST'])
@admin_required
def add_usuario():
    try:
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        email = request.form['email']
        
        if password != confirm_password:
            flash('As senhas não coincidem.', 'danger')
            return redirect(url_for('administracao', active_tab='usuarios'))

        if Usuario.query.filter_by(username=username).first():
            flash('Nome de usuário já existe.', 'danger')
            return redirect(url_for('administracao', active_tab='usuarios'))
        
        if Usuario.query.filter_by(email=email).first():
            flash('E-mail já existe.', 'danger')
            return redirect(url_for('administracao', active_tab='usuarios'))

        new_user = Usuario(
            username=username,
            nome=request.form['nome'],
            email=email,
            telefone_fixo=request.form.get('telefone_fixo'),
            celular=request.form.get('celular'),
            role=request.form.get('role', 'user')
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Usuário adicionado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao adicionar usuário: {e}', 'danger')
        
    return redirect(url_for('administracao', active_tab='usuarios'))

@app.route('/edit_usuario/<int:id>')
def edit_usuario(id):
    flash('Funcionalidade de edição de usuário ainda não implementada.', 'info')
    return redirect(url_for('administracao', tab='usuarios'))

@app.route('/delete_usuario/<int:id>')
@admin_required
def delete_usuario(id):
    if id == session['user_id']:
        flash('Você não pode excluir seu próprio usuário.', 'danger')
        return redirect(url_for('administracao', tab='usuarios'))

    try:
        user_to_delete = db.session.get(Usuario, id)
        if user_to_delete:
            db.session.delete(user_to_delete)
            db.session.commit()
            flash('Usuário excluído com sucesso.', 'success')
        else:
            flash('Usuário não encontrado.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir usuário: {e}', 'danger')
    
    return redirect(url_for('administracao', tab='usuarios'))

@app.route('/salvar_configuracao_robo', methods=['POST'])
@admin_required
def salvar_configuracao_robo():
    configuracao = db.session.query(ConfiguracaoRobo).first()
    if not configuracao:
        configuracao = ConfiguracaoRobo()

    try:
        configuracao.url_acesso = request.form['url_acesso']
        configuracao.filial = request.form['filial']
        configuracao.usuario_site = request.form['usuario_site']
        
        new_senha_site = request.form.get('senha_site')
        if new_senha_site:
            configuracao.set_senha_site(new_senha_site)
        
        configuracao.email_retorno = request.form['email_retorno']
        configuracao.pagina_raspagem = request.form.get('pagina_raspagem')
        configuracao.contato = request.form.get('contato')
        configuracao.telefone = request.form.get('telefone')
        configuracao.head_evento = 'head_evento' in request.form
        configuracao.modo_execucao = 'agendado' if 'modo_execucao' in request.form else 'teste'
        configuracao.tempo_espera_segundos = int(request.form.get('tempo_espera_segundos', 30))

        db.session.add(configuracao)
        db.session.commit()
        flash('Configurações do robô salvas com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao salvar configurações do robô: {e}', 'danger')

    return redirect(url_for('administracao', tab='configuracoes'))

@app.route('/api/teste_robo', methods=['POST'])
def api_teste_robo():
    # if 'user_id' not in session:
    #     return jsonify(success=False, message='Não autorizado'), 401
    
    data = request.get_json()
    print("Dados de teste do robô recebidos (API):", data)
    return jsonify(success=True, message="Dados de teste do robô recebidos no servidor.")

@app.route('/relatorios')
@login_required
def relatorios():
    user = g.user
    return render_template('relatorios.html', user=user)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('login'))



# --- API Routes ---
@app.route('/api/agendas_processar') # Renamed from agendas_em_espera
@login_required
def agendas_processar():
    agendas = Agenda.query.filter_by(status='espera').order_by(Agenda.data_agendamento.desc()).all()
    return jsonify([agenda.to_dict() for agenda in agendas])

@app.route('/api/agendas_agendadas') # New endpoint for agendado status
@login_required
def agendas_agendadas():
    try:
        year = request.args.get('year', default=datetime.now().year, type=int)
        month = request.args.get('month', default=datetime.now().month, type=int)

        # Query agendas based on the provided year and month, for all statuses
        agendas = Agenda.query.filter(
            extract('year', Agenda.data_agendamento) == year,
            extract('month', Agenda.data_agendamento) == month
        ).order_by(Agenda.data_agendamento.desc()).all()
        
        return jsonify([agenda.to_dict(for_socket=True) for agenda in agendas])
    except Exception as e:
        print(f"Error in /api/agendas_agendadas: {e}")
        return jsonify(error=str(e)), 500

@app.route('/api/agendas/updates')
@login_required
def agendas_updates():
    # Este endpoint retorna agendas com status diferente de 'espera' para polling
    agendas = Agenda.query.filter(Agenda.status != 'espera').order_by(Agenda.data_agendamento.desc()).all()
    return jsonify([agenda.to_dict() for agenda in agendas])

@app.route('/agendar', methods=['POST'])
@login_required
def agendar():
    data = request.get_json()
    if not data:
        return jsonify(success=False, message='Dados inválidos'), 400

    motorista_id = data.get('motorista_id')
    caminhao_id = data.get('caminhao_id')
    fertipar_item = data.get('fertipar_item')
    carga_solicitada = data.get('carga_solicitada')

    if not all([motorista_id, caminhao_id, fertipar_item]):
        return jsonify(success=False, message='Campos obrigatórios ausentes.'), 400
    
    existing = Agenda.query.filter_by(fertipar_protocolo=fertipar_item.get('Protocolo')).first()
    if existing:
        return jsonify(success=False, message=f'Já existe uma agenda para o protocolo {fertipar_item.get("Protocolo")}.'), 409

    try:
        config = db.session.query(ConfiguracaoRobo).first()
        print("--- DADOS PARA PERSISTIR E EXECUTAR RPA ---")
        print(f"Dados da Agenda Recebidos: {data}")
        if config:
            config_to_print = {
                'id': config.id,
                'url_acesso': config.url_acesso,
                'filial': config.filial,
                'usuario_site': config.usuario_site,
                'email_retorno': config.email_retorno,
                'pagina_raspagem': config.pagina_raspagem,
                'contato': config.contato,
                'telefone': config.telefone,
                'head_evento': config.head_evento,
                'tempo_espera_segundos': config.tempo_espera_segundos,
                'modo_execucao': config.modo_execucao,
                'senha_site_encrypted': '***Criptografada***' # Mask sensitive info
            }
            print(f"Configuracoes do Robo: {config_to_print}")
        else:
            print("Configuracoes do Robo: Nenhuma")

        new_agenda = Agenda(
            motorista_id=motorista_id,
            caminhao_id=caminhao_id,
            fertipar_protocolo=fertipar_item.get('Protocolo'),
            fertipar_pedido=fertipar_item.get('Pedido'),
            fertipar_destino=fertipar_item.get('Destino'),
            fertipar_data=fertipar_item.get('Data'),
            fertipar_qtde=fertipar_item.get('Qtde.'),
            fertipar_embalagem=fertipar_item.get('Embalagem'),
            carga_solicitada=carga_solicitada,
            status='espera'
        )
        db.session.add(new_agenda)
        db.session.commit()
        
        agenda_data = new_agenda.to_dict()
        
        return jsonify(success=True, message='Agenda criada com sucesso!', agenda=agenda_data), 201
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao criar agenda: {e}")
        return jsonify(success=False, message=f'Erro interno do servidor: {e}'), 500

@app.route('/api/scrape_fertipar_data')
@login_required
def scrape_data():
    # Carrega a configuração do robô do banco de dados
    config = db.session.query(ConfiguracaoRobo).first()
    if not config:
        return jsonify({'success': False, 'message': 'Configuração do robô não encontrada.'}), 500
        
    # Verifica se a senha está configurada
    if not config.senha_site:
        return jsonify({'success': False, 'message': 'A senha para o site da Fertipar não está configurada.'}), 500

    try:
        # Executa a função de scraping assíncrona em um loop de eventos
        data = asyncio.run(scrape_fertipar_data(config))
        
        if data is None:
             return jsonify({'success': False, 'message': 'Dados não coletados. O site pode estar bloqueado ou a estrutura mudou.'})
        
        # Se a raspagem retornou uma lista vazia, significa que não havia dados disponíveis.
        if not data:
            return jsonify({'success': True, 'message': 'Nenhuma cotação disponível no momento.', 'data': []})
            
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        # Log do erro detalhado em um arquivo para depuração
        tb_str = traceback.format_exc()
        error_log_message = f"--- ERRO EM {datetime.now()} ---\n"
        error_log_message += f"Erro na rota /api/scrape_fertipar_data: {e}\n"
        error_log_message += f"Traceback:\n{tb_str}\n"
        
        # Use um caminho de arquivo temporário seguro se possível
        log_file_path = os.path.join(os.path.dirname(__file__), 'scraping_error.log')
        try:
            with open(log_file_path, "a", encoding='utf-8') as f:
                f.write(error_log_message)
        except Exception as log_e:
            print(f"Erro ao escrever no arquivo de log: {log_e}")
            
        # Resposta para o cliente
        print(f"Erro inesperado durante o scraping. Detalhes em {log_file_path}: {e}")
        return jsonify({
            'success': False, 
            'message': f'Ocorreu um erro interno no servidor. Consulte o arquivo scraping_error.log para detalhes técnicos.'
        }), 500

@app.route('/api/agenda/<int:agenda_id>', methods=['DELETE'])
@login_required
def delete_agenda(agenda_id):
    agenda = db.session.get(Agenda, agenda_id)
    if not agenda:
        return jsonify(success=False, message='Agenda não encontrada'), 404
        
    try:
        db.session.delete(agenda)
        db.session.commit()
        return jsonify(success=True, message='Agenda cancelada com sucesso!')
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message=f'Erro ao cancelar agenda: {e}'), 500

@app.route('/api/motoristas')
@login_required
def get_motoristas():
    motoristas = Motorista.query.all()
    return jsonify([{'id': m.id, 'nome': m.nome, 'cpf': m.cpf, 'telefone': m.telefone} for m in motoristas])

@app.route('/api/caminhoes')
@login_required
def get_caminhoes():
    caminhoes = Caminhao.query.all()
    return jsonify([{
        'id': c.id, 'placa': c.placa, 'uf': c.uf, 'tipo_carroceria': c.tipo_carroceria,
        'placa_reboque1': c.placa_reboque1, 'uf1': c.uf1,
        'placa_reboque2': c.placa_reboque2, 'uf2': c.uf2,
        'placa_reboque3': c.placa_reboque3, 'uf3': c.uf3
    } for c in caminhoes])

@app.route('/api/agendas/clear', methods=['POST'])
@dev_required
def clear_agendas():
    try:
        num_deleted = db.session.query(Agenda).filter_by(status='espera').delete(synchronize_session=False)
        db.session.commit()
        return jsonify(success=True, message=f'{num_deleted} agendamentos em espera foram limpos.')
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message=f'Erro ao limpar agendamentos: {e}'), 500

@app.route('/api/agendas/monitor_status', methods=['POST'])
@dev_required # Or @login_required
def monitor_status_task():
    """
    Triggers the RPA task to monitor an order's status.
    """
    data = request.get_json()
    protocolo = data.get('protocolo')
    pedido = data.get('pedido')

    if not all([protocolo, pedido]):
        return jsonify(success=False, message="Protocolo e Pedido são obrigatórios."), 400

    config_db = db.session.query(ConfiguracaoRobo).first()
    if not config_db:
        return jsonify(success=False, message="Configuração do robô não encontrada."), 500
        
    sessao_rpa = db.session.query(RpaSessao).first()
    storage_state = sessao_rpa.storage_state if sessao_rpa else None

    # Structure params for the RPA function
    rpa_config_params = {
        "url_acesso": config_db.url_acesso,
        "filial": config_db.filial,
        "usuario_site": config_db.usuario_site,
        "senha_site": config_db.senha_site,
        "head_evento": config_db.head_evento,
        "storage_state": storage_state
    }
    
    try:
        # Run the monitoring task
        result = asyncio.run(monitor_agendamento_status(rpa_config_params, protocolo, pedido))

        # Save new session state if login happened
        new_storage_state = result.get('new_storage_state')
        if new_storage_state:
            if sessao_rpa:
                sessao_rpa.storage_state = new_storage_state
                sessao_rpa.last_updated = datetime.now(timezone.utc)
            else:
                sessao_rpa = RpaSessao(storage_state=new_storage_state)
                db.session.add(sessao_rpa)
            db.session.commit()

        return jsonify(result)

    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, status="ERRO", message=f"Erro interno do servidor ao monitorar status: {e}"), 500
        
@app.route('/api/agendas/execute/<int:agenda_id>', methods=['POST'])
@dev_required
def execute_agenda_task(agenda_id):
    """
    Executes the Playwright RPA task for a specific agenda item.
    Handles loading and saving of the RPA session state.
    """
    print(f"--- Iniciando execute_agenda_task para agenda_id: {agenda_id} ---")
    agenda = db.session.get(Agenda, agenda_id)
    if not agenda:
        return jsonify(success=False, message="Agenda não encontrada."), 404

    config = db.session.query(ConfiguracaoRobo).first()
    if not config:
        return jsonify(success=False, message="Configuração do robô não encontrada."), 500

    motorista = db.session.get(Motorista, agenda.motorista_id)
    caminhao = db.session.get(Caminhao, agenda.caminhao_id)

    if not motorista or not caminhao:
        return jsonify(success=False, message="Motorista ou Caminhão da agenda não encontrados."), 404

    # --- LÓGICA DE SESSÃO: Carregar estado do banco de dados ---
    print("--- Carregando estado de sessão do RPA do banco de dados... ---")
    sessao_rpa = db.session.query(RpaSessao).first()
    storage_state = sessao_rpa.storage_state if sessao_rpa else None
    if storage_state:
        print("Estado de sessão encontrado.")
    else:
        print("Nenhum estado de sessão encontrado. Será necessário um novo login.")


    # --- Estruturar todos os dados em um único dicionário (JSON) ---
    rpa_params = {
        "config": {
            "url_acesso": config.url_acesso,
            "filial": config.filial,
            "usuario_site": config.usuario_site,
            "senha_site": config.senha_site, # senha_site é uma property que decodifica o valor
            "email_retorno": config.email_retorno,
            "pagina_raspagem": config.pagina_raspagem,
            "contato": config.contato,
            "telefone": config.telefone,
            "head_evento": config.head_evento,
            "tempo_espera_segundos": config.tempo_espera_segundos,
            "modo_execucao": config.modo_execucao,
        },
        "agenda": {
            "id": agenda.id,
            "fertipar_protocolo": agenda.fertipar_protocolo,
            "fertipar_pedido": agenda.fertipar_pedido,
            "fertipar_destino": agenda.fertipar_destino,
            "carga_solicitada": float(agenda.carga_solicitada) if agenda.carga_solicitada else None,
        },
        "motorista": {
            "id": motorista.id,
            "nome": motorista.nome,
            "cpf": motorista.cpf,
        },
        "caminhao": {
            "id": caminhao.id,
            "placa": caminhao.placa,
            "uf": caminhao.uf,
            "tipo_carroceria": caminhao.tipo_carroceria,
            "placa_reboque1": caminhao.placa_reboque1,
            "uf1": caminhao.uf1,
            "placa_reboque2": caminhao.placa_reboque2,
            "uf2": caminhao.uf2,
            "placa_reboque3": caminhao.placa_reboque3,
            "uf3": caminhao.uf3,
        },
        "storage_state": storage_state # Passa o estado da sessão para o robô
    }
    
    print("\n--- PARÂMETROS PARA EXECUÇÃO DO RPA (JSON) ---")
    # Não imprimir o storage_state para não poluir o log
    params_to_print = {k: v for k, v in rpa_params.items() if k != 'storage_state'}
    print(json.dumps(params_to_print, indent=4))
    print("--------------------------------------------\n")
    
    agenda.status = 'processando'
    db.session.commit()

    try:
        run_headless_mode = False # Forçado para navegador visível a pedido do usuário
        print(f"Chamando process_agendamento_main_task com run_headless={run_headless_mode}")
        result = asyncio.run(process_agendamento_main_task(rpa_params, run_headless=run_headless_mode))
        
        # --- LÓGICA DE SESSÃO: Salvar novo estado se existir ---
        new_storage_state = result.get('new_storage_state')
        if new_storage_state:
            print("--- SALVANDO NOVO ESTADO DA SESSÃO NO BANCO DE DADOS ---")
            if sessao_rpa:
                sessao_rpa.storage_state = new_storage_state
                sessao_rpa.last_updated = datetime.now(timezone.utc)
            else:
                sessao_rpa = RpaSessao(storage_state=new_storage_state)
                db.session.add(sessao_rpa)
            db.session.commit()
            print("--- Novo estado da sessão salvo com sucesso. ---")


        if result['success']:
            agenda.status = 'agendado'
            # agenda.log_retorno = result.get('message', 'Agendamento concluído com sucesso.') # log_retorno não existe
            db.session.commit()
            return jsonify(success=True, message=result.get('user_facing_message', result.get('message', 'Agendamento concluído com sucesso.')))
        else:
            agenda.status = 'erro'
            log_content_for_db = result.get('message', 'Erro desconhecido durante a execução do RPA.')
            # agenda.log_retorno = log_content_for_db # log_retorno não existe

            try:
                db.session.commit()
            except Exception as commit_e:
                db.session.rollback()
                print(f"ERROR app.py: db.session.commit() failed for agenda {agenda.id}: {commit_e}")
                try:
                    # agenda.log_retorno = f"Original commit failed: {commit_e}" # log_retorno não existe
                    db.session.commit()
                except Exception as final_e:
                    db.session.rollback()
                    print(f"CRITICAL ERROR app.py: Failed to commit commit error for agenda {agenda.id}: {final_e}")
                return jsonify(success=False, message=f"Erro ao persistir log: {commit_e}"), 200

            return jsonify(success=False, message=result.get('user_facing_message', result.get('message', 'Ocorreu um erro durante a execução do RPA.'))), 200
    except Exception as e:
        db.session.rollback()
        agenda.status = 'erro'
        # agenda.log_retorno = f"Erro inesperado no servidor: {e}" # log_retorno não existe
        db.session.commit()
        print(f"Erro ao executar automação para agenda {agenda_id}: {e}")
        return jsonify(success=False, message="Erro interno ao executar a automação do robô."), 500

@app.route('/api/agendas/execute_dev_mode/<int:agenda_id>', methods=['POST'])
@dev_required
def execute_agenda_task_dev_mode(agenda_id):
    """
    Executes the Playwright RPA task for a specific agenda item in non-headless mode,
    passing all necessary data as a single JSON object.
    Handles loading and saving of the RPA session state.
    """
    print(f"--- Iniciando execute_agenda_task_dev_mode para agenda_id: {agenda_id} ---")
    agenda = db.session.get(Agenda, agenda_id)
    if not agenda:
        print(f"Agenda ID {agenda_id} não encontrada.")
        return jsonify(success=False, message="Agenda não encontrada."), 404

    config = db.session.query(ConfiguracaoRobo).first()
    if not config:
        print("Configuracoes do Robo: Nenhuma")
        return jsonify(success=False, message="Configuração do robô não encontrada."), 500

    motorista = db.session.get(Motorista, agenda.motorista_id)
    caminhao = db.session.get(Caminhao, agenda.caminhao_id)
    if not motorista or not caminhao:
        return jsonify(success=False, message="Motorista ou Caminhão da agenda não encontrados."), 404

    # --- LÓGICA DE SESSÃO: Carregar estado do banco de dados ---
    print("--- Carregando estado de sessão do RPA do banco de dados (Dev Mode)... ---")
    sessao_rpa = db.session.query(RpaSessao).first()
    storage_state = sessao_rpa.storage_state if sessao_rpa else None
    if storage_state:
        print("Estado de sessão encontrado (Dev Mode).")
    else:
        print("Nenhum estado de sessão encontrado. Será necessário um novo login (Dev Mode).")


    # --- 1. Estruturar todos os dados em um único dicionário (JSON) ---
    rpa_params = {
        "config": {
            "url_acesso": config.url_acesso,
            "filial": config.filial,
            "usuario_site": config.usuario_site,
            "senha_site": config.senha_site, # senha_site é uma property que decodifica o valor
            "email_retorno": config.email_retorno,
            "pagina_raspagem": config.pagina_raspagem,
            "contato": config.contato,
            "telefone": config.telefone,
            "head_evento": config.head_evento,
            "tempo_espera_segundos": config.tempo_espera_segundos,
            "modo_execucao": config.modo_execucao,
        },
        "agenda": {
            "id": agenda.id,
            "fertipar_protocolo": agenda.fertipar_protocolo,
            "fertipar_pedido": agenda.fertipar_pedido,
            "fertipar_destino": agenda.fertipar_destino,
            "carga_solicitada": float(agenda.carga_solicitada) if agenda.carga_solicitada else None,
        },
        "motorista": {
            "id": motorista.id,
            "nome": motorista.nome,
            "cpf": motorista.cpf,
        },
        "caminhao": {
            "id": caminhao.id,
            "placa": caminhao.placa,
            "uf": caminhao.uf,
            "tipo_carroceria": caminhao.tipo_carroceria,
            "placa_reboque1": caminhao.placa_reboque1,
            "uf1": caminhao.uf1,
            "placa_reboque2": caminhao.placa_reboque2,
            "uf2": caminhao.uf2,
            "placa_reboque3": caminhao.placa_reboque3,
            "uf3": caminhao.uf3,
        },
        "storage_state": storage_state # Passa o estado da sessão para o robô
    }

    # --- 2. Remover prints antigos e imprimir o JSON formatado ---
    print("\n--- PARÂMETROS PARA EXECUÇÃO DO RPA (JSON) (Dev Mode) ---")
    params_to_print = {k: v for k, v in rpa_params.items() if k != 'storage_state'}
    print(json.dumps(params_to_print, indent=4))
    print("--------------------------------------------\n")

    agenda.status = 'processando (Dev)'
    db.session.commit()

    try:
        run_headless_mode = False  # Sempre visível para modo dev
        print(f"Chamando process_agendamento_main_task com run_headless={run_headless_mode} (Dev Mode)")
        
        # --- 3. Passar o dicionário `rpa_params` que agora contém o storage_state ---
        result = asyncio.run(process_agendamento_main_task(rpa_params, run_headless=run_headless_mode))
        
        # --- LÓGICA DE SESSÃO: Salvar novo estado se existir (Dev Mode) ---
        new_storage_state = result.get('new_storage_state')
        if new_storage_state:
            print("--- SALVANDO NOVO ESTADO DA SESSÃO NO BANCO DE DADOS (Dev Mode) ---")
            if sessao_rpa:
                sessao_rpa.storage_state = new_storage_state
                sessao_rpa.last_updated = datetime.now(timezone.utc)
            else:
                sessao_rpa = RpaSessao(storage_state=new_storage_state)
                db.session.add(sessao_rpa)
            db.session.commit()
            print("--- Novo estado da sessão salvo com sucesso (Dev Mode). ---")

        if result['success']:
            agenda.status = 'agendado'
            # agenda.log_retorno = result.get('message', 'Agendamento concluído com sucesso (Dev Mode).') # log_retorno não existe
            db.session.commit()
            return jsonify(success=True, message=result.get('user_facing_message', result.get('message', 'Agendamento concluído com sucesso (Dev Mode).')))
        else:
            agenda.status = 'erro (Dev)'
            log_content_for_db = result.get('message', 'Erro desconhecido durante a execução do RPA (Dev Mode).')
            # agenda.log_retorno = log_content_for_db # log_retorno não existe
            
            try:
                db.session.commit()
            except Exception as commit_e:
                db.session.rollback()
                print(f"ERROR app.py: db.session.commit() failed for agenda {agenda.id} (Dev Mode): {commit_e}")
                try:
                    # agenda.log_retorno = f"Original commit (Dev Mode) failed: {commit_e}" # log_retorno não existe
                    db.session.commit()
                except Exception as final_e:
                    db.session.rollback()
                    print(f"CRITICAL ERROR app.py: Failed to commit commit error for agenda {agenda.id} (Dev Mode): {final_e}")
                return jsonify(success=False, message=f"Erro ao persistir log (Dev Mode): {commit_e}"), 200

            return jsonify(success=False, message=result.get('user_facing_message', result.get('message', 'Ocorreu um erro durante a execução do RPA (Dev Mode).'))), 200
    except Exception as e:
        db.session.rollback()
        agenda.status = 'erro (Dev)'
        # agenda.log_retorno = f"Erro inesperado no servidor (Dev Mode): {e}" # log_retorno não existe
        db.session.commit()
        print(f"Erro ao executar automação (Dev Mode) para agenda {agenda_id}: {e}")
        return jsonify(success=False, message="Erro interno ao executar a automação do robô (Dev Mode)."), 500





