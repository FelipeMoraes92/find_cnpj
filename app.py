from flask import Flask, render_template, request, jsonify, send_file, session
import requests
import re
import json
import pandas as pd
import os
from datetime import datetime
import openai

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Necessário para usar session

# Credentials will be loaded from environment variables or config file
BIGDATA_TOKEN_ID = os.getenv('BIGDATA_TOKEN_ID')
BIGDATA_TOKEN_HASH = os.getenv('BIGDATA_TOKEN_HASH')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def fetch_bdc_data(document_number, url, dataset, token_hash, token_id):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "AccessToken": token_hash,
        "TokenId": token_id
    }
    payload = {
        "q": f"doc{{{document_number}}}",
        "Datasets": dataset
    }
    
    print(f"Fazendo requisição para: {url}")
    print(f"Payload: {payload}")
    
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    
    data = response.json()
    print(f"Resposta recebida para CNPJ {document_number}: {type(data)}")
    print(f"Estrutura da resposta: {list(data.keys()) if isinstance(data, dict) else 'Não é dict'}")
    
    return data

@app.route('/config')
def config():
    return render_template('config.html')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    try:
        # Obter credenciais do localStorage via JavaScript
        cnpjs = request.form.get('cnpjs', '').split('\n')
        cnpjs = [cnpj.strip() for cnpj in cnpjs if cnpj.strip()]
        search_type = request.form.get('type', 'empresas')
        
        # Obter credenciais do header da requisição
        bigdata_token_id = request.headers.get('X-BigData-TokenId')
        bigdata_token_hash = request.headers.get('X-BigData-TokenHash')
        openai_api_key = request.headers.get('X-OpenAI-Key')
        
        if not all([bigdata_token_id, bigdata_token_hash, openai_api_key]):
            return jsonify({"error": "Credenciais não configuradas"}), 401
        
        if not cnpjs:
            return jsonify({"error": "Nenhum CNPJ fornecido"}), 400
        
        resultados = []
        for cnpj in cnpjs:
            cnpj_sanitizado = re.sub(r'\D', '', cnpj)
            try:
                endpoint = "https://plataforma.bigdatacorp.com.br/empresas" if search_type == "empresas" else "https://plataforma.bigdatacorp.com.br/pessoas"
                
                bdc_data = fetch_bdc_data(
                    document_number=cnpj_sanitizado,
                    url=endpoint,
                    dataset="registration_data",
                    token_hash=bigdata_token_hash,
                    token_id=bigdata_token_id
                )
                resultados.append(bdc_data)
            except requests.exceptions.RequestException as e:
                resultados.append({
                    "document_number": cnpj_sanitizado,
                    "error": f"Erro de conexão: {str(e)}"
                })
            except Exception as e:
                resultados.append({
                    "document_number": cnpj_sanitizado,
                    "error": f"Erro inesperado: {str(e)}"
                })
        
        return jsonify(resultados)
    except Exception as e:
        return jsonify({"error": f"Erro interno do servidor: {str(e)}"}), 500

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    records = []

    for item in data:
        if "Result" not in item or not item["Result"]:
            continue

        for result in item["Result"]:
            # Verificar se RegistrationData existe e acessar corretamente
            rd = result.get("RegistrationData", {}) or result.get("registrationData", {})
            
            if not rd:
                # Se não há dados de registro, pular este item
                continue
            
            record = {
                "CNPJ": rd.get("TaxIdNumber") or rd.get("taxIdNumber"),
                "Razão Social": rd.get("OfficialName") or rd.get("officialName"),
                "Nome Fantasia": rd.get("TradeName") or rd.get("tradeName"),
                "UF": rd.get("HeadquarterState") or rd.get("headquarterState"),
                "Situação": rd.get("TaxIdStatus") or rd.get("taxIdStatus"),
                "Regime Tributário": rd.get("TaxRegime") or rd.get("taxRegime"),
                "Capital (R$)": float(rd.get("CapitalRS", 0.0)),
                "Data de Fundação": (rd.get("FoundedDate") or "")[:10],
                "Natureza Jurídica": rd.get("LegalNature") or rd.get("legalNature"),
                "Porte": rd.get("CompanySize") or rd.get("companySize"),
                "Endereço": rd.get("Address") or rd.get("address"),
                "Bairro": rd.get("Neighborhood") or rd.get("neighborhood"),
                "Cidade": rd.get("City") or rd.get("city"),
                "CEP": rd.get("ZipCode") or rd.get("zipCode"),
                "Telefone": rd.get("Phone") or rd.get("phone"),
                "Email": rd.get("Email") or rd.get("email")
            }
            
            records.append(record)

    if not records:
        return jsonify({"error": "Nenhum dado válido encontrado para download"}), 400

    df = pd.DataFrame(records)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"resultado_cnpjs_{timestamp}.xlsx"
    df.to_excel(filename, index=False)
    
    return send_file(filename, as_attachment=True)

