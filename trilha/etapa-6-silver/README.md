# Etapa 6: Spark e silver

Código esperado ao fim do Módulo 6 (Spark e silver) da trilha de estudo da
[Dome Analytics](https://www.domeanalytics.com). São os arquivos da pasta de prática no fim do módulo,
para você comparar com os seus.

- `silver.py`: lê a bronze com o Spark e grava a camada silver em `dados/silver`. As internações do RD
  ganham nomes e tipos (lições 6.1 e 6.2), ficam com uma linha por AIH, a da conta mais recente
  (lição 6.3), e são gravadas em pastas por ano e mês. As tabelas de procedimentos, diagnósticos,
  municípios e estabelecimentos saem do SIGTAP, da CID-10, do IBGE e do CNES, com joins (lição 6.4).
- `Dockerfile`: o da [etapa 5](../etapa-5-bronze/) mais o Java 17, que o Spark usa (lição 6.1).
- `requirements.txt`: o da etapa 5 mais o `pyspark` (lição 6.1).
- `baixar.py`, `bronze.py`, `docker-compose.yml`, `.dockerignore` e `referencias.py`: iguais aos da
  etapa 5.

Para rodar no PowerShell, dentro desta pasta e com o Docker Desktop aberto:

```powershell
docker compose build
docker compose run --rm referencias python baixar.py
docker compose run --rm referencias python bronze.py
docker compose run --rm referencias python silver.py
```

O `silver.py` grava cerca de 20 MB em `dados/silver`, em cinco tabelas: 668.001 internações,
4.844 procedimentos, 14.233 diagnósticos, 5.571 municípios e 16.338 estabelecimentos de Pernambuco.
Ele dá 4 GB de memória ao Spark, como o `spark/silver.py` do projeto. Rodando de novo, ele grava a
silver por cima. Para outra UF ou outro ano, passe o mesmo `-e` nos três scripts, como em
`docker compose run --rm -e UF=PB referencias python silver.py`.
