import os
from io import BytesIO
from flask import Flask, abort, render_template, redirect, url_for, flash, request, send_file, send_from_directory, \
    Blueprint
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user,login_required
from flask_admin import Admin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import StringField, SubmitField,IntegerField,TextAreaField,BooleanField,SelectField,PasswordField
from wtforms.validators import DataRequired,Email,NumberRange
import smtplib
from email.mime.text import MIMEText
import requests
import enum

#Selecionando os estados brasileiros
url_ibge='https://servicodados.ibge.gov.br/api/v1/localidades/distritos'
resposta=requests.get(url_ibge,params={'orderBy':'nome'})
data=resposta.json()
lista_cidades = [cidade['nome']+','+cidade['municipio']['microrregiao']['mesorregiao']['UF']['nome'] for cidade in data]
cidades_formatadas=[]
for cidade in lista_cidades:
    if cidade not in cidades_formatadas:
        cidades_formatadas.append(cidade)

#Função para envio de email para o Candidato
def enviar_email(destinatario):
    meu_email = ''
    senha = ''
    assunto = 'Formulario Preenchido!'
    mensagem = 'Seus dados estão confirmados no nosso sistema.'

    msg = MIMEText(mensagem, 'plain', 'utf-8')
    msg['Subject'] = assunto
    msg['From'] = meu_email
    msg['To'] = destinatario
    try:
        with smtplib.SMTP('smtp.gmail.com') as conexao:
            conexao.starttls()
            conexao.login(user=meu_email, password=senha)
            conexao.sendmail(meu_email, destinatario, msg.as_string())
            print('E-mail enviado com sucesso')
    except smtplib.SMTPAuthenticationError:
        print('Erro de autenticação. Verifique seu e-mail e senha.')
    except Exception as e:
        print('Ocorreu um erro ao enviar o e-mail:', str(e))


app = Flask(__name__)
app.config['SECRET_KEY'] = ''
Bootstrap5(app)

# CONECTANDO AO BANCO
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///formulario.db'
db = SQLAlchemy()
db.init_app(app)

#INICILIZANDO O OBJETO DA CLASSE ADMIN
admin = Admin()
admin.init_app(app)


#INICIALIZANDO A CLASSE LOGIN_MANAGER
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(adm_id):
    return db.get_or_404(Admin,adm_id)


class Candidatura(enum.Enum):
    aprovado = 'Aprovado'
    rejeitado = 'Rejeitado'
    em_espera = 'Em Espera'


class CadastroUsuario(db.Model):
    __tablename__ = 'cadastro_usuario'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    idade = db.Column(db.Integer)
    email = db.Column(db.String(255), nullable=False, unique=True)
    telefone = db.Column(db.String(25), nullable=False)
    localidade = db.Column(db.String(100))
    nome_curriculo = db.Column(db.String(50))
    curriculo = db.Column(db.LargeBinary)
    descricao = db.Column(db.Text)
    empregabilidade = db.Column(db.String(25))
    expectativa_sal = db.Column(db.String(5))
    status_candidatura = db.Column(db.Enum("Aprovado", "Rejeitado", "Em espera", name="Candidatura"), default="Em espera")
    contactar = db.Column(db.Boolean)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

class Admin(UserMixin,db.Model):
    __tablename__= 'admin'
    id = db.Column( db.Integer, primary_key = True)
    email = db.Column(db.String(100),unique = True)
    senha = db.Column(db.String)

with app.app_context():
    db.create_all()


#ADICIONANDO O ADM NO BANCO
# with app.app_context():
#     senha_hash = generate_password_hash(password='123456', method='pbkdf2:sha256', salt_length=8)
#     adm = Admin(
#         email='admin@email.com',
#         senha = senha_hash
#                 )
#     db.session.add(adm)
#     db.session.commit()

msg_erro='Campo não preenchido'
class Formulario(FlaskForm):
    nome = StringField('Nome',validators=[DataRequired(message=msg_erro)])
    idade = IntegerField('Idade',validators=[NumberRange(min=16,message="Idade minima de 16 anos.")])
    telefone = StringField('Telefone',validators=[DataRequired(msg_erro)])
    localidade = SelectField('Localidade',choices=cidades_formatadas)
    email = StringField('Email',validators=[DataRequired(msg_erro),Email(message="Email Invalido")])
    curriculo = FileField("Curriculo(Opcional)")
    descricao = TextAreaField("Descreva sua Qualificações(Opcional)")
    empregabilidade = SelectField('Status de Empregabilidade',choices=['Empregado','Desempregado','Estagiando'])
    expectativa_sal = StringField('Expectativa Salarial')
    enviar_email=BooleanField("Gostaria de Receber o Email no caso de Aprovação?")
    submit = SubmitField('Enviar')

class LoginAdm(FlaskForm):
    email = StringField("Email",validators=[DataRequired(msg_erro),Email()])
    senha = PasswordField("Senha",validators=[DataRequired(msg_erro)])
    submit = SubmitField("Enviar")

#CAMINHO DO DIRETORIO PARA CRIAÇÃO DA PASTA COM O CURRICULO,TENDO O ID DO USUARIO COMO O NOME DO ARQUIVO;
diretorio = 'C:/Users/Acer/PycharmProjects/PythonCódigos/Web/FlaskWeb/TrabalhoPython/static/curriculo'

