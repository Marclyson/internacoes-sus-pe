"""Baixa as fontes públicas do projeto para dados/raw.

- SIH/SUS, AIH reduzida (RD): um arquivo .dbc por mês, do FTP do DATASUS
- SIGTAP: tabela unificada de procedimentos do SUS (competência de dezembro do ano)
- CID-10: tabelas do DATASUS em CSV
- Municípios: API de localidades do IBGE
- CNES: cadastro de estabelecimentos do OpenDataSUS

Arquivos que já existem não são baixados de novo.
"""
import ftplib
import json
import os
import sys
from pathlib import Path

import requests

ANO = int(os.environ.get("ANO", "2024"))
UF = os.environ.get("UF", "PE").upper()
RAW = Path("dados/raw")

FTP_DATASUS = "ftp.datasus.gov.br"
DIR_SIH = "/dissemin/publicos/SIHSUS/200801_/Dados"
FTP_SIGTAP = "ftp2.datasus.gov.br"
DIR_SIGTAP = "/pub/sistemas/tup/downloads"
URL_CID = "http://www2.datasus.gov.br/cid10/V2008/downloads/CID10CSV.zip"
URL_IBGE = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
URL_CNES = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/CNES/cnes_estabelecimentos.zip"


def baixar_ftp(host, pasta, nome, destino):
    if destino.exists():
        print(f"  já existe: {destino}")
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(destino.suffix + ".part")
    with ftplib.FTP(host, timeout=120) as ftp:
        ftp.login()
        ftp.cwd(pasta)
        with open(tmp, "wb") as f:
            ftp.retrbinary(f"RETR {nome}", f.write)
    tmp.rename(destino)
    print(f"  baixado: {destino} ({destino.stat().st_size:,} bytes)")


def baixar_http(url, destino):
    if destino.exists():
        print(f"  já existe: {destino}")
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(destino.suffix + ".part")
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for bloco in r.iter_content(1 << 20):
                f.write(bloco)
    tmp.rename(destino)
    print(f"  baixado: {destino} ({destino.stat().st_size:,} bytes)")


def arquivo_sigtap():
    """Nome do pacote do SIGTAP de dezembro do ano (ou o último disponível do ano)."""
    with ftplib.FTP(FTP_SIGTAP, timeout=120) as ftp:
        ftp.login()
        ftp.cwd(DIR_SIGTAP)
        nomes = sorted(n for n in ftp.nlst() if n.startswith(f"TabelaUnificada_{ANO}"))
    if not nomes:
        sys.exit(f"SIGTAP de {ANO} não encontrado no FTP")
    return nomes[-1]


def main():
    aa = str(ANO)[2:]
    print(f"SIH/SUS RD {UF} {ANO}")
    for mes in range(1, 13):
        nome = f"RD{UF}{aa}{mes:02d}.dbc"
        baixar_ftp(FTP_DATASUS, DIR_SIH, nome, RAW / "sih" / nome)

    print("SIGTAP")
    nome = arquivo_sigtap()
    baixar_ftp(FTP_SIGTAP, DIR_SIGTAP, nome, RAW / "sigtap" / nome)

    print("CID-10")
    baixar_http(URL_CID, RAW / "cid10" / "CID10CSV.zip")

    print("Municípios (IBGE)")
    destino = RAW / "ibge" / "municipios.json"
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        dados = requests.get(URL_IBGE, timeout=120).json()
        destino.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        print(f"  baixado: {destino} ({len(dados)} municípios)")
    else:
        print(f"  já existe: {destino}")

    print("CNES (OpenDataSUS)")
    baixar_http(URL_CNES, RAW / "cnes" / "cnes_estabelecimentos.zip")


if __name__ == "__main__":
    main()
