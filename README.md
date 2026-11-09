# emporio-ai-agent
AI-powered customer service agent built with Python, LLM tool calling and retrieval for Artefact's technical challenge.

Projeto do desafio técnico de AI Engineer da Artefact para a loja fictícia
Empório da Música. O desenvolvimento será incremental, com arquitetura simples,
código legível e testes automatizados. Esta etapa contém apenas a estrutura
inicial; o agente, a integração com LLM e a interface ainda não foram implementados.

## Configuração do ambiente

Requisito: Python 3.12. Na raiz do repositório:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
```

No Windows, ative o ambiente com `.venv\Scripts\Activate.ps1` no PowerShell.
A instalação editável permite desenvolver o pacote sem reinstalá-lo a cada alteração.
Nenhuma chave de API ou serviço externo é necessário nesta etapa.

## Estrutura inicial

```text
src/emporio_agent/  Pacote Python principal
  tools/           Futuras ferramentas de consulta
  retrieval/       Recuperação das políticas internas
  services/        Serviços e acesso aos dados
tests/             Testes automatizados
examples/          Exemplos de conversas (a adicionar)
data/              Arquivos fornecidos pela Artefact (a adicionar)
```

Os diretórios `examples/` e `data/` contêm apenas marcadores para serem
versionados. Não há dados fictícios. Não versione credenciais, informações
pessoais ou dados sensíveis; revise os arquivos antes de adicioná-los ao Git.
