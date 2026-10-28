"""Camada silver com PySpark: tipos corretos, campos derivados e tabelas de referência limpas.

Saídas em dados/silver (Parquet):
- internacoes/      uma linha por AIH, particionada por ano e mês de competência
- procedimentos/    SIGTAP com grupo, subgrupo e forma de organização
- diagnosticos/     CID-10 por subcategoria, com categoria, grupo e capítulo
- municipios/       municípios do IBGE com código de 6 dígitos (o usado no SUS)
- estabelecimentos/ estabelecimentos do CNES na UF do projeto
"""
import os

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

DADOS = os.environ.get("DADOS", "dados")
ANO = os.environ.get("ANO", "2024")
UF = os.environ.get("UF", "PE").upper()
# Código de cada UF no IBGE, usado para filtrar o CNES
CODIGOS_UF = {
    "RO": 11, "AC": 12, "AM": 13, "RR": 14, "PA": 15, "AP": 16, "TO": 17,
    "MA": 21, "PI": 22, "CE": 23, "RN": 24, "PB": 25, "PE": 26, "AL": 27, "SE": 28, "BA": 29,
    "MG": 31, "ES": 32, "RJ": 33, "SP": 35, "PR": 41, "SC": 42, "RS": 43,
    "MS": 50, "MT": 51, "GO": 52, "DF": 53,
}
if UF not in CODIGOS_UF:
    raise SystemExit(f"UF desconhecida: {UF}")
UF_IBGE = CODIGOS_UF[UF]
BRONZE = f"{DADOS}/bronze"
SILVER = f"{DADOS}/silver"

