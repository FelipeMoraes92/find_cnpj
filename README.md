# Consulta de CNPJs - Big Data Corp

Esta é uma aplicação web para consultar dados de CNPJs utilizando a API da Big Data Corp.

## Funcionalidades

- Interface web amigável para inserção de CNPJs
- Consulta em massa de CNPJs
- Visualização dos resultados em formato JSON
- Download dos resultados em formato Excel
- Suporte a múltiplos CNPJs (um por linha)

## Requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

## Instalação

1. Clone este repositório ou baixe os arquivos
2. Crie um ambiente virtual (recomendado):
   ```bash
   python -m venv venv
   source venv/bin/activate  # No Windows: venv\Scripts\activate
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

## Executando a aplicação

1. Ative o ambiente virtual (se ainda não estiver ativo):
   ```bash
   source venv/bin/activate  # No Windows: venv\Scripts\activate
   ```
2. Execute a aplicação:
   ```bash
   python app.py
   ```
3. Abra seu navegador e acesse:
   ```
   http://localhost:5000
   ```

## Uso

1. Na página inicial, insira os CNPJs que deseja consultar (um por linha)
2. Clique no botão "Consultar"
3. Aguarde o resultado da consulta
4. Visualize os dados em formato JSON
5. Clique no botão "Baixar Excel" para exportar os resultados

## Estrutura do Projeto

```
.
├── app.py              # Aplicação Flask
├── requirements.txt    # Dependências do projeto
├── templates/         # Templates HTML
│   └── index.html     # Página principal
└── README.md          # Este arquivo
```

## Observações

- Os CNPJs podem ser inseridos com ou sem formatação (pontos e traços)
- A aplicação suporta consulta de múltiplos CNPJs simultaneamente
- Os resultados são exibidos em formato JSON e podem ser exportados para Excel 