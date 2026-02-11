import os
import datetime

import dotenv
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Configurações básicas (em produção, use variáveis de ambiente)
app.config['SECRET_KEY'] = 'dev-key-123'


# --- CONFIGURADORES DE CONTEXTO ---

CONTEXTO_CHAT = {
    "historico_mensagens": [],
    "nome_cliente": None,
    "telefone_cliente": None
}

def montar_contexto_sistema():
    """
    Monta system_text com variáveis já conhecidas.
    """
    dotenv.load_dotenv()
    hora_atual = datetime.datetime.now()
    cardapio = {'hamburguer': 10, 'refrigerante': 6}
    telefone = '85985858585'

    # Incluir nome/telefone conhecidos no prompt
    nome_conhecido = f"NOME: {CONTEXTO_CHAT['nome_cliente']}" if CONTEXTO_CHAT['nome_cliente'] else "NOME: desconhecido"
    tel_conhecido = f"TELEFONE: {CONTEXTO_CHAT['telefone_cliente']}" if CONTEXTO_CHAT['telefone_cliente'] else "TELEFONE: desconhecido"

    system_text = (
        "Você é atendente virtual de lanchonete. REGRAS RÍGIDAS:\n\n"
        f"DADOS ATUAIS - {nome_conhecido} | {tel_conhecido}\n\n"
        "- SEMPRE português, educado, 1 pergunta por vez\n"
        f"- Horário: 18h-00h (agora: {hora_atual.hour}:{hora_atual.minute:02d})\n"
        f"- Cardápio: {cardapio}\n"
        f"- Emergência → telefone loja: {telefone}\n\n"
        
        "🚨 EXTRAÇÃO OBRIGATÓRIA 🚨\n"
        "QUANDO cliente der NOME/TELEFONE → ADICIONE NO FINAL da resposta:\n"
        "→ [nome]='NOME_EXATO' [telefone]='DDD+NUMERO'\n\n"
        "EXEMPLO EXATO:\n"
        "Cliente: 'meu nome João'\n"
        "Você: 'Olá João! Qual telefone? [nome]=\"João\"'\n\n"
        
        "NÃO explique as marcações. NÃO use aspas duplas. SEMPRE no final."
    )

    print("[montar_contexto_sistema] Conhecido:", nome_conhecido, "|", tel_conhecido)
    return system_text
# --- HELPERS GEMINI ---


def construir_payload_gemini(system_text, historico_mensagens, generation_config=None):
    """
    Constrói o payload no formato esperado pelo Gemini, dado:
    - system_text: texto da instrução de sistema
    - historico_mensagens: lista de dicts no formato:
        [{"role": "user"/"assistant", "content": "texto"}]
    """
    if generation_config is None:
        generation_config = {
            "maxOutputTokens": 200,
            "temperature": 1,
        }

    # Converte histórico para o formato de contents do Gemini
    contents = []
    for i, msg in enumerate(historico_mensagens):
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if not content:
            print(f"[construir_payload_gemini] Aviso: mensagem vazia no índice {i}")
            continue

        # Gemini usa "user" e "model"
        if role == "assistant":
            role_gemini = "model"
        else:
            role_gemini = "user"

        contents.append({
            "role": role_gemini,
            "parts": [{"text": content}]
        })

    payload = {
        "systemInstruction": {
            "parts": [
                {
                    "text": system_text
                }
            ]
        },
        "contents": contents,
        "generationConfig": generation_config
    }

    print("[construir_payload_gemini] Payload montado. contents len:", len(contents))
    return payload


