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
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()

@app.route('/config')
def config():
    return render_template('config.html')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
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
    
    resultados = []
    for cnpj in cnpjs:
        cnpj_sanitizado = re.sub(r'\D', '', cnpj)
        try:
            endpoint = "https://plataforma.bigdatacorp.com.br/empresas" if search_type == "empresas" else "https://plataforma.bigdatacorp.com.br/pessoas"
            
            bdc_data = fetch_bdc_data(
                document_number=cnpj_sanitizado,
                url=endpoint,
                dataset="""basic_data,
               processes.filter(partypolarity = PASSIVE),
               kyc.filter(standardized_type, standardized_sanction_type, type, sanctions_source = Conselho Nacional de Justiça)""",
                token_hash=bigdata_token_hash,
                token_id=bigdata_token_id
            )
            resultados.append(bdc_data)
        except Exception as e:
            resultados.append({
                "document_number": cnpj_sanitizado,
                "error": str(e)
            })
    
    return jsonify(resultados)

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    records = []

    for item in data:
        if "Result" not in item or not item["Result"]:
            continue

        for result in item["Result"]:
            bd = result.get("BasicData", {})
            main_activity = ""
            cnae_code = ""
            if "Activities" in bd:
                main = next((a for a in bd["Activities"] if a.get("IsMain")), {})
                main_activity = main.get("Activity", "")
                # Format CNAE code
                cnae_code = main.get("CNAE", "")
                if cnae_code:
                    # Remove any non-digit characters and pad with zeros if needed
                    cnae_code = re.sub(r'\D', '', cnae_code)
                    cnae_code = cnae_code.zfill(7)  # Ensure 7 digits

            # Adicionando informações de processos e KYC
            processes = result.get("Processes", [])
            kyc_data = result.get("KYC", {})
            
            record = {
                "CNPJ": bd.get("TaxIdNumber"),
                "Razão Social": bd.get("OfficialName"),
                "Nome Fantasia": bd.get("TradeName", ""),
                "UF": bd.get("HeadquarterState"),
                "Situação": bd.get("TaxIdStatus"),
                "Regime Tributário": bd.get("TaxRegime"),
                "Capital (R$)": float(bd.get("AdditionalOutputData", {}).get("CapitalRS", 0.0)),
                "Data de Fundação": bd.get("FoundedDate", "")[:10],
                "Atividade Principal": main_activity,
                "CNAE": cnae_code,
                "Número de Processos Passivos": len(processes),
                "Sanções CNJ": len(kyc_data.get("Sanctions", [])) if kyc_data else 0
            }
            
            records.append(record)

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
                    bd = result.get("BasicData", {})
                    simplified_data.append({
                        "CNPJ": bd.get("TaxIdNumber"),
                        "Razão Social": bd.get("OfficialName"),
                        "Nome Fantasia": bd.get("TradeName"),
                        "UF": bd.get("HeadquarterState"),
                        "Situação": bd.get("TaxIdStatus"),
                        "Regime Tributário": bd.get("TaxRegime"),
                        "Capital": bd.get("AdditionalOutputData", {}).get("CapitalRS"),
                        "Data de Fundação": bd.get("FoundedDate"),
                        "Atividades": [a.get("Activity") for a in bd.get("Activities", []) if a.get("IsMain")],
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