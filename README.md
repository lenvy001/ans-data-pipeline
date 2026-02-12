# 📊 Sistema de Integracao e Processamento de Dados da ANS

## Visao Geral

Este projeto implementa um pipeline automatizado em Python para coleta, consolidacao, validacao e agregacao de dados publicos disponibilizados pela Agencia Nacional de Saude Suplementar (ANS).

O sistema realiza:
- Download automatizado dos demonstrativos contabeis
- Identificacao dos 3 trimestres mais recentes disponiveis
- Extracao e consolidacao de despesas por operadora
- Validacao de CNPJ com calculo de digito verificador
- Enriquecimento com base cadastral (CADOP)
- Agregacao estatistica (total, media trimestral e desvio padrao)

O objetivo foi desenvolver uma solucao estruturada para automacao de coleta e tratamento de dados publicos, aplicando conceitos de integracao HTTP, manipulacao de arquivos, validacao de dados e analise estatistica basica.

## 🏗 Arquitetura do Projeto

O pipeline foi dividido em duas etapas principais:

### 🔹 Etapa 1 — Integracao e Consolidacao

Responsavel por:
- Acessar repositorio publico da ANS via HTTP
- Identificar automaticamente os trimestres disponiveis
- Implementar mecanismo de retry para requisicoes
- Baixar e extrair arquivos ZIP
- Processar multiplos CSVs
- Filtrar registros relevantes (despesas, sinistros, eventos)
- Consolidar valores por operadora (REG_ANS)

Saida gerada:

```
data/processed/consolidado_despesas.csv
```

### 🔹 Etapa 2 — Validacao e Enriquecimento

Responsavel por:
- Normalizacao e validacao de CNPJ com calculo oficial de digitos verificadores
- Cruzamento com base cadastral CADOP
- Classificacao de registros inconsistentes
- Enriquecimento com:
  - CNPJ
  - Razao Social
  - UF
  - Modalidade
- Agregacao por operadora e estado

Calculos realizados:
- Total de despesas
- Media trimestral
- Variancia
- Desvio padrao

Saida gerada:

```
data/processed/despesas_agregadas.csv
```

## 🧠 Decisoes Tecnicas

- Utilizacao de requests com controle de falha (retry)
- Parsing HTML com BeautifulSoup
- Extracao de padroes de nome via regex
- Processamento de CSV com tratamento de encoding (latin-1)
- Uso de defaultdict para agregacoes
- Implementacao manual de validacao de CNPJ
- Estrutura modular separando integracao e processamento

## 🛠 Tecnologias Utilizadas

- Python 3.10+
- requests
- beautifulsoup4
- csv
- regex
- math
- collections

## 📁 Estrutura do Projeto

```
.
├── script_python/
│   ├── part_1_integracao.py
│   └── part_2_validacao.py
├── data/
│   ├── raw/
│   ├── extracted/
│   └── processed/
├── requirements.txt
├── run_pipeline.py
└── README.md
```

## ▶ Como Executar

Instale as dependencias:

```bash
pip install -r requirements.txt
```

Execute o pipeline completo:

```bash
python run_pipeline.py
```

Ou execute cada etapa separadamente:

```bash
python script_python/part_1_integracao.py
python script_python/part_2_validacao.py
```

Os arquivos finais serao gerados na pasta:

```
data/processed/
```

## 📌 Observacoes

- Os dados utilizados sao publicos e obtidos diretamente do portal oficial da ANS.
- O projeto pode ser facilmente expandido para incluir persistencia em banco de dados ou exposicao via API.
