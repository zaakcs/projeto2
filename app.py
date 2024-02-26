from flask import Flask, abort, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf import FlaskForm
from wtforms import DateTimeField, SubmitField
from datetime import datetime
from wtforms.validators import DataRequired
from flask_login import UserMixin, LoginManager, login_user, current_user, login_required, logout_user
from wtforms import StringField
from flask import render_template



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SECRET_KEY'] = 'your_secret_key'  # Defina uma chave secreta para usar o Flask-WTF
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class DataAtual(DataRequired):
    def __init__(self, message=None):
        super().__init__('Este campo é obrigatório.')
    
    def __call__(self, form, field):
        if field.data < datetime.now():
            raise ValueError('A data deve ser no futuro.')

class AgendamentoForm(FlaskForm):
    cpf = StringField('CPF', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    telefone = StringField('Telefone', validators=[DataRequired()])
    data_hora = DateTimeField('Data e Hora da Consulta', format='%Y-%m-%dT%H:%M', validators=[DataAtual()], default=datetime.now(), render_kw={"type": "datetime-local"})
    submit = SubmitField('Agendar')

class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    cpf = db.Column(db.String(11), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    senha = db.Column(db.String(60), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)  # Pode ser 'aluno' ou 'psicologo'
    consultas_aluno = db.relationship('Consulta', foreign_keys='Consulta.aluno_id', backref='aluno', lazy=True)
    consultas_psicologo = db.relationship('Consulta', foreign_keys='Consulta.psicologo_id', backref='psicologo', lazy=True)

class Consulta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    psicologo_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    data_hora = db.Column(db.DateTime, nullable=False)
    feita = db.Column(db.Boolean, default=False)
    finalizada = db.Column(db.Boolean, default=False)  # Novo campo
    

class DataAtual(DataRequired):
    def __init__(self, message=None):
        super().__init__('Este campo é obrigatório.')
    
    def __call__(self, form, field):
        if field.data < datetime.now():
            raise ValueError('A data deve ser no futuro.')

class AgendamentoForm(FlaskForm):
    data_hora = DateTimeField('Data e Hora da Consulta', format='%Y-%m-%dT%H:%M', validators=[DataAtual()], default=datetime.now(), render_kw={"type": "datetime-local"})
    submit = SubmitField('Agendar')

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


@app.errorhandler(403)
def forbidden(error):
    return render_template('403.html'), 403

@app.route('/agendar_consulta', methods=['GET', 'POST'])
@login_required
def agendar_consulta():
    form = AgendamentoForm()

    if form.validate_on_submit():
        data_hora = form.data_hora.data

        # Verificar se a data já está agendada
        consulta_existente = Consulta.query.filter_by(data_hora=data_hora).first()

        if consulta_existente:
            flash('Erro: Consulta já agendada para esta data e hora. Escolha outra data.', 'danger')
        else:
            # Lógica para encontrar um psicólogo disponível (substitua por sua lógica real)
            psicologo_disponivel = Usuario.query.filter(Usuario.tipo == 'psicologo', Usuario.id != current_user.id).first()

            if psicologo_disponivel is None:
                flash('Desculpe, não há psicólogos disponíveis no momento. Tente novamente mais tarde.', 'danger')
            else:
                consulta = Consulta(aluno=current_user, psicologo=psicologo_disponivel, data_hora=data_hora)
                db.session.add(consulta)
                db.session.commit()
                flash('Consulta agendada com sucesso!', 'success')

    # Adicione este redirecionamento fora do bloco if, para garantir que a página seja recarregada mesmo em caso de erro
    return redirect(url_for('pagina_aluno'))


# Rota padrão (raiz)
@app.route('/')
def home():
    return redirect(url_for('cadastro'))

# Rota para a tela de cadastro
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    error_message = None

    if request.method == 'POST':
        nome = request.form['nome']
        cpf = request.form['cpf']
        email = request.form['email']
        senha = request.form['senha']
        tipo = request.form['tipo']

        # Verificar se o e-mail já existe na base de dados
        usuario_existente_email = Usuario.query.filter_by(email=email).first()

        if usuario_existente_email:
            # Se o e-mail já existe, configurar a mensagem de erro
            error_message = "E-mail já cadastrado. Tente outro."
        else:
            # Verificar se o CPF já existe na base de dados
            usuario_existente_cpf = Usuario.query.filter_by(cpf=cpf).first()

            if usuario_existente_cpf:
                # Se o CPF já existe, configurar a mensagem de erro
                error_message = "CPF já cadastrado. Tente outro."
            else:
                # Se não existir, criar um novo usuário
                novo_usuario = Usuario(nome=nome, cpf=cpf, email=email, senha=senha, tipo=tipo)
                db.session.add(novo_usuario)
                db.session.commit()

                return redirect(url_for('login'))

    return render_template('cadastro.html', error=error_message)

# Rota para a tela de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None

    if request.method == 'POST':
        email_ou_cpf = request.form['email_ou_cpf']
        senha = request.form['senha']
        tipo = request.form['tipo']

        # Lógica de autenticação
        usuario = None

        if '@' in email_ou_cpf:
            # Se o campo contém '@', assume que é um e-mail
            usuario = Usuario.query.filter_by(email=email_ou_cpf).first()
        else:
            # Se não contém '@', assume que é um CPF
            usuario = Usuario.query.filter_by(cpf=email_ou_cpf).first()

        if usuario and usuario.senha == senha:
            if usuario.tipo == tipo:
                login_user(usuario)  # Adicione esta linha para realizar o login do usuário
                if usuario.tipo == 'aluno':
                    return redirect(url_for('pagina_aluno'))
                elif usuario.tipo == 'psicologo':
                    return redirect(url_for('pagina_psicologo'))
            else:
                # Mensagem de erro se o tipo do usuário não coincidir com o tipo selecionado no login
                error_message = f"Você é um {usuario.tipo}, não um {tipo}."
        else:
            # Se o usuário não existir ou a senha estiver incorreta, configurar a mensagem de erro
            error_message = "Usuário não encontrado ou senha incorreta. Verifique seus dados e tente novamente."

    return render_template('login.html', error=error_message)

## Rota para a página do aluno
@app.route('/pagina_aluno', methods=['GET', 'POST'])
@login_required
def pagina_aluno():
    if current_user.tipo != 'aluno':
        abort(403)  # Se o usuário não for um aluno, retorna status 403 (Forbidden)

    form = AgendamentoForm()

    if form.validate_on_submit():
        # Lógica para agendar consulta aqui (ainda precisa ser implementada)
        flash('Consulta agendada com sucesso!', 'success')
        return redirect(url_for('pagina_aluno'))

    return render_template('pagina_aluno.html', form=form)

# Rota para a página do psicólogo
@app.route('/pagina_psicologo')
@login_required
def pagina_psicologo():
    if current_user.tipo != 'psicologo':
        abort(403)  # Se o usuário não for um psicólogo, retorna status 403 (Forbidden)

    # Obtenha todas as consultas agendadas
    consultas = Consulta.query.all()
    return render_template('pagina_psicologo.html', consultas=consultas)



@app.route('/get_unavailable_dates')
@login_required
def get_unavailable_dates():
    # Lógica para obter as datas indisponíveis com base nas consultas agendadas
    unavailable_dates = [consulta.data_hora.strftime('%Y-%m-%d %H:%M') for consulta in Consulta.query.all()]

    return jsonify({'unavailableDates': unavailable_dates})



@app.route('/marcar_feita/<int:consulta_id>')
@login_required
def marcar_feita(consulta_id):
    consulta = Consulta.query.get(consulta_id)

    # Verifique se a consulta pertence ao psicólogo logado
    if consulta and consulta.psicologo_id == current_user.id:
        # Marque a consulta como feita (ou altere o status conforme necessário)
        consulta.feita = True

        # Exclua a consulta do banco de dados
        db.session.delete(consulta)
        db.session.commit()

        flash('Consulta marcada como feita e removida com sucesso!', 'success')
    else:
        flash('Erro: Consulta não encontrada ou não pertence a você.', 'danger')

    return redirect(url_for('pagina_psicologo'))


# Manipulador de erro 404
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


@app.route('/finalizar_consulta/<int:consulta_id>')
@login_required
def finalizar_consulta(consulta_id):
    consulta = Consulta.query.get(consulta_id)

    # Verifique se a consulta pertence ao psicólogo logado
    if consulta and consulta.psicologo_id == current_user.id:
        # Marque a consulta como finalizada
        consulta.finalizada = True

        # Atualize a consulta no banco de dados
        db.session.commit()

        flash('Consulta finalizada com sucesso!', 'success')
    else:
        flash('Erro: Consulta não encontrada ou não pertence a você.', 'danger')

    return redirect(url_for('pagina_psicologo'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)