spark = (
    SparkSession.builder.appName("internacoes-sus-silver")
    .master("local[*]")
    .config("spark.sql.session.timeZone", "America/Recife")
    .config("spark.sql.shuffle.partitions", "8")
    .config("spark.driver.memory", "4g")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")


def texto(col):
    """Texto vazio vira nulo."""
    return F.when(F.trim(F.col(col)) == "", None).otherwise(F.trim(F.col(col)))


def data_aaaammdd(col):
    return F.to_date(texto(col), "yyyyMMdd")


def numero(col):
    return texto(col).cast("decimal(14,2)")


def inteiro(col):
    return texto(col).cast("int")


# ---------------------------------------------------------------- internações
# Só os arquivos do ano e da UF desta execução: a bronze pode guardar outros de execuções anteriores
rd = spark.read.parquet(f"{BRONZE}/sih_rd/RD{UF}{ANO[2:]}*.parquet")

internacoes = rd.select(
    texto("N_AIH").alias("n_aih"),
    texto("IDENT").alias("tipo_aih"),
    inteiro("ANO_CMPT").alias("ano_cmpt"),
    inteiro("MES_CMPT").alias("mes_cmpt"),
    F.lpad(texto("CNES"), 7, "0").alias("cnes"),
    texto("MUNIC_MOV").alias("munic_mov"),
    texto("MUNIC_RES").alias("munic_res"),
    texto("ESPEC").alias("espec_leito"),
    texto("CAR_INT").alias("carater_atendimento"),
    texto("COMPLEX").alias("complexidade"),
    texto("PROC_REA").alias("proc_realizado"),
    texto("PROC_SOLIC").alias("proc_solicitado"),
    F.upper(F.substring(texto("DIAG_PRINC"), 1, 4)).alias("diag_principal"),
    texto("SEXO").alias("sexo"),
    texto("RACA_COR").alias("raca_cor"),
    texto("COD_IDADE").alias("cod_idade"),
    inteiro("IDADE").alias("idade"),
    data_aaaammdd("DT_INTER").alias("dt_internacao"),
    data_aaaammdd("DT_SAIDA").alias("dt_saida"),
    inteiro("DIAS_PERM").alias("dias_permanencia"),
    inteiro("UTI_MES_TO").alias("dias_uti"),
    F.coalesce(inteiro("MORTE"), F.lit(0)).cast("boolean").alias("obito"),
    numero("VAL_TOT").alias("valor_total"),
    numero("VAL_SH").alias("valor_servicos_hosp"),
    numero("VAL_SP").alias("valor_servicos_prof"),
    numero("VAL_UTI").alias("valor_uti"),
    texto("ARQUIVO_ORIGEM").alias("arquivo_origem"),
)

# Idade em anos: o SUS informa a unidade em COD_IDADE (2 dias, 3 meses, 4 anos, 5 = 100 + anos)
internacoes = internacoes.withColumn(
    "idade_anos",
    F.when(F.col("cod_idade") == "4", F.col("idade"))
    .when(F.col("cod_idade") == "5", F.col("idade") + 100)
    .when(F.col("cod_idade").isin("2", "3"), F.lit(0)),
).drop("idade", "cod_idade")

internacoes = internacoes.withColumn(
    "faixa_etaria",
    F.when(F.col("idade_anos").isNull(), "Ignorada")
    .when(F.col("idade_anos") < 1, "Menor de 1 ano")
    .when(F.col("idade_anos") < 15, "1 a 14 anos")
    .when(F.col("idade_anos") < 30, "15 a 29 anos")
    .when(F.col("idade_anos") < 45, "30 a 44 anos")
    .when(F.col("idade_anos") < 60, "45 a 59 anos")
    .when(F.col("idade_anos") < 75, "60 a 74 anos")
    .otherwise("75 anos ou mais"),
)

# A mesma AIH pode aparecer de novo em meses seguintes (reapresentação). Fica a última competência.
ultima = Window.partitionBy("n_aih", "tipo_aih").orderBy(F.col("ano_cmpt").desc(), F.col("mes_cmpt").desc())
antes = internacoes.count()
internacoes = (
    internacoes.withColumn("_ordem", F.row_number().over(ultima))
    .filter(F.col("_ordem") == 1)
    .drop("_ordem")
)
depois = internacoes.count()

(
    internacoes.repartition("ano_cmpt", "mes_cmpt")
    .write.mode("overwrite")
    .partitionBy("ano_cmpt", "mes_cmpt")
    .parquet(f"{SILVER}/internacoes")
)
print(f"internacoes: {antes:,} lidas, {depois:,} gravadas ({antes - depois:,} reapresentações removidas)")


# ---------------------------------------------------------------- SIGTAP
def largura_fixa(arquivo, campos):
    """Lê um arquivo de largura fixa do SIGTAP. campos = [(nome, inicio, tamanho)]."""
    linhas = spark.read.text(arquivo)
    return linhas.select(*[F.trim(F.substring("value", ini, tam)).alias(nome) for nome, ini, tam in campos])


def ler_csv(caminho, **opcoes):
    return spark.read.options(**opcoes).csv(caminho)


proc = largura_fixa(
    f"{BRONZE}/sigtap/{ANO}/tb_procedimento.txt",
    [("cod_procedimento", 1, 10), ("procedimento", 11, 250), ("tp_complexidade", 261, 1),
     ("qt_dias_permanencia", 267, 4), ("vl_sh", 283, 10), ("vl_sp", 303, 10)],
)
grupo = largura_fixa(f"{BRONZE}/sigtap/{ANO}/tb_grupo.txt", [("co_grupo", 1, 2), ("grupo", 3, 100)])
subgrupo = largura_fixa(
    f"{BRONZE}/sigtap/{ANO}/tb_sub_grupo.txt", [("co_grupo", 1, 2), ("co_sub_grupo", 3, 2), ("subgrupo", 5, 100)]
)
forma = largura_fixa(
    f"{BRONZE}/sigtap/{ANO}/tb_forma_organizacao.txt",
    [("co_grupo", 1, 2), ("co_sub_grupo", 3, 2), ("co_forma", 5, 2), ("forma_organizacao", 7, 100)],
)

procedimentos = (
    proc.withColumn("co_grupo", F.substring("cod_procedimento", 1, 2))
    .withColumn("co_sub_grupo", F.substring("cod_procedimento", 3, 2))
    .withColumn("co_forma", F.substring("cod_procedimento", 5, 2))
    .join(grupo, "co_grupo", "left")
    .join(subgrupo, ["co_grupo", "co_sub_grupo"], "left")
    .join(forma, ["co_grupo", "co_sub_grupo", "co_forma"], "left")
    .withColumn("qt_dias_permanencia", F.col("qt_dias_permanencia").cast("int"))
    # valores do SIGTAP vêm em centavos
    .withColumn("valor_sh_tabela", (F.col("vl_sh").cast("long") / 100).cast("decimal(12,2)"))
    .withColumn("valor_sp_tabela", (F.col("vl_sp").cast("long") / 100).cast("decimal(12,2)"))
    .drop("vl_sh", "vl_sp")
)
procedimentos.write.mode("overwrite").parquet(f"{SILVER}/procedimentos")
print(f"procedimentos: {procedimentos.count():,}")


# ---------------------------------------------------------------- CID-10
cid_opts = dict(sep=";", header=True)
subcat = ler_csv(f"{BRONZE}/cid10/CID-10-SUBCATEGORIAS.CSV", **cid_opts).select(
    F.col("SUBCAT").alias("cod_cid"), F.col("DESCRICAO").alias("diagnostico")
)
categ = ler_csv(f"{BRONZE}/cid10/CID-10-CATEGORIAS.CSV", **cid_opts).select(
    F.col("CAT").alias("cod_categoria"), F.col("DESCRICAO").alias("categoria")
)
grupos = ler_csv(f"{BRONZE}/cid10/CID-10-GRUPOS.CSV", **cid_opts).select(
    F.col("CATINIC").alias("g_ini"), F.col("CATFIM").alias("g_fim"), F.col("DESCRICAO").alias("grupo_cid")
)
capitulos = ler_csv(f"{BRONZE}/cid10/CID-10-CAPITULOS.CSV", **cid_opts).select(
    F.col("NUMCAP").cast("int").alias("num_capitulo"),
    F.col("CATINIC").alias("c_ini"), F.col("CATFIM").alias("c_fim"),
    # "Capítulo XV - Gravidez, parto e puerpério" -> "Gravidez, parto e puerpério" (o número já está em num_capitulo)
    F.regexp_replace("DESCRICAO", r"^Cap\S*\s+[IVXL]+\s*-\s*", "").alias("capitulo"),
)

# O SIH usa a subcategoria (4 caracteres) ou só a categoria (3). As categorias entram como linha própria.
cid = subcat.unionByName(categ.select(F.col("cod_categoria").alias("cod_cid"), F.col("categoria").alias("diagnostico")))
cid = (
    cid.withColumn("cod_categoria", F.substring("cod_cid", 1, 3))
    .join(categ, "cod_categoria", "left")
    .join(F.broadcast(grupos), F.col("cod_categoria").between(F.col("g_ini"), F.col("g_fim")), "left")
    .join(F.broadcast(capitulos), F.col("cod_categoria").between(F.col("c_ini"), F.col("c_fim")), "left")
    .withColumn("capitulo", F.regexp_replace("capitulo", r"\s+", " "))
    .drop("g_ini", "g_fim", "c_ini", "c_fim")
    .dropDuplicates(["cod_cid"])
)
cid.write.mode("overwrite").parquet(f"{SILVER}/diagnosticos")
print(f"diagnosticos: {cid.count():,}")


# ---------------------------------------------------------------- municípios (IBGE)
ibge = spark.read.option("multiLine", True).json(f"{BRONZE}/ibge/municipios.json")
municipios = ibge.select(
    F.col("id").cast("string").alias("cod_ibge"),
    F.substring(F.col("id").cast("string"), 1, 6).alias("cod_municipio"),
    F.col("nome").alias("municipio"),
    F.col("`regiao-imediata`.`regiao-intermediaria`.UF.sigla").alias("uf"),
    F.col("`regiao-imediata`.`regiao-intermediaria`.UF.regiao.nome").alias("regiao"),
    F.col("`regiao-imediata`.`regiao-intermediaria`.nome").alias("regiao_intermediaria"),
    F.col("`regiao-imediata`.nome").alias("regiao_imediata"),
)
municipios.write.mode("overwrite").parquet(f"{SILVER}/municipios")
print(f"municipios: {municipios.count():,}")


# ---------------------------------------------------------------- estabelecimentos (CNES)
cnes = ler_csv(f"{BRONZE}/cnes/cnes_estabelecimentos.csv", sep=";", header=True, quote='"')
estabelecimentos = (
    cnes.filter(F.col("CO_UF").cast("int") == UF_IBGE)
    .select(
        F.lpad(F.col("CO_CNES"), 7, "0").alias("cnes"),
        F.col("NO_FANTASIA").alias("estabelecimento"),
        F.col("NO_RAZAO_SOCIAL").alias("razao_social"),
        F.col("CO_IBGE").alias("cod_municipio"),
        F.col("DS_ESFERA_ADMINISTRATIVA").alias("esfera_administrativa"),
        F.col("TP_UNIDADE").alias("tipo_unidade"),
        F.col("NU_LATITUDE").cast("double").alias("latitude"),
        F.col("NU_LONGITUDE").cast("double").alias("longitude"),
    )
    .dropDuplicates(["cnes"])
)
estabelecimentos.write.mode("overwrite").parquet(f"{SILVER}/estabelecimentos")
print(f"estabelecimentos: {estabelecimentos.count():,}")

spark.stop()