def conversar_gemini(mensagem_usuario, historico_mensagens=None,
                     modelo='gemini-2.5-flash', generation_config=None):
    """
    Conversa com o Gemini:
    - monta contexto de sistema
    - acrescenta mensagem do usuário ao histórico
    - envia para a API
    - retorna (texto_resposta, historico_atualizado)
    """
    dotenv.load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        print("[conversar_gemini] ERRO: GEMINI_API_KEY não encontrada no .env")
        return "Erro de configuração da IA (GEMINI_API_KEY).", []

    if historico_mensagens is None:
        historico_mensagens = []

    print("[conversar_gemini] Entrada mensagem_usuario:", mensagem_usuario)
    print("[conversar_gemini] Historico inicial len:", len(historico_mensagens))

    # Adiciona a mensagem do usuário ao histórico (formato interno)
    historico_mensagens.append({
        "role": "user",
        "content": mensagem_usuario
    })

    system_text = montar_contexto_sistema()
    payload = construir_payload_gemini(system_text, historico_mensagens, generation_config)

    url_base = "https://generativelanguage.googleapis.com/v1beta/models"
    url = f"{url_base}/{modelo}:generateContent?key={api_key}"

    print("[conversar_gemini] Enviando requisição para Gemini. Modelo:", modelo)
    try:
        resp = requests.post(url, json=payload, timeout=60)
        print("[conversar_gemini] Status code:", resp.status_code)

        resp_json = resp.json()

        if resp.status_code != 200:
            msg_erro = resp_json.get('error', {}).get('message', 'Erro desconhecido na API Gemini')
            print("[conversar_gemini] ERRO na API Gemini:", msg_erro)
            return f"Erro na IA (Gemini): {msg_erro}", historico_mensagens

        # Extrair texto
        try:
            texto_ia = resp_json['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError) as e:
            print("[conversar_gemini] ERRO ao extrair texto:", e)
            return "Erro ao processar a resposta da IA (Gemini).", historico_mensagens

        print("[conversar_gemini] Resposta (preview):", texto_ia[:200])

        # Adiciona resposta da IA ao histórico
        historico_mensagens.append({
            "role": "assistant",
            "content": texto_ia
        })

        return texto_ia, historico_mensagens

    except requests.RequestException as e:
        print("[conversar_gemini] ERRO de requisição:", e)
        return f"Erro de comunicação com a IA (Gemini): {e}", historico_mensagens


# --- HELPERS PERPLEXITY ---


def construir_messages_perplexity(system_text, historico_mensagens):
    """
    Constrói o array messages no formato OpenAI/Perplexity:
    [{"role": "system"|"user"|"assistant", "content": "texto"}]
    """
    messages = []

    if system_text:
        messages.append({
            "role": "system",
            "content": system_text
        })

    for i, msg in enumerate(historico_mensagens):
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if not content:
            print(f"[construir_messages_perplexity] Aviso: mensagem vazia no índice {i}")
            continue

        # Perplexity usa "user" / "assistant"
        if role not in ("user", "assistant", "system"):
            role = "user"

        messages.append({
            "role": role,
            "content": content
        })

    print("[construir_messages_perplexity] messages len:", len(messages))
    return messages


def conversar_perplexity(mensagem_usuario, historico_mensagens=None,
                         modelo='sonar-pro', generation_config=None):
    """
    Conversa com a Perplexity (Sonar API /chat/completions compatível com OpenAI):
    - monta contexto de sistema
    - acrescenta mensagem do usuário ao histórico
    - envia para a API
    - retorna (texto_resposta, historico_atualizado)
    """
    dotenv.load_dotenv()
    api_key = os.getenv('PERPLEXITY_API_KEY')

    if not api_key:
        print("[conversar_perplexity] ERRO: PERPLEXITY_API_KEY não encontrada no .env")
        return "Erro de configuração da IA (PERPLEXITY_API_KEY).", []

    if historico_mensagens is None:
        historico_mensagens = []

    print("[conversar_perplexity] Entrada mensagem_usuario:", mensagem_usuario)
    print("[conversar_perplexity] Historico inicial len:", len(historico_mensagens))

    # Adiciona a mensagem do usuário ao histórico (formato interno)
    historico_mensagens.append({
        "role": "user",
        "content": mensagem_usuario
    })

    system_text = montar_contexto_sistema()
    messages = construir_messages_perplexity(system_text, historico_mensagens)

    if generation_config is None:
        generation_config = {}

    temperature = float(generation_config.get("temperature", 1.0))
    max_tokens = int(generation_config.get("maxOutputTokens", 200))

    body = {
        "model": modelo,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    print("[conversar_perplexity] Enviando requisição para Perplexity")
    print("[conversar_perplexity] Modelo:", modelo)
    print("[conversar_perplexity] temperature:", temperature, "max_tokens:", max_tokens)

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=60)
        print("[conversar_perplexity] Status code:", resp.status_code)

        resp_json = resp.json()

        if resp.status_code != 200:
            msg_erro = resp_json.get('error', {}).get('message', 'Erro desconhecido na API Perplexity')
            print("[conversar_perplexity] ERRO na API Perplexity:", msg_erro)
            return f"Erro na IA (Perplexity): {msg_erro}", historico_mensagens

        try:
            choice0 = (resp_json.get("choices") or [])[0]
            msg0 = choice0.get("message", {})
            texto_ia = msg0.get("content", "")
        except (KeyError, IndexError, AttributeError) as e:
            print("[conversar_perplexity] ERRO ao extrair texto:", e)
            return "Erro ao processar a resposta da IA (Perplexity).", historico_mensagens

        print("[conversar_perplexity] Resposta (preview):", texto_ia[:200])

        # Adiciona resposta da IA ao histórico
        historico_mensagens.append({
            "role": "assistant",
            "content": texto_ia
        })

        return texto_ia, historico_mensagens

    except requests.RequestException as e:
        print("[conversar_perplexity] ERRO de requisição:", e)
        return f"Erro de comunicação com a IA (Perplexity): {e}", historico_mensagens


# --- ROTAS ---


@app.route('/')
def index():
    """Rota principal que carrega a interface do chatbot."""
    return render_template('index.html')


# Para simplificar, o histórico ficará em memória por sessão FIXA aqui.
# Em produção, você iria guardar por usuário (session, banco, etc.).
HISTORICO_MENSAGENS = []


import re


@app.route('/enviar_mensagem', methods=['POST'])
def enviar_mensagem():
    dados = request.get_json() or {}
    mensagem_usuario = dados.get('mensagem', '')
    ia_escolhida = dados.get('ia', 'perplexity')  # padrão perplexity

    print("[/enviar_mensagem] mensagem_usuario:", mensagem_usuario)
    print("[/enviar_mensagem] ia_escolhida:", ia_escolhida)

    if not mensagem_usuario:
        return jsonify({"resposta": "Mensagem vazia", "status": "erro"}), 400

    generation_config = {"maxOutputTokens": 200, "temperature": 0.3}  # temperature baixo = mais consistente

    # Usa o histórico persistente
    texto_ia, novo_historico = (
        conversar_perplexity(mensagem_usuario, CONTEXTO_CHAT["historico_mensagens"], modelo='sonar-pro', generation_config=generation_config)
        if ia_escolhida == 'perplexity' else
        conversar_gemini(mensagem_usuario, CONTEXTO_CHAT["historico_mensagens"], generation_config=generation_config)
    )

    # Atualiza histórico
    CONTEXTO_CHAT["historico_mensagens"] = novo_historico

    # --- EXTRAÇÃO MELHORADA ---
    nome_extraido = CONTEXTO_CHAT.get("nome_cliente")
    telefone_extraido = CONTEXTO_CHAT.get("telefone_cliente")

    # Regex mais flexível
    padrao = r"\[(nome|telefone)\]\s*[=:]\s*['\"]?([^'\[\]\s,;]+)['\"]?"
    matches = re.findall(padrao, texto_ia, re.IGNORECASE)

    for chave, valor in matches:
        valor_limpo = valor.strip().replace('"', '').replace("'", "")
        if chave.lower() == "nome" and valor_limpo:
            nome_extraido = valor_limpo
            CONTEXTO_CHAT["nome_cliente"] = nome_extraido
            print(f"[EXTRAÇÃO] Nome atualizado: '{nome_extraido}'")
        elif chave.lower() == "telefone" and valor_limpo:
            telefone_extraido = valor_limpo
            CONTEXTO_CHAT["telefone_cliente"] = telefone_extraido
            print(f"[EXTRAÇÃO] Telefone atualizado: '{telefone_extraido}'")

    print("[/enviar_mensagem] FINAL - nome:", nome_extraido, "| telefone:", telefone_extraido)

    # Remove marcações do texto visível
    texto_ia_visivel = re.sub(padrao, "", texto_ia, flags=re.IGNORECASE).strip()

    # SALVAR NO BANCO AQUI
    # if nome_extraido and telefone_extraido:
    #     salvar_cliente(nome=nome_extraido, telefone=telefone_extraido)

    return jsonify({
        "resposta": texto_ia_visivel or texto_ia,
        "status": "sucesso" if "Erro" not in texto_ia else "erro"
    })

# --- TRATAMENTO DE ERROS ---


@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html', erro="Página não encontrada"), 404


if __name__ == '__main__':
    # debug=True permite que o servidor reinicie sozinho ao salvar alterações
    app.run(debug=True, port=5000, host='0.0.0.0')
