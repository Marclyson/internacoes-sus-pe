# Etapa 7: dbt e gold

Código esperado ao fim do Módulo 7 (dbt, modelo e testes) da trilha de estudo da
[Dome Analytics](https://www.domeanalytics.com). São os arquivos da pasta de prática no fim do módulo,
para você comparar com os seus.

- `dbt/`: o projeto dbt que lê a silver e grava a camada gold em `dados/gold`. Tem as fontes e os
  modelos de staging, os seeds que traduzem os códigos do SIH, a fato e as cinco dimensões
  (lição 7.2), os testes do `_marts.yml` e da pasta `tests/` (lição 7.3), o
  `mart_indicadores_mensais`, a materialização `external`, que grava os marts em Parquet, e as
  descrições dos modelos e das colunas (lição 7.4).
- `Dockerfile`: o da [etapa 6](../etapa-6-silver/) mais a variável `DBT_PROFILES_DIR`, que diz ao
  dbt onde fica o `profiles.yml` (lição 7.2).
- `requirements.txt`: o da etapa 6 mais o `dbt-duckdb` e o `duckdb` (lição 7.2).
- `baixar.py`, `bronze.py`, `silver.py`, `docker-compose.yml`, `.dockerignore` e `referencias.py`:
  iguais aos da etapa 6.

O `gold.sql` da lição 7.1 não está aqui, porque o projeto dbt faz o mesmo trabalho.

Para rodar no PowerShell, dentro desta pasta e com o Docker Desktop aberto:

```powershell
docker compose build
docker compose run --rm referencias python baixar.py
docker compose run --rm referencias python bronze.py
docker compose run --rm referencias python silver.py
mkdir dados\gold
docker compose run --rm -w /app/dbt referencias dbt build
```

O `mkdir` só é preciso na primeira vez, porque o dbt não cria a pasta do `dw.duckdb`. O `dbt build`
roda 42 passos (5 seeds, 12 modelos e 25 testes) e termina com 41 aprovados e 1 aviso, o do
diagnóstico N18.5, que não existe na tabela da CID-10. Em `dados/gold` ficam o `dw.duckdb` e sete
arquivos Parquet, que somam cerca de 20 MB: a fato com 666.262 internações, as cinco dimensões e o
resumo mensal com 2.912 linhas, uma por mês e hospital. Os arquivos são iguais aos que o `dbt/` do
projeto grava.

Para ver a documentação do modelo, rode
`docker compose run --rm -w /app/dbt referencias dbt docs generate --static` e abra
`dbt\target\static_index.html` no navegador.
