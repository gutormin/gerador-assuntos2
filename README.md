# Sistema Gerador de Assuntos para Ofícios e E-mails

Sistema web para cadastrar e consultar assuntos padronizados de ofícios e e-mails,
com controle de acesso por perfil, busca por palavra-chave, auditoria e histórico.

Tecnologias: **Python + Flask + SQLite** (banco em arquivo, sem instalação de servidor).

---

## Requisitos

- Python 3.9 ou superior instalado no computador.
  - Para verificar, abra o terminal (Prompt de Comando) e digite: `python --version`

---

## Como instalar e rodar

1. Abra o terminal dentro da pasta do projeto (`gerador_assuntos`).

2. (Opcional, recomendado) Crie um ambiente virtual:
   ```
   python -m venv venv
   ```
   - Windows:  `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

3. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

4. Inicie o sistema:
   ```
   python app.py
   ```

5. Abra o navegador em:
   ```
   http://127.0.0.1:5000
   ```

O banco de dados (`assuntos.db`) é criado automaticamente na primeira execução.

---

## Acesso inicial

Um usuário administrador é criado automaticamente:

- **E-mail:** admin@local
- **Senha:** admin123

> ⚠️ **IMPORTANTE:** crie seu próprio usuário administrador na tela "Usuários"
> e exclua ou troque a senha deste usuário padrão antes de usar de verdade.

---

## Perfis de acesso

| Perfil | O que pode fazer |
|--------|------------------|
| **Administrador/Auditor** | Tudo: gerencia usuários, vê auditoria/logs, cadastra e consulta |
| **Editor/Revisor** | Cadastra, edita e exclui assuntos; gerencia as listas (tipos, subtítulos, tags) |
| **Servidor** | Apenas consulta e copia assuntos |

---

## Funcionalidades

- **Consulta:** busca por palavra-chave (no título, corpo e tags), filtros por
  tipo de documento e subtítulo, ordenação, e botão "copiar título".
- **Cadastro de assuntos:** título, subtítulo, tipo de documento, palavras-chave e corpo modelo.
- **Listas cadastráveis:** tipos de documento, subtítulos e tags são gerenciáveis pela interface.
- **Usuários:** criação, exclusão e desbloqueio (apenas administrador).
- **Auditoria:** registro de todas as ações com data, usuário e detalhe.
- **Histórico:** cada edição de assunto guarda a versão anterior.

---

## Segurança implementada

- Senhas armazenadas com hash forte (nunca em texto puro).
- Bloqueio automático após 5 tentativas de login erradas.
- Controle de acesso por perfil em cada tela.
- Consultas ao banco parametrizadas (proteção contra SQL Injection).
- Trilha de auditoria de todas as ações.

### Antes de usar em produção (em rede/servidor real)
- Troque a `secret_key` em `app.py` por uma chave aleatória forte.
- Troque a senha do administrador padrão.
- Rode atrás de HTTPS (ex: usando um servidor como gunicorn + nginx).
- Faça backup periódico do arquivo `assuntos.db`.

---

## Estrutura dos arquivos

```
gerador_assuntos/
├── app.py              → aplicação principal (rotas e regras)
├── database.py         → criação do banco e dados iniciais
├── requirements.txt    → dependências
├── assuntos.db         → banco de dados (criado ao rodar)
├── templates/          → telas HTML
│   ├── base.html
│   ├── login.html
│   ├── consulta.html
│   ├── assunto_form.html
│   ├── cadastros.html
│   ├── usuarios.html
│   └── auditoria.html
└── static/
    ├── css/estilo.css  → aparência
    └── js/app.js       → função de copiar
```