@app.route('/',methods=['GET','POST'])
def home():
    form = Formulario()
    if form.validate_on_submit():
        verificar_email_existente = CadastroUsuario.query.filter_by(email=form.email.data).first()
        if verificar_email_existente:
            flash('Email já cadastrado')
            return redirect(url_for('home'))

        if form.curriculo.data:
            arquivo = form.curriculo.data
            nome_arquivo = arquivo.filename
            conteudo_arquivo = arquivo.read()
            print(nome_arquivo)
        else:
            nome_arquivo = None
            conteudo_arquivo = None
        print(f'Nome Do Arquivo:{nome_arquivo}')
        novoCadastro = CadastroUsuario(
            nome = form.nome.data.title(),
            idade = form.idade.data,
            email = form.email.data,
            telefone = form.telefone.data,
            localidade = form.localidade.data,
            nome_curriculo = nome_arquivo,
            curriculo =conteudo_arquivo,
            descricao = form.descricao.data,
            empregabilidade = form.empregabilidade.data,
            expectativa_sal = form.expectativa_sal.data,
            contactar = form.enviar_email.data
        )
        db.session.add(novoCadastro)
        db.session.commit()
        #Adicionando o PDF em uma Pasta expecifica,para posteriormente viabilizalas para visualizacao
        if conteudo_arquivo:
            _dir = os.path.join(diretorio,f'{novoCadastro.id}')
            if not os.path.exists(_dir):
                os.makedirs(_dir)
            with open(f'./static/curriculo/{novoCadastro.id}/{nome_arquivo}','wb') as arquivo:
                arquivo.write(conteudo_arquivo)
        # if form.enviar_email.data:
            # email=form.email.data
            # email_formatado=email.encode('utf-8')
            # enviar_email(email=email_formatado)
        flash(message='Cadastro Concluido')
        return redirect(url_for('home'))
    return render_template('index.html',form=form)

# with app.app_context():
    # query = f'%juca%'
    # cadastros_query = CadastroUsuario.query.filter(CadastroUsuario.email.like(query)).all()
    # cadastros_q = CadastroUsuario.query.filter(CadastroUsuario.nome.icontains(query) | CadastroUsuario.email.icontains(query)).all()
    # print(cadastros_q.all())

#LOGAR ADMIN
@app.route('/login',methods=['GET','POST'])
def login_admin():
    form = LoginAdm()
    if form.validate_on_submit():
        adm = Admin.query.filter_by(email = form.email.data).first()
        if not adm:
            flash('Email Incorreto')
            return redirect(url_for('login_admin'))

        elif not check_password_hash(adm.senha,form.senha.data):
            flash('Senha Incorreta')
            return redirect(url_for('login_admin'))

        else:
            login_user(adm)
            return redirect(url_for('cadastro'))
    return render_template('login.html',form=form)

@app.route('/cadastros',methods=['GET','POST'])
@login_required
def cadastro():
    todos_cadastros = db.session.query(CadastroUsuario).all()
    if request.method=='POST':
        query = f'{request.form["search"]}%'
        print(query)
        cadastros_q = CadastroUsuario.query.filter(
            CadastroUsuario.nome.icontains(query) | CadastroUsuario.email.icontains(query) \
            | CadastroUsuario.idade.icontains(query)).all()
        return render_template('registros.html',cadastros=cadastros_q)

    return render_template('registros.html',cadastros=todos_cadastros)

@app.route('/perfil/<int:id>')
@login_required
def perfil(id):
    perfil = db.session.get(CadastroUsuario,id)
    if request.args.get('editar'):
        return render_template('perfil.html',perfil=perfil,editar=True)

    if request.args.get('status'):
        status = request.args.get('status')
        perfil.status_candidatura = status
        db.session.commit()
        print(status)
        if status == 'Aprovado' and perfil.contactar:
            print(perfil.contactar)
            print(perfil.email)
            enviar_email(destinatario=perfil.email)
        return redirect(url_for('perfil',id=perfil.id))
    return render_template('perfil.html',perfil=perfil)

#DOWNLOAD CURRICULO
@app.route('/curriculo/<id_curriculo>')
def get_curriculo(id_curriculo):
    curriculo = CadastroUsuario.query.filter_by(id=id_curriculo).first()
    print(curriculo.nome_curriculo)
    return send_file(BytesIO(curriculo.curriculo),download_name = curriculo.nome_curriculo,as_attachment=True)

#Visualizar curriculo
@app.route('/visualizar/<id_curriculo>')
def visualizar_curriculo(id_curriculo):
    curriculo = db.session.get(CadastroUsuario,id_curriculo)
    print(f'/curriculo/{curriculo.id}/{curriculo.nome_curriculo}')
    return send_from_directory('static',f'curriculo/{curriculo.id}/{curriculo.nome_curriculo}')

#DELETANDO REGISTROS
@app.route('/delete')
def delete():
    id_candidato = request.args.get('id')
    candidado = db.session.get(CadastroUsuario,id_candidato)
    db.session.delete(candidado)
    db.session.commit()
    return redirect(url_for('cadastro'))

#Função para Deslogar
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))
    
if __name__=='__main__':
    app.run(debug=True)
