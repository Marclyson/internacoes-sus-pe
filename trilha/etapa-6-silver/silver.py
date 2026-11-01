# Monta a camada silver com o Spark: as internações do RD, uma linha por AIH e gravadas por ano e mês,
# e as tabelas de referência do SIGTAP, da CID-10, do IBGE e do CNES
import os

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

uf = os.environ.get("UF", "PE").upper()
ano = os.environ.get("ANO", "2024")
BRONZE = "dados/bronze"
SILVER = "dados/silver"

spark = (
    SparkSession.builder.appName("estudos-silver")
    .master("local[*]")
    .config("spark.sql.session.timeZone", "America/Recife")
    .config("spark.sql.shuffle.partitions", "8")
    .config("spark.driver.memory", "4g")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")


# Tira os espaços das pontas; texto vazio vira nulo
def texto(col):
    return F.when(F.trim(F.col(col)) == "", None).otherwise(F.trim(F.col(col)))


def inteiro(col):
    return texto(col).cast("int")


def numero(col):
    return texto(col).cast("decimal(14,2)")


def data_aaaammdd(col):
    return F.to_date(texto(col), "yyyyMMdd")


rd = spark.read.parquet(f"{BRONZE}/sih_rd")
rd = rd.filter(F.col("ARQUIVO_ORIGEM").startswith(f"RD{uf}{ano[2:]}"))

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

# Idade em anos: COD_IDADE diz a unidade da IDADE (2 dias, 3 meses, 4 anos, 5 = 100 + anos)
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

# A AIH tipo 5 volta em cada competência até a alta: fica a linha mais recente, e a dt_saida desempata
ultima = Window.partitionBy("n_aih", "tipo_aih").orderBy(
    F.col("ano_cmpt").desc(), F.col("mes_cmpt").desc(), F.col("dt_saida").desc()
)
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
print(f"internacoes: {antes:,} lidas, {depois:,} gravadas ({antes - depois:,} linhas repetidas removidas)")


# Lê um arquivo de largura fixa do SIGTAP; cada campo é (nome, início, tamanho)
def largura_fixa(arquivo, campos):
    linhas = spark.read.text(arquivo)
    colunas = []
    for nome, inicio, tamanho in campos:
        colunas.append(F.trim(F.substring("value", inicio, tamanho)).alias(nome))
    return linhas.select(colunas)


SIGTAP = f"{BRONZE}/sigtap/{ano}"
proc = largura_fixa(
    f"{SIGTAP}/tb_procedimento.txt",
    [("cod_procedimento", 1, 10), ("procedimento", 11, 250), ("tp_complexidade", 261, 1),
     ("qt_dias_permanencia", 267, 4), ("vl_sh", 283, 10), ("vl_sp", 303, 10)],
)
grupo = largura_fixa(f"{SIGTAP}/tb_grupo.txt", [("co_grupo", 1, 2), ("grupo", 3, 100)])
subgrupo = largura_fixa(
    f"{SIGTAP}/tb_sub_grupo.txt", [("co_grupo", 1, 2), ("co_sub_grupo", 3, 2), ("subgrupo", 5, 100)]
)
forma = largura_fixa(
    f"{SIGTAP}/tb_forma_organizacao.txt",
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
    # O SIGTAP guarda os valores em centavos
    .withColumn("valor_sh_tabela", (F.col("vl_sh").cast("long") / 100).cast("decimal(12,2)"))
    .withColumn("valor_sp_tabela", (F.col("vl_sp").cast("long") / 100).cast("decimal(12,2)"))
    .drop("vl_sh", "vl_sp")
)
procedimentos.write.mode("overwrite").parquet(f"{SILVER}/procedimentos")
print(f"procedimentos: {procedimentos.count():,}")

CID = f"{BRONZE}/cid10"
subcat = spark.read.csv(f"{CID}/CID-10-SUBCATEGORIAS.CSV", sep=";", header=True).select(
    F.col("SUBCAT").alias("cod_cid"), F.col("DESCRICAO").alias("diagnostico")
)
categ = spark.read.csv(f"{CID}/CID-10-CATEGORIAS.CSV", sep=";", header=True).select(
    F.col("CAT").alias("cod_categoria"), F.col("DESCRICAO").alias("categoria")
)
grupos = spark.read.csv(f"{CID}/CID-10-GRUPOS.CSV", sep=";", header=True).select(
    F.col("CATINIC").alias("g_ini"), F.col("CATFIM").alias("g_fim"), F.col("DESCRICAO").alias("grupo_cid")
)
capitulos = spark.read.csv(f"{CID}/CID-10-CAPITULOS.CSV", sep=";", header=True).select(
    F.col("NUMCAP").cast("int").alias("num_capitulo"),
    F.col("CATINIC").alias("c_ini"),
    F.col("CATFIM").alias("c_fim"),
    # "Capítulo XV - Gravidez, parto e puerpério" vira "Gravidez, parto e puerpério"
    F.split("DESCRICAO", " - ")[1].alias("capitulo"),
)

# O RD usa a subcategoria (4 caracteres) ou só a categoria (3). As categorias entram como linha,
# menos as que já estão nas subcategorias com o mesmo código
so_categoria = categ.join(subcat, F.col("cod_categoria") == F.col("cod_cid"), "left_anti")
cid = subcat.unionByName(
    so_categoria.select(F.col("cod_categoria").alias("cod_cid"), F.col("categoria").alias("diagnostico"))
)
# Os grupos se encaixam uns nos outros: fica o de início mais alto e, no empate, o de fim mais baixo
mais_especifico = Window.partitionBy("cod_cid").orderBy(F.col("g_ini").desc(), F.col("g_fim"))
diagnosticos = (
    cid.withColumn("cod_categoria", F.substring("cod_cid", 1, 3))
    .join(categ, "cod_categoria", "left")
    .join(F.broadcast(grupos), F.col("cod_categoria").between(F.col("g_ini"), F.col("g_fim")), "left")
    .join(F.broadcast(capitulos), F.col("cod_categoria").between(F.col("c_ini"), F.col("c_fim")), "left")
    .withColumn("_ordem", F.row_number().over(mais_especifico))
    .filter(F.col("_ordem") == 1)
    .drop("g_ini", "g_fim", "c_ini", "c_fim", "_ordem")
)
diagnosticos.write.mode("overwrite").parquet(f"{SILVER}/diagnosticos")
print(f"diagnosticos: {diagnosticos.count():,}")

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

# O CNES traz o Brasil inteiro; o left_semi deixa só os estabelecimentos dos municípios da UF
cnes = spark.read.csv(f"{BRONZE}/cnes/cnes_estabelecimentos.csv", sep=";", header=True)
municipios_uf = municipios.filter(F.col("uf") == uf).select("cod_municipio")
estabelecimentos = cnes.join(F.broadcast(municipios_uf), F.col("CO_IBGE") == F.col("cod_municipio"), "left_semi").select(
    F.lpad(F.col("CO_CNES"), 7, "0").alias("cnes"),
    F.col("NO_FANTASIA").alias("estabelecimento"),
    F.col("NO_RAZAO_SOCIAL").alias("razao_social"),
    F.col("CO_IBGE").alias("cod_municipio"),
    F.col("DS_ESFERA_ADMINISTRATIVA").alias("esfera_administrativa"),
    F.col("TP_UNIDADE").alias("tipo_unidade"),
    F.col("NU_LATITUDE").cast("double").alias("latitude"),
    F.col("NU_LONGITUDE").cast("double").alias("longitude"),
)
estabelecimentos.write.mode("overwrite").parquet(f"{SILVER}/estabelecimentos")
print(f"estabelecimentos: {estabelecimentos.count():,}")

spark.stop()
