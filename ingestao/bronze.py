"""Camada bronze: os arquivos brutos em formato legível, sem nenhuma regra de negócio.

- SIH: cada .dbc (DBF comprimido do DATASUS) vira um Parquet com todas as colunas como texto
- SIGTAP, CID-10 e CNES: os arquivos de dentro dos .zip são extraídos como estão
- IBGE: o JSON da API é copiado
"""
import io
import os
import shutil
import struct
import tempfile
import zipfile
from pathlib import Path

import datasus_dbc
import pyarrow as pa
import pyarrow.parquet as pq
import numpy as np

ANO = os.environ.get("ANO", "2024")
UF = os.environ.get("UF", "PE").upper()
RAW = Path("dados/raw")
BRONZE = Path("dados/bronze")

ARQUIVOS_SIGTAP = ["tb_procedimento.txt", "tb_grupo.txt", "tb_sub_grupo.txt", "tb_forma_organizacao.txt"]
ARQUIVOS_CID = ["CID-10-CAPITULOS.CSV", "CID-10-GRUPOS.CSV", "CID-10-CATEGORIAS.CSV", "CID-10-SUBCATEGORIAS.CSV"]


def ler_dbf(caminho):
    """Lê um DBF inteiro de uma vez, com NumPy. Todas as colunas saem como texto, sem espaços nas pontas.

    O DBF tem um cabeçalho com a lista de campos e depois registros de tamanho fixo,
    então cada campo é uma fatia de colunas da matriz de bytes.
    """
    dados = caminho.read_bytes()
    n_registros, tam_cabecalho, tam_registro = struct.unpack("<IHH", dados[4:12])
    campos, pos, inicio = [], 32, 1  # o byte 0 de cada registro é a marca de excluído
    while dados[pos] != 0x0D:
        nome = dados[pos:pos + 11].split(b"\x00")[0].decode("ascii")
        tamanho = dados[pos + 16]
        campos.append((nome, inicio, tamanho))
        inicio += tamanho
        pos += 32
    matriz = np.frombuffer(dados, dtype=np.uint8, count=n_registros * tam_registro, offset=tam_cabecalho)
    matriz = matriz.reshape(n_registros, tam_registro)
    matriz = matriz[matriz[:, 0] != ord("*")]
    colunas = {}
    for nome, ini, tam in campos:
        bruto = np.ascontiguousarray(matriz[:, ini:ini + tam]).view(f"S{tam}").ravel()
        texto = np.char.strip(np.char.decode(bruto, "latin1"))
        colunas[nome] = pa.array(np.where(texto == "", None, texto), type=pa.string())
    return pa.table(colunas)


def sih_para_parquet():
    destino = BRONZE / "sih_rd"
    destino.mkdir(parents=True, exist_ok=True)
    total = 0
    # Só os arquivos do ano e da UF desta execução; outros que estejam na raw ficam de fora
    for dbc in sorted((RAW / "sih").glob(f"RD{UF}{ANO[2:]}*.dbc")):
        saida = destino / f"{dbc.stem}.parquet"
        if saida.exists():
            print(f"  já existe: {saida}")
            continue
        with tempfile.TemporaryDirectory() as tmp:
            # A descompressão lê o arquivo em pedaços pequenos. Numa pasta montada do Windows
            # isso leva minutos; copiando antes para o disco do contêiner, leva menos de 1 s.
            local = Path(tmp) / dbc.name
            shutil.copy(dbc, local)
            dbf = Path(tmp) / f"{dbc.stem}.dbf"
            datasus_dbc.decompress(str(local), str(dbf))
            t = ler_dbf(dbf)
        colunas = t.column_names
        t = t.append_column("ARQUIVO_ORIGEM", pa.array([dbc.name] * t.num_rows, type=pa.string()))
        pq.write_table(t, saida, compression="zstd")
        total += t.num_rows
        print(f"  {dbc.name}: {t.num_rows:,} linhas, {len(colunas)} colunas")
    print(f"  total novo: {total:,} linhas")


def extrair(zip_path, nomes, destino):
    """Extrai do .zip e converte de Latin-1 (padrão do DATASUS) para UTF-8."""
    destino.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        for nome in nomes:
            alvo = destino / nome
            if not alvo.exists():
                with z.open(nome) as origem, open(alvo, "w", encoding="utf-8", newline="") as f:
                    texto = io.TextIOWrapper(origem, encoding="latin1", newline="")
                    shutil.copyfileobj(texto, f)
            print(f"  {alvo}")


def main():
    print("SIH/SUS RD")
    sih_para_parquet()
    print("SIGTAP")
    sigtap = sorted((RAW / "sigtap").glob(f"TabelaUnificada_{ANO}*.zip"))[-1]
    extrair(sigtap, ARQUIVOS_SIGTAP, BRONZE / "sigtap" / ANO)
    print("CID-10")
    extrair(RAW / "cid10" / "CID10CSV.zip", ARQUIVOS_CID, BRONZE / "cid10")
    print("CNES")
    extrair(RAW / "cnes" / "cnes_estabelecimentos.zip", ["cnes_estabelecimentos.csv"], BRONZE / "cnes")
    print("IBGE")
    (BRONZE / "ibge").mkdir(parents=True, exist_ok=True)
    shutil.copy(RAW / "ibge" / "municipios.json", BRONZE / "ibge" / "municipios.json")
    print(f"  {BRONZE / 'ibge' / 'municipios.json'}")


if __name__ == "__main__":
    main()
