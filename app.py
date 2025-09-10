from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

# Conexão com o PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# Criar tabelas se não existirem
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuario (
        id SERIAL PRIMARY KEY,
        nome VARCHAR(100) NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        senha_hash VARCHAR(255) NOT NULL,
        tipo VARCHAR(20) NOT NULL
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS turma (
        id SERIAL PRIMARY KEY,
        nome VARCHAR(50) NOT NULL
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tema (
        id SERIAL PRIMARY KEY,
        titulo VARCHAR(100) NOT NULL,
        descricao TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS redacao (
        id SERIAL PRIMARY KEY,
        usuario_id INTEGER REFERENCES usuario(id),
        tema_id INTEGER REFERENCES tema(id),
        texto TEXT NOT NULL,
        nota NUMERIC(5,2),
        avaliacao TEXT,
        criado_em TIMESTAMP DEFAULT NOW()
    );
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

# Rotas
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, senha_hash, tipo, nome FROM usuario WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user and check_password_hash(user[1], senha):
            session["user_id"] = user[0]
            session["user_name"] = user[3]
            session["user_tipo"] = user[2]
            return redirect(url_for("dashboard"))
        return "Usuário ou senha incorretos"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    cur = conn.cursor()
    # Alunos veem seus temas e redações
    if session["user_tipo"] == "aluno":
        cur.execute("SELECT * FROM tema")
        temas = cur.fetchall()
        cur.execute("SELECT r.id, t.titulo, r.texto, r.nota, r.avaliacao FROM redacao r JOIN tema t ON r.tema_id = t.id WHERE r.usuario_id = %s", (session["user_id"],))
        redacoes = cur.fetchall()
        cur.close()
        conn.close()
        return render_template("dashboard_aluno.html", temas=temas, redacoes=redacoes)
    # Professores veem tudo
    else:
        cur.execute("SELECT r.id, u.nome, t.titulo, r.texto, r.nota, r.avaliacao FROM redacao r JOIN tema t ON r.tema_id = t.id JOIN usuario u ON r.usuario_id = u.id")
        redacoes = cur.fetchall()
        cur.execute("SELECT * FROM tema")
        temas = cur.fetchall()
        cur.close()
        conn.close()
        return render_template("dashboard_prof.html", redacoes=redacoes, temas=temas)

@app.route("/enviar_redacao", methods=["POST"])
def enviar_redacao():
    if "user_id" not in session or session["user_tipo"] != "aluno":
        return redirect(url_for("login"))
    tema_id = request.form["tema_id"]
    texto = request.form["texto"]
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO redacao (usuario_id, tema_id, texto) VALUES (%s, %s, %s)", (session["user_id"], tema_id, texto))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("dashboard"))

@app.route("/avaliar_redacao/<int:redacao_id>", methods=["POST"])
def avaliar_redacao(redacao_id):
    if "user_id" not in session or session["user_tipo"] != "professor":
        return redirect(url_for("login"))
    nota = request.form["nota"]
    avaliacao = request.form["avaliacao"]
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE redacao SET nota=%s, avaliacao=%s WHERE id=%s", (nota, avaliacao, redacao_id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("dashboard"))

@app.route("/criar_tema", methods=["POST"])
def criar_tema():
    if "user_id" not in session or session["user_tipo"] != "professor":
        return redirect(url_for("login"))
    titulo = request.form["titulo"]
    descricao = request.form["descricao"]
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO tema (titulo, descricao) VALUES (%s, %s)", (titulo, descricao))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(debug=True)
