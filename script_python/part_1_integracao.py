import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import zipfile
import time
import csv

# =========================
# CONFIGURAÇÕES GERAIS
# =========================
# URL base onde estão os demonstrativos contábeis da ANS
BASE_URL = "https://dadosabertos.ans.gov.br/FTP/PDA/demonstracoes_contabeis/"

# Cabeçalho HTTP para evitar bloqueios simples do servidor
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# =========================
# FUNÇÃO DE REQUISIÇÃO COM RETRY
# =========================
def safe_get(url, tentativas=3, espera=2):
    """
    Realiza uma requisição HTTP com múltiplas tentativas.
    Evita falhas temporárias de conexão ou timeout.
    Retorna a resposta válida ou None em caso de falha.
    """
    for tentativa in range(tentativas):
        try:
            response = requests.get(url, headers=HEADERS, timeout=20)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            print(f"Tentativa {tentativa + 1} falhou: {e}")
            time.sleep(espera)
    return None

# =========================
# EXTRAÇÃO DE ANO E TRIMESTRE
# =========================
def extrair_trimestre_ano(nome_arquivo: str):
    """
    Extrai o ano e o trimestre a partir do nome do arquivo ZIP.
    Suporta variações como 1T, T1, 1TRIMESTRE, etc.
    Retorna (ano, trimestre) ou None se não identificado.
    """
    nome = nome_arquivo.lower().replace("_", "").replace("-", "")

    ano_match = re.search(r"(20\d{2})", nome)
    if not ano_match:
        return None
    ano = int(ano_match.group(1))

    trimestre_match = re.search(
        r"(1t|t1|2t|t2|3t|t3|4t|t4|"
        r"1trimestre|trimestre1|2trimestre|trimestre2|"
        r"3trimestre|trimestre3|4trimestre|trimestre4)",
        nome
    )
    if not trimestre_match:
        return None

    trimestre = int(re.search(r"[1-4]", trimestre_match.group()).group())
    return ano, trimestre

# =========================
# LISTA DE ANOS DISPONÍVEIS
# =========================
def lista_anos_disponiveis():
    """
    Acessa o diretório principal da ANS e retorna
    a lista de anos disponíveis para download.
    """
    response = safe_get(BASE_URL)
    if response is None:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    anos = []

    for link in soup.find_all("a"):
        href = link.get("href")
        if href and href.endswith("/"):
            href = href[:-1]
            if href.isdigit():
                anos.append(int(href))

    return sorted(anos)

# =========================
# LISTA ZIPS POR ANO
# =========================
def lista_zips_por_ano(ano):
    """
    Lista todos os arquivos ZIP disponíveis para um ano específico.
    Retorna uma lista com nome e URL de cada arquivo.
    """
    url_ano = f"{BASE_URL}{ano}/"
    response = safe_get(url_ano)
    if response is None:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    zips = []

    for link in soup.find_all("a"):
        href = link.get("href")
        if href and href.lower().endswith(".zip"):
            zips.append({
                "url": urljoin(url_ano, href),
                "nome": href
            })
    return zips

# =========================
# IDENTIFICA OS 3 ÚLTIMOS TRIMESTRES GLOBAIS
# =========================
def selecionar_ultimos_3_trimestres_global():
    """
    Identifica globalmente os três últimos trimestres disponíveis
    considerando todos os anos presentes no servidor da ANS.
    """
    anos = lista_anos_disponiveis()
    todos = []

    for ano in anos:
        for zip_info in lista_zips_por_ano(ano):
            resultado = extrair_trimestre_ano(zip_info["nome"])
            if not resultado:
                continue

            ano_zip, trimestre = resultado
            if ano_zip == ano:
                todos.append({
                    "ano": ano,
                    "trimestre": trimestre,
                    "url": zip_info["url"]
                })

    todos.sort(key=lambda x: (x["ano"], x["trimestre"]))
    return todos[-3:]

# =========================
# DOWNLOAD E EXTRAÇÃO DOS ARQUIVOS
# =========================
def download_zip(url, pasta):
    """
    Faz o download de um arquivo ZIP e salva localmente.
    Evita download duplicado se o arquivo já existir.
    """
    os.makedirs(pasta, exist_ok=True)
    nome = url.split("/")[-1]
    caminho = os.path.join(pasta, nome)

    if os.path.exists(caminho):
        return caminho

    response = safe_get(url)
    if response is None:
        return None

    with open(caminho, "wb") as f:
        f.write(response.content)

    return caminho

