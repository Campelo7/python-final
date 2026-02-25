import requests

# ======================================
# CONFIGURAÇÃO FLOWISE (RAG JURÍDICO)
# ======================================

FLOWISE_API_URL = "https://cloud.flowiseai.com/api/v1/prediction/826ba8e7-692b-4530-becc-b9e2c24245ea"

# Se precisar de API Key no Flowise:
# FLOWISE_API_KEY = "SUA_CHAVE_AQUI"

# ======================================
# HISTÓRICO LOCAL DA CONVERSA
# ======================================

historico = []

# ======================================
# FUNÇÃO PRINCIPAL FLOWISE
# ======================================

def conversar_flowise(mensagem_usuario):
    global historico

    # Monta histórico formatado
    contexto_formatado = ""
    for msg in historico:
        if msg["role"] == "user":
            contexto_formatado += f"Usuário: {msg['content']}\n"
        elif msg["role"] == "assistant":
            contexto_formatado += f"Assistente: {msg['content']}\n"

    pergunta_final = f"""
Você é um assistente jurídico especializado em Direito do Consumidor brasileiro.

Responda exclusivamente com base no Código de Defesa do Consumidor e documentos fornecidos.
Sempre cite o artigo da lei quando possível.
Se não houver base legal, informe que não encontrou fundamento legal.
Use linguagem formal e objetiva.

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

    # Caso use autenticação:
    # headers["Authorization"] = f"Bearer {FLOWISE_API_KEY}"

    try:
        response = requests.post(
            FLOWISE_API_URL,
            json=payload,
            headers=headers,
            timeout=60
        )

        response.raise_for_status()
        resposta_json = response.json()

        texto_ia = (
            resposta_json.get("text")
            or resposta_json.get("answer")
            or str(resposta_json)
        )

        # Atualiza histórico
        historico.append({"role": "user", "content": mensagem_usuario})
        historico.append({"role": "assistant", "content": texto_ia})

        return texto_ia

    except requests.RequestException as e:
        return f"Erro ao comunicar com o assistente jurídico: {str(e)}"


# ======================================
# INTERFACE TERMINAL (CLI)
# ======================================

def menu():
    print("\n=== Assistente Jurídico - Direito do Consumidor ===")
    print("1 - Fazer pergunta")
    print("2 - Resetar conversa")
    print("3 - Sair")


while True:
    menu()
    opcao = input("Resposta: ")

    if opcao == "1":
        mensagem = input("\nDigite sua pergunta jurídica: ")
        resposta = conversar_flowise(mensagem)
        print("\nAssistente Jurídico:\n")
        print(resposta)

    elif opcao == "2":
        historico = []
        print("\nConversa reiniciada.\n")

    elif opcao == "3":
        print("\nEncerrando sistema.\n")
        break

    else:
        print("\nOpção inválida.\n")