from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import sqlitecloud
from datetime import datetime, timedelta



app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_seguraA'
CAMINHO_BANCO = 'sqlitecloud://cmq6frwshz.g4.sqlite.cloud:8860/database_contagem.db?apikey=Dor8OwUECYmrbcS5vWfsdGpjCpdm9ecSDJtywgvRw8k'


def gerar_proximos_dias(n=7):
    hoje = datetime.now().date()
    return [(hoje + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(n)]


def iniciar_banco():
    with sqlitecloud.connect(CAMINHO_BANCO) as conexao:
        cursor = conexao.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profissionais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                especialidade TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS salas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                identificador TEXT UNIQUE NOT NULL,
                profissional_id INTEGER,
                FOREIGN KEY(profissional_id) REFERENCES profissionais(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alocacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sala_id INTEGER NOT NULL,
                profissional_id INTEGER,
                data TEXT NOT NULL,
                FOREIGN KEY(sala_id) REFERENCES salas(id),
                FOREIGN KEY(profissional_id) REFERENCES profissionais(id)
            )
        ''')
        # Criar 3 salas no 1º andar: 1A, 1B, 1C
        # Criar 7 salas no 2º andar: 2A, 2B, 2C, 2D, 2E, 2F, 2G
        etiquetas = [f"1{chr(65+i)}" for i in range(3)] + [f"2{chr(65+i)}" for i in range(7)]

        for etiqueta in etiquetas:
            cursor.execute("INSERT OR IGNORE INTO salas (identificador) VALUES (?)", (etiqueta,))
        conexao.commit()
########################
@app.route("/alocar", methods=["POST"])
def alocar():
    sala_id = request.form["sala_id"]
    profissional_id = request.form["profissional_id"]
    data = request.form["data"]  # vem do formulário com o input escondido

    with sqlitecloud.connect(CAMINHO_BANCO) as conexao:
        cursor = conexao.cursor()

        # Remove alocação anterior para essa sala e data
        cursor.execute("DELETE FROM alocacoes WHERE sala_id = ? AND data = ?", (sala_id, data))

        # Insere nova alocação
        cursor.execute(
            "INSERT INTO alocacoes (sala_id, profissional_id, data) VALUES (?, ?, ?)",
            (sala_id, profissional_id, data)
        )

        conexao.commit()

    return redirect(url_for("home") + f"?data={data}")



@app.route("/mapa")
def mapa():
    data = request.args.get("data", datetime.now().date().strftime('%Y-%m-%d'))

    with sqlitecloud.connect(CAMINHO_BANCO) as conexao:
        cursor = conexao.cursor()

        cursor.execute("""
            SELECT salas.id, salas.identificador, profissionais.nome
            FROM salas
            LEFT JOIN alocacoes ON salas.id = alocacoes.sala_id AND alocacoes.data = ?
            LEFT JOIN profissionais ON alocacoes.profissional_id = profissionais.id
        """, (data,))
        salas = cursor.fetchall()

        cursor.execute("SELECT * FROM profissionais")
        profissionais = cursor.fetchall()

    return render_template("profissional.html", salas=salas, profissionais=profissionais, data=data, mostrar_login=False)


@app.route("/mapaadm")
def mapaadm():
    data = request.args.get("data", datetime.now().date().strftime('%Y-%m-%d'))

    with sqlitecloud.connect(CAMINHO_BANCO) as conexao:
        cursor = conexao.cursor()

        cursor.execute("""
            SELECT salas.id, salas.identificador, profissionais.nome
            FROM salas
            LEFT JOIN alocacoes ON salas.id = alocacoes.sala_id AND alocacoes.data = ?
            LEFT JOIN profissionais ON alocacoes.profissional_id = profissionais.id
        """, (data,))
        salas = cursor.fetchall()

        cursor.execute("SELECT * FROM profissionais")
        profissionais = cursor.fetchall()

    return render_template("index.html", salas=salas, profissionais=profissionais, data=data, mostrar_login=False)


#######################

@app.route("/")
def profissional():
    with sqlitecloud.connect(CAMINHO_BANCO) as conexao:
        cursor = conexao.cursor()
        cursor.execute("SELECT * FROM profissionais")
        profissionais = cursor.fetchall()
        cursor.execute("""
            SELECT salas.id, salas.identificador, profissionais.nome
            FROM salas LEFT JOIN profissionais ON salas.profissional_id = profissionais.id
        """)
        salas = cursor.fetchall()
        
    return render_template("profissional.html", profissionais=profissionais, salas=salas)

@app.route("/admin", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")
        if usuario == "veronica123" and senha == "20e10":
            session["usuario"] = usuario
        else:
            flash("Usuário ou senha inválidos.")

    if "usuario" not in session:
        mostrar_login = True
    else:
        mostrar_login = False

    # 🟦 Captura a data selecionada ou usa a data de hoje
    data = request.args.get("data", datetime.now().date().strftime('%Y-%m-%d'))

    with sqlitecloud.connect(CAMINHO_BANCO) as conexao:
        cursor = conexao.cursor()

        cursor.execute("""
            SELECT salas.id, salas.identificador, profissionais.nome
            FROM salas
            LEFT JOIN alocacoes ON salas.id = alocacoes.sala_id AND alocacoes.data = ?
            LEFT JOIN profissionais ON alocacoes.profissional_id = profissionais.id
        """, (data,))
        salas = cursor.fetchall()

        cursor.execute("SELECT * FROM profissionais")
        profissionais = cursor.fetchall()

    return render_template("index.html", profissionais=profissionais, salas=salas, mostrar_login=mostrar_login, data=data)

@app.route("/logout")
def logout():
    session.pop("usuario", None)
    return redirect(url_for("home"))

@app.route("/cadastrar", methods=["POST"])
def cadastrar():
    nome = request.form["nome"]
    especialidade = request.form["especialidade"]
    with sqlitecloud.connect(CAMINHO_BANCO) as conexao:
        cursor = conexao.cursor()
        cursor.execute("INSERT INTO profissionais (nome, especialidade) VALUES (?, ?)", (nome, especialidade))
        conexao.commit()
    return redirect(url_for("home"))



@app.route("/desalocar/<int:sala_id>")
def desalocar(sala_id):
    with sqlitecloud.connect(CAMINHO_BANCO) as conexao:
        cursor = conexao.cursor()
        cursor.execute("UPDATE salas SET profissional_id = NULL WHERE id = ?", (sala_id,))
        conexao.commit()
    return redirect(url_for("home"))

if __name__ == "__main__":
    if not os.path.exists(CAMINHO_BANCO):
        iniciar_banco()
    app.run(debug=True,port =5000 ,host='0.0.0.0')
