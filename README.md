# Chatbot com Python, Flask e Flowise

Projeto de estudo de integração entre uma interface web em Flask e um fluxo de IA no Flowise, voltado a perguntas sobre Direito do Consumidor.

## Funcionalidades

* Interface web para envio de mensagens.
* Integração HTTP com o Flowise.
* Histórico de conversa por sessão.
* Reinicialização do histórico.
* Tratamento de falhas na comunicação com o serviço externo.

## Tecnologias

Python, Flask, Flask-Session, Requests e Flowise.

## Estrutura

* `app.py`: aplicação Flask, rotas e integração com o Flowise.
* `templates/`: páginas da interface.
* `requirements.txt`: dependências Python.

## Dependência externa

As respostas dependem da disponibilidade e da configuração do fluxo no Flowise. O repositório, por si só, não reproduz a base de documentos e a configuração desse serviço.

## Melhorias planejadas

* Mover as configurações para variáveis de ambiente.
* Aprimorar a validação das mensagens.
* Revisar logs e tratamento de erros.
* Remover arquivos de sessão do versionamento.
* Adicionar testes e instruções completas de execução.

## Limitação

Projeto educacional. As respostas geradas podem conter erros e não substituem orientação jurídica profissional.
