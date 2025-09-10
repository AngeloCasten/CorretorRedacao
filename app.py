from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get("SECRET_KEY", "troque-isto")

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# --- MODELOS ---
class Turma(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    senha_hash = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # aluno ou professor
    id_turma = db.Column(db.Integer, db.ForeignKey('turma.id'), nullable=True)

class Tema(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    id_turma = db.Column(db.Integer, db.ForeignKey('turma.id'), nullable=False)

class Redacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_aluno = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    id_tema = db.Column(db.Integer, db.ForeignKey('tema.id'), nullable=False)
    texto = db.Column(db.Text, nullable=False)
    nota = db.Column(db.Float, nullable=True)
    avaliacao = db.Column(db.Text, nullable=True)
    enviado_em = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# --- ROTAS ---

@app.route("/cadastro", methods=["POST"])
def cadastro():
    data = request.json
    nome = data.get("nome")
    email = data.get("email")
    senha = data.get("senha")
    tipo = data.get("tipo")
    id_turma = data.get("id_turma")  # opcional para professores
    if not nome or not email or not senha or not tipo:
        return jsonify({"error": "Todos os campos obrigatórios"}), 400
    if Usuario.query.filter_by(email=email).first():
        return jsonify({"error": "Email já cadastrado"}), 400
    u = Usuario(nome=nome, email=email, senha_hash=generate_password_hash(senha), tipo=tipo, id_turma=id_turma)
    db.session.add(u)
    db.session.commit()
    return jsonify({"message": "Cadastro realizado com sucesso"})

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    senha = data.get("senha")
    u = Usuario.query.filter_by(email=email).first()
    if not u or not check_password_hash(u.senha_hash, senha):
        return jsonify({"error": "Credenciais inválidas"}), 401
    session["user_id"] = u.id
    session["tipo"] = u.tipo
    return jsonify({"message": "Login realizado", "tipo": u.tipo, "id": u.id})

@app.route("/temas", methods=["GET"])
def listar_temas():
    user_id = session.get("user_id")
    tipo = session.get("tipo")
    if not user_id: return jsonify({"error":"Não logado"}),401
    if tipo=="aluno":
        u = Usuario.query.get(user_id)
        temas = Tema.query.filter_by(id_turma=u.id_turma).all()
    else:
        temas = Tema.query.all()
    return jsonify([{"id": t.id, "titulo": t.titulo, "descricao": t.descricao} for t in temas])

@app.route("/redacao/enviar", methods=["POST"])
def enviar_redacao():
    user_id = session.get("user_id")
    tipo = session.get("tipo")
    if not user_id or tipo!="aluno": return jsonify({"error":"Somente alunos"}),401
    data = request.json
    id_tema = data.get("id_tema")
    texto = data.get("texto")
    if not id_tema or not texto: return jsonify({"error":"Campos obrigatórios"}),400
    r = Redacao(id_aluno=user_id, id_tema=id_tema, texto=texto)
    db.session.add(r)
    db.session.commit()
    return jsonify({"message":"Redação enviada"})

@app.route("/redacoes", methods=["GET"])
def listar_redacoes():
    user_id = session.get("user_id")
    tipo = session.get("tipo")
    if not user_id: return jsonify({"error":"Não logado"}),401
    if tipo=="aluno":
        redacoes = Redacao.query.filter_by(id_aluno=user_id).all()
    else:
        redacoes = Redacao.query.all()
    return jsonify([{"id":r.id,"id_aluno":r.id_aluno,"id_tema":r.id_tema,"texto":r.texto,"nota":r.nota,"avaliacao":r.avaliacao} for r in redacoes])

@app.route("/redacao/avaliar/<int:id_redacao>", methods=["POST"])
def avaliar_redacao(id_redacao):
    user_id = session.get("user_id")
    tipo = session.get("tipo")
    if not user_id or tipo!="professor": return jsonify({"error":"Somente professores"}),401
    data = request.json
    nota = data.get("nota")
    avaliacao = data.get("avaliacao")
    r = Redacao.query.get_or_404(id_redacao)
    r.nota = float(nota) if nota else None
    r.avaliacao = avaliacao
    db.session.commit()
    return jsonify({"message":"Redação avaliada"})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000)
