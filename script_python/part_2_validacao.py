import csv
import re
import math
from collections import defaultdict

# =========================
# PATHS
# =========================
BASE_RAW = "data/raw"
BASE_PROCESSED = "data/processed"

CAMINHO_CONSOLIDADO = f"{BASE_PROCESSED}/consolidado_despesas.csv"
CAMINHO_CADOP = f"{BASE_RAW}/Relatorio_cadop.csv"
CAMINHO_SAIDA = f"{BASE_PROCESSED}/despesas_agregadas.csv"

# =========================
# CNPJ
# =========================
def normalizar_cnpj(cnpj: str) -> str:
    return re.sub(r"\D", "", cnpj or "")

def validar_cnpj(cnpj: str) -> bool:
    cnpj = normalizar_cnpj(cnpj)

    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False

    def calc_digito(cnpj, pesos):
        soma = sum(int(cnpj[i]) * pesos[i] for i in range(len(pesos)))
        resto = soma % 11
        return "0" if resto < 2 else str(11 - resto)

    pesos1 = [5,4,3,2,9,8,7,6,5,4,3,2]
    pesos2 = [6] + pesos1

    d1 = calc_digito(cnpj, pesos1)
    d2 = calc_digito(cnpj[:12] + d1, pesos2)

    return cnpj[-2:] == d1 + d2

# =========================
# CONSOLIDADO (PARTE 1)
# =========================
def carregar_consolidado():
    registros = []

    with open(CAMINHO_CONSOLIDADO, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for r in reader:
            try:
                registros.append({
                    "reg_ans": r["REG_ANS"],
                    "cnpj": normalizar_cnpj(r["CNPJ"]),
                    "razao_social": r["Razao_Social"],
                    "ano": int(r["Ano"]),
                    "trimestre": int(r["Trimestre"]),
                    "valor": float(r["Valor_Despesas"])
                })
            except Exception:
                continue

    return registros

# =========================
# CADOP
# =========================
def carregar_cadop():
    cadastro = {}

    with open(CAMINHO_CADOP, newline="", encoding="latin-1") as f:
        reader = csv.DictReader(f, delimiter=";")

        for r in reader:
            reg_ans = r.get("REGISTRO_OPERADORA")
            if not reg_ans:
                continue

            cadastro[reg_ans] = {
                "cnpj": normalizar_cnpj(r.get("CNPJ")),
                "razao_social": r.get("Razao_Social"),
                "uf": r.get("UF"),
                "modalidade": r.get("Modalidade")
            }

    return cadastro


# =========================
# CLASSIFICAÇÃO
# =========================
def classificar(registro, cadop_info):
    if not validar_cnpj(registro["cnpj"]):
        return "CNPJ_INVALIDO"
    if not cadop_info:
        return "SEM_CADOP"
    if len(cadop_info) > 1:
        return "DUPLICADO"
    if not registro["razao_social"]:
        return "RAZAO_SOCIAL_INVALIDA"
    return "VALIDO"

# =========================
# ENRIQUECIMENTO
# =========================
def enriquecer(registros, cadop):
    enriquecidos = []

    for r in registros:
        base = cadop.get(r["reg_ans"])

        if not base:
            status = "SEM_CADOP"
            enriquecidos.append({
                **r,
                "status": status
            })
            continue

        cnpj_final = base["cnpj"]
        razao_final = base["razao_social"]
        uf_final = base["uf"]

        if not validar_cnpj(cnpj_final):
            status = "CNPJ_INVALIDO"
        else:
            status = "VALIDO"

        enriquecidos.append({
            **r,
            "cnpj": cnpj_final,
            "razao_social": razao_final,
            "uf": uf_final,
            "modalidade": base.get("modalidade"),
            "status": status
        })

    return enriquecidos


# =========================
# AGREGAÇÃO
# =========================
def agregar(registros):
    grupos = defaultdict(list)

    for r in registros:
        chave = (r["razao_social"], r["uf"])
        grupos[chave].append(r["valor"])

    resultado = []

    for (razao, uf), valores in grupos.items():
        total = sum(valores)
        media = total / len(valores)

        variancia = sum((v - media) ** 2 for v in valores) / len(valores)
        desvio = math.sqrt(variancia)

        resultado.append({
            "Razao_Social": razao,
            "UF": uf,
            "Total_Despesas": round(total, 2),
            "Media_Trimestral": round(media, 2),
            "Desvio_Padrao": round(desvio, 2)
        })

    resultado.sort(key=lambda x: x["Total_Despesas"], reverse=True)
    return resultado

# =========================
# SAÍDA
# =========================
def salvar_csv(registros):
    with open(CAMINHO_SAIDA, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "Razao_Social",
                "UF",
                "Total_Despesas",
                "Media_Trimestral",
                "Desvio_Padrao"
            ]
        )
        writer.writeheader()
        writer.writerows(registros)

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    print("Iniciando Parte 2 – Validação e Enriquecimento")

    consolidado = carregar_consolidado()
    cadop = carregar_cadop()

    enriquecidos = enriquecer(consolidado, cadop)
    validos = [r for r in enriquecidos if r["status"] == "VALIDO"]
    agregados = agregar(validos)

    salvar_csv(agregados)

    print("Parte 2 finalizada com sucesso.")
    print(f"Arquivo gerado: {CAMINHO_SAIDA}")