def extrair_zip(caminho_zip, ano, trimestre):
    """
    Extrai o conteúdo do ZIP para uma pasta organizada
    por ano e trimestre.
    """
    destino = os.path.join("data", "extracted", str(ano), f"trimestre_{trimestre}")
    os.makedirs(destino, exist_ok=True)

    if os.listdir(destino):
        return destino

    with zipfile.ZipFile(caminho_zip, "r") as zip_ref:
        zip_ref.extractall(destino)

    return destino

# =========================
# CONSOLIDAÇÃO DO CSV FINAL
# =========================
def gerar_csv_consolidado(trimestres, caminho_saida):
    """
    Consolida os dados dos CSVs extraídos, somando
    despesas, sinistros e eventos assistenciais
    POR OPERADORA (REG_ANS) em cada trimestre.
    """
    linhas_saida = []

    for item in trimestres:
        ano = item["ano"]
        trimestre = item["trimestre"]
        pasta = os.path.join("data", "extracted", str(ano), f"trimestre_{trimestre}")

        totais_por_operadora = {}

        for root, _, files in os.walk(pasta):
            for nome in files:
                if not nome.lower().endswith(".csv"):
                    continue

                caminho_csv = os.path.join(root, nome)

                with open(caminho_csv, newline="", encoding="latin-1") as f:
                    reader = csv.DictReader(f, delimiter=";")

                    if not reader.fieldnames:
                        continue
                    if (
                        "DESCRICAO" not in reader.fieldnames
                        or "VL_SALDO_FINAL" not in reader.fieldnames
                        or "REG_ANS" not in reader.fieldnames
                    ):
                        continue

                    for linha in reader:
                        descricao = (linha.get("DESCRICAO") or "").lower()
                        valor_raw = (linha.get("VL_SALDO_FINAL") or "").strip()
                        reg_ans = (linha.get("REG_ANS") or "").strip()

                        if not reg_ans:
                            continue

                        if not (
                            "despesa" in descricao
                            or "sinistro" in descricao
                            or "evento" in descricao
                        ):
                            continue

                        try:
                            valor = float(valor_raw.replace(".", "").replace(",", "."))
                        except ValueError:
                            continue

                        if reg_ans not in totais_por_operadora:
                            totais_por_operadora[reg_ans] = 0.0

                        totais_por_operadora[reg_ans] += valor

        # gera UMA linha por operadora nesse trimestre
        for reg_ans, total in totais_por_operadora.items():
            linhas_saida.append({
                "REG_ANS": reg_ans,
                "CNPJ": "DESCONHECIDO",
                "Razao_Social": "SEM_CADASTRO_ANS",
                "Ano": ano,
                "Trimestre": trimestre,
                "Valor_Despesas": round(total, 2)
            })

    os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)
    with open(caminho_saida, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "REG_ANS",
                "CNPJ",
                "Razao_Social",
                "Ano",
                "Trimestre",
                "Valor_Despesas"
            ]
        )
        writer.writeheader()
        writer.writerows(linhas_saida)
    

def carregar_cadop(caminho):
    """
    Carrega o arquivo CADOP para mapeamento de CNPJ e Razão Social.
    Retorna um dicionário com CNPJ como chave e Razão Social como valor.
    """
    mapa = {}
    with open(caminho, encoding="latin-1") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            reg = row.get("REGISTRO_OPERADORA")
            if reg:
                mapa[reg]= {
                    'cnpj': row.get('cnpj'), 
                    'razao_social': row.get('razao_social')
                }
    return mapa

# =========================
# PONTO DE ENTRADA DO SCRIPT 
# =========================
if __name__ == "__main__":
    print("Iniciando script...\nAguarde o processamento\n")
    print(' buscando os últimos 3 trimestres disponíveis...')
    trimestres = selecionar_ultimos_3_trimestres_global()
    print(f'baixando e processando os trimestres: \n{[(t["ano"], t["trimestre"]) for t in trimestres]}')
    pasta_zips = os.path.join("data", "raw", "zips")

    for item in trimestres:
        zip_path = download_zip(item["url"], pasta_zips)
        if zip_path:
            extrair_zip(zip_path, item["ano"], item["trimestre"])

    print('\ngerando CSV consolidado de despesas...')
    gerar_csv_consolidado(
        trimestres,
        os.path.join("data", "processed", "consolidado_despesas.csv")
    )

    print("Processamento finalizado com sucesso.")
