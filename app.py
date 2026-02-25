import os
import requests
from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
from datetime import timedelta

# ===============================
# CONFIGURAÇÕES INICIAIS
# ===============================

app = Flask(__name__)

app.config["SECRET_KEY"] = "super-secret-key"
app.config["SESSION_TYPE"] = "filesystem"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=2)

Session(app)

# ===============================
# CONFIGURAÇÃO FLOWISE (RAG)
# ===============================

FLOWISE_API_URL = "https://cloud.flowiseai.com/api/v1/prediction/826ba8e7-692b-4530-becc-b9e2c24245ea"

# Se seu Flowise exigir API Key:
# FLOWISE_API_KEY = "SUA_CHAVE_AQUI"

# ===============================
# FUNÇÃO PRINCIPAL FLOWISE
# ===============================

def conversar_flowise(mensagem_usuario, historico):
    """
    Envia pergunta + histórico para o Flowise (RAG Jurídico)
    """

    contexto_formatado = ""
    for msg in historico:
        if msg["role"] == "user":
            contexto_formatado += f"Usuário: {msg['content']}\n"
        elif msg["role"] == "assistant":
            contexto_formatado += f"Assistente: {msg['content']}\n"

    pergunta_final = f"""
Você é um assistente jurídico especializado em Direito do Consumidor brasileiro.
Responda com base apenas nos documentos fornecidos.
Sempre cite o artigo da lei quando possível.
Se não houver base legal, diga que não encontrou fundamento legal.

Histórico da conversa:
{contexto_formatado}

Pergunta atual:
{mensagem_usuario}
"""

    payload = {
        "question": pergunta_final
    }

    headers = {
        "Content-Type": "application/json"
    }

    # Se Flowise exigir autenticação:
    # headers["Authorization"] = f"Bearer {FLOWISE_API_KEY}"

    try:
        response = requests.post(
            FLOWISE_API_URL,
            json=payload,
            headers=headers,
            timeout=60
        )

        print("STATUS FLOWISE:", response.status_code)
        print("RESPOSTA BRUTA FLOWISE:", response.text)

        response.raise_for_status()
        resposta_json = response.json()

        # Flowise pode retornar diferentes formatos
        texto_ia = (
            resposta_json.get("text")
            or resposta_json.get("answer")
            or str(resposta_json)
        )

        # Atualiza histórico
        historico.append({"role": "user", "content": mensagem_usuario})
        historico.append({"role": "assistant", "content": texto_ia})

        return texto_ia, historico

    except requests.RequestException as e:
        return f"Erro ao comunicar com o sistema jurídico: {str(e)}", historico


# ===============================
# ROTAS
# ===============================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/enviar_mensagem", methods=["POST"])
def enviar_mensagem():
    dados = request.get_json()
    mensagem_usuario = dados.get("mensagem", "")

    if not mensagem_usuario:
        return jsonify({"resposta": "Mensagem vazia", "status": "erro"}), 400

    # Inicializa histórico por sessão
    if "historico" not in session:
        session["historico"] = []

    historico = session["historico"]

    resposta_ia, novo_historico = conversar_flowise(
        mensagem_usuario,
        historico
    )

    session["historico"] = novo_historico

    return jsonify({
        "resposta": resposta_ia,
        "status": "sucesso" if "Erro" not in resposta_ia else "erro"
    })


@app.route("/reset", methods=["POST"])
def reset():
    session.pop("historico", None)
    return jsonify({"status": "sucesso", "mensagem": "Sessão reiniciada."})


# ===============================
# TRATAMENTO DE ERROS
# ===============================

@app.errorhandler(404)
def page_not_found(e):
    return render_template("index.html"), 404


# ===============================
# START
# ===============================

if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")