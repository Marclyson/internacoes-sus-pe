# Baixa as tabelas de referência do projeto para dados/raw
import ftplib
import json
import os
from pathlib import Path

import requests

uf = os.environ.get("UF", "PE").upper()
ano = int(os.environ.get("ANO", "2024"))
RAW = Path("dados/raw")

URL_CID = "http://www2.datasus.gov.br/cid10/V2008/downloads/CID10CSV.zip"
URL_IBGE = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
URL_CNES = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/CNES/cnes_estabelecimentos.zip"
FTP_SIGTAP = "ftp2.datasus.gov.br"
DIR_SIGTAP = "/pub/sistemas/tup/downloads"


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


def arquivo_sigtap(ano):
    with ftplib.FTP(FTP_SIGTAP, timeout=120) as ftp:
        ftp.login()
        ftp.cwd(DIR_SIGTAP)
        nomes = []
        for nome in ftp.nlst():
            if nome.startswith(f"TabelaUnificada_{ano}"):
                nomes.append(nome)
    return sorted(nomes)[-1]


def nome_rd(ano, mes, uf="PE"):
    return f"RD{uf}{str(ano)[2:]}{mes:02d}.dbc"


print("CID-10")
baixar_http(URL_CID, RAW / "cid10" / "CID10CSV.zip")

print("Municípios (IBGE)")
destino = RAW / "ibge" / "municipios.json"
if destino.exists():
    print(f"  já existe: {destino}")
else:
    destino.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(URL_IBGE, timeout=120)
    r.raise_for_status()
    municipios = r.json()
    destino.write_text(json.dumps(municipios, ensure_ascii=False), encoding="utf-8")
    print(f"  baixado: {destino} ({len(municipios)} municípios)")

print("CNES")
baixar_http(URL_CNES, RAW / "cnes" / "cnes_estabelecimentos.zip")

print(f"SIGTAP {ano}")
nome = arquivo_sigtap(ano)
baixar_ftp(FTP_SIGTAP, DIR_SIGTAP, nome, RAW / "sigtap" / nome)

faltam = 0
for mes in range(1, 13):
    if not (RAW / "sih" / nome_rd(ano, mes, uf)).exists():
        faltam = faltam + 1
print(f"RD {uf} {ano}: faltam {faltam} de 12, que você baixa no Módulo 5")
