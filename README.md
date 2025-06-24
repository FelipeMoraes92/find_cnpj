# Consulta de CNPJ/CPF

Aplicação web para consulta de CNPJs e CPFs utilizando a API da BigData Corp.

## Funcionalidades

- Consulta de CNPJs e CPFs
- Exportação dos resultados em Excel e JSON
- Análise de risco utilizando GPT
- Interface amigável e responsiva
- Armazenamento seguro das credenciais

## Requisitos

- Python 3.9+
- Flask
- Requests
- Pandas
- OpenAI

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/find_cnpj.git
cd find_cnpj
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Execute a aplicação:
```bash
python app.py
```

## Configuração

Ao acessar a aplicação pela primeira vez, você será redirecionado para a página de configuração onde deverá inserir:

- BigData Token ID
- BigData Token Hash
- OpenAI API Key

As credenciais são armazenadas localmente no seu navegador e não são enviadas para o servidor.

## Uso

1. Acesse a aplicação no navegador
2. Escolha entre consulta de Empresas ou Pessoas
3. Insira os CNPJs/CPFs (um por linha)
4. Clique em Consultar
5. Utilize os botões para:
   - Download em Excel
   - Download em JSON
   - Análise GPT

## Segurança

- Credenciais armazenadas localmente
- Sem exposição de dados sensíveis
- Proteção contra commit acidental de credenciais

## Licença

MIT 