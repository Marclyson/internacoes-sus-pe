# Grava a camada bronze: o RD em Parquet, um arquivo por mês, e as tabelas de referência em UTF-8
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import datasus_dbc
import pyarrow as pa
import pyarrow.parquet as pq

uf = os.environ.get("UF", "PE").upper()
ano = os.environ.get("ANO", "2024")
RAW = Path("dados/raw")
BRONZE = Path("dados/bronze")

ARQUIVOS_SIGTAP = ["tb_procedimento.txt", "tb_grupo.txt", "tb_sub_grupo.txt", "tb_forma_organizacao.txt"]
ARQUIVOS_CID = ["CID-10-CAPITULOS.CSV", "CID-10-GRUPOS.CSV", "CID-10-CATEGORIAS.CSV", "CID-10-SUBCATEGORIAS.CSV"]


def campos_dbf(dados):
    tam_cabecalho = int.from_bytes(dados[8:10], "little")
    n_campos = (tam_cabecalho - 33) // 32
    campos = []
    inicio = 1
    for i in range(n_campos):
        pos = 32 + i * 32
        nome = dados[pos:pos + 11].split(b"\x00")[0].decode("ascii")
        tamanho = dados[pos + 16]
        campos.append((nome, inicio, tamanho))
        inicio = inicio + tamanho
    return campos


def ler_dbf(caminho):
    dados = caminho.read_bytes()
    n_registros = int.from_bytes(dados[4:8], "little")
    tam_cabecalho = int.from_bytes(dados[8:10], "little")
    tam_registro = int.from_bytes(dados[10:12], "little")
    campos = campos_dbf(dados)
    colunas = {}
    for nome, inicio, tamanho in campos:
        colunas[nome] = []
    for i in range(n_registros):
        comeco = tam_cabecalho + i * tam_registro
        registro = dados[comeco:comeco + tam_registro]
        if registro[0:1] != b"*":
            for nome, inicio, tamanho in campos:
                texto = registro[inicio:inicio + tamanho].decode("latin1").strip()
                if texto == "":
                    texto = None
                colunas[nome].append(texto)
    for nome in colunas:
        colunas[nome] = pa.array(colunas[nome], type=pa.string())
    return pa.table(colunas)


def extrair(caminho_zip, nomes, destino):
    destino.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(caminho_zip) as z:
        for nome in nomes:
            alvo = destino / nome
            if alvo.exists():
                print(f"  já existe: {alvo}")
            else:
                texto = z.read(nome).decode("latin1")
                parcial = alvo.with_suffix(alvo.suffix + ".part")
                parcial.write_text(texto, encoding="utf-8")
                parcial.rename(alvo)
                print(f"  convertido: {alvo}")


destino = BRONZE / "sih_rd"
destino.mkdir(parents=True, exist_ok=True)
print(f"RD {uf} {ano}")
for dbc in sorted((RAW / "sih").glob(f"RD{uf}{ano[2:]}*.dbc")):
    saida = destino / f"{dbc.stem}.parquet"
    if saida.exists():
        print(f"  já existe: {saida}")
    else:
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / dbc.name
            shutil.copy(dbc, local)
            dbf = local.with_suffix(".dbf")
            datasus_dbc.decompress(str(local), str(dbf))
            tabela = ler_dbf(dbf)
        origem = pa.array([dbc.name] * tabela.num_rows, type=pa.string())
        tabela = tabela.append_column("ARQUIVO_ORIGEM", origem)
        parcial = saida.with_suffix(".parquet.part")
        pq.write_table(tabela, parcial, compression="zstd")
        parcial.rename(saida)
        print(f"  {dbc.name}: {tabela.num_rows:,} linhas, {tabela.num_columns} colunas")

print("SIGTAP")
sigtap = sorted((RAW / "sigtap").glob(f"TabelaUnificada_{ano}*.zip"))[-1]
extrair(sigtap, ARQUIVOS_SIGTAP, BRONZE / "sigtap" / ano)
print("CID-10")
extrair(RAW / "cid10" / "CID10CSV.zip", ARQUIVOS_CID, BRONZE / "cid10")
print("CNES")
extrair(RAW / "cnes" / "cnes_estabelecimentos.zip", ["cnes_estabelecimentos.csv"], BRONZE / "cnes")
print("IBGE")
(BRONZE / "ibge").mkdir(parents=True, exist_ok=True)
shutil.copy(RAW / "ibge" / "municipios.json", BRONZE / "ibge" / "municipios.json")
print(f"  copiado: {BRONZE / 'ibge' / 'municipios.json'}")
