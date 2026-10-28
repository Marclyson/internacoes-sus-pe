"""Painel: agrega a camada gold com DuckDB e gera um HTML único, com os dados embutidos.

Saída: dados/painel/index.html (abre direto no navegador, sem servidor e sem biblioteca externa)
"""
import base64
import json
import os
from datetime import datetime
from pathlib import Path

import duckdb

DADOS = Path(os.environ.get("DADOS", "dados"))
GOLD = DADOS / "gold"
SAIDA = DADOS / "painel"
AQUI = Path(__file__).parent
TOP_HOSPITAIS = 40

con = duckdb.connect()
for tabela in ["fato_internacao", "dim_estabelecimento", "dim_procedimento", "dim_diagnostico", "dim_municipio"]:
    con.sql(f"create view {tabela} as select * from read_parquet('{GOLD / tabela}.parquet')")

con.sql("""
    create view base as
    select f.*, d.capitulo, d.num_capitulo, p.procedimento, p.grupo as grupo_procedimento,
           mr.municipio as municipio_residencia, mi.municipio as municipio_internacao
    from fato_internacao f
    left join dim_diagnostico d using (cod_cid)
    left join dim_procedimento p using (cod_procedimento)
    left join dim_municipio mr on mr.cod_municipio = f.cod_municipio_residencia
    left join dim_municipio mi on mi.cod_municipio = f.cod_municipio_internacao
""")


def linhas(sql, params=None):
    rel = con.execute(sql, params or [])
    cols = [c[0] for c in rel.description]
    return [dict(zip(cols, (float(v) if hasattr(v, "as_integer_ratio") and not isinstance(v, (int, bool)) else v for v in r))) for r in rel.fetchall()]


def recorte(filtro, params):
    """Todos os blocos do painel para um recorte (todos os hospitais ou um só)."""
    where = f"where {filtro}" if filtro else ""
    kpis = linhas(f"""
        select count(*) as internacoes,
               sum(valor_total) as valor_total,
               avg(valor_total) as valor_medio,
               avg(dias_permanencia) as permanencia_media,
               100.0 * avg(obito::int) as mortalidade,
               100.0 * avg((tipo_entrada = 'Urgência')::int) as urgencia,
               100.0 * avg(usou_uti::int) as uti,
               100.0 * avg(internado_fora_do_municipio::int) as fora_municipio
        from base {where}""", params)[0]
    mensal = linhas(f"""
        select month(competencia) as mes, count(*) as internacoes, sum(valor_total) as valor,
               100.0 * avg(obito::int) as mortalidade, avg(dias_permanencia) as permanencia
        from base {where} group by 1 order by 1""", params)
    capitulos = linhas(f"""
        select coalesce(capitulo, 'Sem classificação') as nome, any_value(num_capitulo) as num,
               count(*) as n, 100.0 * avg(obito::int) as mortalidade
        from base {where} group by 1 order by 3 desc, 1 limit 10""", params)
    procedimentos = linhas(f"""
        select procedimento as nome, count(*) as n, avg(valor_total) as valor_medio, avg(dias_permanencia) as permanencia
        from base {where} group by 1 order by 2 desc, 1 limit 10""", params)
    piramide = linhas(f"""
        select faixa_etaria as faixa, sexo, count(*) as n
        from base {where} {'and' if where else 'where'} sexo in ('Masculino', 'Feminino')
        group by 1, 2 order by 1, 2""", params)
    leitos = linhas(f"""
        select especialidade_leito as nome, count(*) as n
        from base {where} group by 1 order by 2 desc, 1 limit 6""", params)
    return dict(kpis=kpis, mensal=mensal, capitulos=capitulos, procedimentos=procedimentos, piramide=piramide, leitos=leitos)


hospitais = linhas(f"""
    select f.cnes, e.estabelecimento as nome, e.municipio, e.esfera_administrativa as esfera,
           count(*) as internacoes, sum(f.valor_total) as valor_total,
           avg(f.dias_permanencia) as permanencia_media, 100.0 * avg(f.obito::int) as mortalidade,
           100.0 * avg(f.usou_uti::int) as uti
    from fato_internacao f left join dim_estabelecimento e using (cnes)
    group by all order by internacoes desc, f.cnes limit {TOP_HOSPITAIS}""")

fluxo = linhas("""
    select municipio_residencia as origem, municipio_internacao as destino, count(*) as n
    from base where internado_fora_do_municipio and municipio_residencia is not null
    group by 1, 2 order by 3 desc, 1, 2 limit 12""")

destinos = linhas("""
    select municipio_internacao as nome, count(*) as n,
           100.0 * avg(internado_fora_do_municipio::int) as de_fora
    from base group by 1 order by 2 desc, 1 limit 8""")

ano = con.sql("select max(year(competencia)) from fato_internacao").fetchone()[0]
total_hospitais = con.sql("select count(distinct cnes) from fato_internacao").fetchone()[0]

dados = {
    "ano": ano,
    "uf": os.environ.get("UF", "PE").upper(),
    "gerado_em": datetime.now().strftime("%d/%m/%Y"),
    "total_hospitais": total_hospitais,
    "hospitais": hospitais,
    "fluxo": fluxo,
    "destinos": destinos,
    "recortes": {"todos": recorte("", [])},
}
for h in hospitais:
    dados["recortes"][h["cnes"]] = recorte("cnes = ?", [h["cnes"]])

SAIDA.mkdir(parents=True, exist_ok=True)
html = (AQUI / "template.html").read_text(encoding="utf-8")
html = html.replace("/*CSS*/", (AQUI / "painel.css").read_text(encoding="utf-8"))
html = html.replace("/*JS*/", (AQUI / "painel.js").read_text(encoding="utf-8"))
html = html.replace("/*LOGO*/", base64.b64encode((AQUI / "logo.webp").read_bytes()).decode("ascii"))
# "</" dentro do JSON fecharia a tag <script> antes da hora
json_dados = json.dumps(dados, ensure_ascii=False, default=str, separators=(",", ":")).replace("</", "<\\/")
html = html.replace("/*DADOS*/", json_dados)
(SAIDA / "index.html").write_text(html, encoding="utf-8")
print(f"painel: {SAIDA / 'index.html'} ({len(html) / 1024:.0f} KB, {len(hospitais)} hospitais com recorte próprio)")
