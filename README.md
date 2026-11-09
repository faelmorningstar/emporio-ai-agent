# emporio-ai-agent
AI-powered customer service agent built with Python, LLM tool calling and retrieval for Artefact's technical challenge.

Projeto do desafio técnico de AI Engineer da Artefact para a loja fictícia
Empório da Música. O desenvolvimento será incremental, com arquitetura simples,
código legível e testes automatizados. Esta etapa contém apenas a estrutura
inicial e consultas ao catálogo; o agente, a integração com LLM e a interface
ainda não foram implementados.

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

## Consultas ao catálogo

Coloque os arquivos originais `categories.csv`, `products.csv` e `promotions.csv`
em `data/`. Eles são privados e estão ignorados pelo Git. Os testes usam somente
dados sintéticos em diretórios temporários, sem depender desses arquivos.

```python
from decimal import Decimal
from emporio_agent.services.catalog import Catalog

catalog = Catalog.load("data")  # caminho relativo ao diretório de execução
products = catalog.search_products(
    name="violão", category="Violões", max_price=Decimal("1000.00")
)
for product in products:
    print(product.name, product.status, product.in_stock, product.available)
    for promotion in catalog.active_promotions(product.product_id):
        print(promotion.discounted_price(product.price_brl))
```

O carregamento exige CSV UTF-8 (BOM opcional), delimitado por vírgulas, com os
cabeçalhos originais. Valida IDs positivos e únicos, referências entre tabelas,
campos preenchidos, preço não negativo e finito, estoque inteiro não negativo,
`specs` como objeto JSON e `created_at` como data ISO. Os relacionamentos são
`products.category_id → categories.category_id` e
`promotions.product_id → products.product_id`; categorias sem produtos são válidas.
Arquivos ou registros inválidos geram `CatalogError` com contexto do arquivo
e, para erros de registro, da linha. Referências inválidas identificam os IDs.

A busca combina filtros: nome parcial e categoria por ID ou nome exato, sem
distinguir maiúsculas, e limites de preço inclusivos. Os filtros usam preço de
catálogo e incluem todos os status. `get_product(id)` retorna o produto ou gera
`LookupError`. `in_stock` verifica quantidade positiva; `available` exige também
status `active`. Outros status aceitos são `discontinued` e `coming_soon`.

Promoções ativas dependem exclusivamente de `is_active` (`0` ou `1`): os arquivos
não informam datas de validade. Descontos percentuais entre 0 e 100 são calculados
individualmente com `Decimal` e arredondamento `ROUND_HALF_UP` para centavos.
Não se presume acumulação nem escolha automática entre promoções. Valores de
preço nas consultas devem ser strings decimais ou `Decimal`, nunca `float`.

Publique código, documentação e testes sintéticos; não publique os CSVs originais,
o ZIP recebido, credenciais, ambientes virtuais ou caches. Novos arquivos em
`data/` também ficam ignorados por padrão, exceto `.gitkeep`.
