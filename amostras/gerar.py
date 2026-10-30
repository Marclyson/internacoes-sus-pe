"""Amostra para estudo: as internações de moradores do Recife numa competência, num CSV pequeno.

Lê a camada gold e grava amostras/internacoes-recife-AAAA-MM.csv, com uma linha por internação e os
nomes do hospital e do capítulo da CID já resolvidos. É a tabela usada nos exercícios de SQL da
trilha de estudo da Dome Analytics; as respostas dos exercícios saem deste arquivo, então mudar as
colunas ou o filtro muda as respostas.

Grava também, para a lição de joins, as mesmas internações com os códigos no lugar dos nomes
(internacoes-codigos-recife-AAAA-MM.csv, com cnes e cod_cid) e duas tabelas de apoio só com os
códigos que aparecem nelas: hospitais-recife-AAAA-MM.csv e diagnosticos-recife-AAAA-MM.csv.

Uso, dentro do contêiner, depois de rodar o pipeline de 2024 para PE:
    python amostras/gerar.py              (competência de março de 2024)
    python amostras/gerar.py 2024-05      (outra competência)
"""
import os
import sys
from pathlib import Path

import duckdb

DADOS = Path(os.environ.get("DADOS", "dados"))
GOLD = DADOS / "gold"
AQUI = Path(__file__).parent
RECIFE = "261160"   # código do IBGE com 6 dígitos, como vem no SIH

competencia = sys.argv[1] if len(sys.argv) > 1 else "2024-03"
saida = AQUI / f"internacoes-recife-{competencia}.csv"

con = duckdb.connect()
con.sql(f"""
    create table amostra as
    select f.n_aih as aih, f.dt_internacao as data_internacao, f.dt_saida as data_saida, f.sexo,
           f.idade_anos as idade, coalesce(e.estabelecimento, f.cnes) as hospital,
           coalesce(d.capitulo, 'Sem diagnóstico') as capitulo_cid, f.carater_atendimento as carater,
           f.dias_permanencia, f.usou_uti, f.obito, f.valor_total
    from read_parquet('{GOLD / "fato_internacao.parquet"}') f
    left join read_parquet('{GOLD / "dim_estabelecimento.parquet"}') e using (cnes)
    left join read_parquet('{GOLD / "dim_diagnostico.parquet"}') d using (cod_cid)
    where f.cod_municipio_residencia = '{RECIFE}' and f.competencia = date '{competencia}-01'
    order by f.dt_internacao, f.n_aih
""")
total = con.sql("select count(*) from amostra").fetchone()[0]
if not total:
    sys.exit(f"Nenhuma internação de moradores do Recife na competência {competencia}. "
             "Rode antes o pipeline do ano dessa competência para PE.")
con.sql(f"copy amostra to '{saida}' (header, delimiter ',')")
print(f"{total} internações em {saida} ({saida.stat().st_size / 2**20:.1f} MB)")

# Versão com códigos e as tabelas de apoio, para juntar com join.
con.sql(f"""
    create table codigos as
    select n_aih as aih, dt_internacao as data_internacao, dt_saida as data_saida, sexo,
           idade_anos as idade, cnes, cod_cid, carater_atendimento as carater,
           dias_permanencia, usou_uti, obito, valor_total
    from read_parquet('{GOLD / "fato_internacao.parquet"}')
    where cod_municipio_residencia = '{RECIFE}' and competencia = date '{competencia}-01'
    order by dt_internacao, n_aih
""")
tabelas = {
    f"internacoes-codigos-recife-{competencia}.csv": "select * from codigos",
    f"hospitais-recife-{competencia}.csv": f"""
        select cnes, estabelecimento as hospital, municipio
        from read_parquet('{GOLD / "dim_estabelecimento.parquet"}')
        where cnes in (select cnes from codigos) order by cnes""",
    f"diagnosticos-recife-{competencia}.csv": f"""
        select cod_cid, diagnostico, categoria, capitulo
        from read_parquet('{GOLD / "dim_diagnostico.parquet"}')
        where cod_cid in (select cod_cid from codigos) order by cod_cid""",
}
for nome, consulta in tabelas.items():
    arq = AQUI / nome
    con.sql(f"copy ({consulta}) to '{arq}' (header, delimiter ',')")
    n = con.sql(f"select count(*) from ({consulta})").fetchone()[0]
    print(f"{n} linhas em {arq}")