@app.route('/download_json', methods=['POST'])
def download_json():
    data = request.json
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"resultado_cnpjs_{timestamp}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return send_file(filename, as_attachment=True)

@app.route('/analyze_gpt', methods=['POST'])
def analyze_gpt():
    data = request.json
    openai_api_key = request.headers.get('X-OpenAI-Key')
    
    if not openai_api_key:
        return jsonify({"error": "OpenAI API Key não configurada"}), 401
    
    try:
        client = openai.OpenAI(api_key=openai_api_key)
        
        # Preparar o prompt
        prompt = """Você é um analista de risco especializado em AML/KYP/PLD. Sua função é analisar empresas e tomar decisões assertivas sobre o nível de risco, sem rodeios.

        Analise os dados fornecidos e forneça um parecer estruturado da seguinte forma:

        1. RESUMO EXECUTIVO (2-3 linhas)
        - Principais pontos de atenção
        - Decisão final (APROVADO, APROVADO COM RESTRIÇÕES, ou REPROVADO)

        2. ANÁLISE DETALHADA
        - Perfil da empresa
        - Atividades e operações
        - Indicadores de risco
        - Histórico e processos

        3. RECOMENDAÇÕES
        - Medidas mitigadoras (se necessário)
        - Condicionantes (se aplicável)
        - Próximos passos

        IMPORTANTE:
        - Seja direto e objetivo
        - Tome uma posição clara
        - Justifique sua decisão com base nos dados
        - Formate o texto com quebras de linha para melhor legibilidade
        - Use marcadores para listas
        - Destaque pontos críticos em NEGRITO

        Por favor, analise os seguintes dados:"""
        
        # Limitar o tamanho dos dados enviados
        simplified_data = []
        for item in data:
            if "Result" in item and item["Result"]:
                for result in item["Result"]:
                    # Verificar se RegistrationData existe e acessar corretamente
                    rd = result.get("RegistrationData", {}) or result.get("registrationData", {})
                    
                    if not rd:
                        continue
                    
                    simplified_data.append({
                        "CNPJ": rd.get("TaxIdNumber") or rd.get("taxIdNumber"),
                        "Razão Social": rd.get("OfficialName") or rd.get("officialName"),
                        "Nome Fantasia": rd.get("TradeName") or rd.get("tradeName"),
                        "UF": rd.get("HeadquarterState") or rd.get("headquarterState"),
                        "Situação": rd.get("TaxIdStatus") or rd.get("taxIdStatus"),
                        "Regime Tributário": rd.get("TaxRegime") or rd.get("taxRegime"),
                        "Capital": rd.get("CapitalRS"),
                        "Data de Fundação": rd.get("FoundedDate"),
                        "Atividades": [a.get("Activity") for a in (rd.get("Activities") or []) if a.get("IsMain")],
                        "Processos": len(result.get("Processes", [])),
                        "Sanções": len(result.get("KYC", {}).get("Sanctions", []))
                    })
        
        # Fazer a chamada para a API do GPT
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(simplified_data, ensure_ascii=False)}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        analysis = response.choices[0].message.content
        return jsonify({"analysis": analysis})
    except Exception as e:
        print(f"Erro na análise GPT: {str(e)}")  # Log do erro
        error_message = str(e)
        if "context_length_exceeded" in error_message:
            return jsonify({"error": "Os dados são muito extensos para análise. Por favor, reduza a quantidade de CNPJs consultados."}), 400
        elif "rate_limit_exceeded" in error_message:
            return jsonify({"error": "Limite de requisições excedido. Por favor, aguarde um momento e tente novamente."}), 429
        else:
            return jsonify({"error": f"Erro ao realizar a análise: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port) 