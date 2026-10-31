# Etapa 5: raw e bronze

Código esperado ao fim do Módulo 5 (Raw e bronze) da trilha de estudo da
[Dome Analytics](https://www.domeanalytics.com). São os arquivos da pasta de prática no fim do módulo,
para você comparar com os seus.

- `baixar.py`: baixa as tabelas de referência e o RD de um ano inteiro do FTP do DATASUS para
  `dados/raw`. Pula o que já existe, grava cada arquivo primeiro como `.part` e avisa os meses que
  ainda não foram publicados (lição 5.1).
- `bronze.py`: grava a camada bronze em `dados/bronze`. O RD vira um Parquet por mês, com todas as
  colunas como texto e a coluna `ARQUIVO_ORIGEM` com o nome do DBC (lições 5.2 e 5.3). As tabelas do
  SIGTAP, da CID-10 e do CNES saem do zip e são convertidas de Latin-1 para UTF-8, e o JSON do IBGE é
  copiado (lição 5.3).
- `requirements.txt`: o da [etapa 4](../etapa-4-docker/) mais o `datasus-dbc` e a `pyarrow`
  (lição 5.2).
- `Dockerfile`, `.dockerignore`, `docker-compose.yml` e `referencias.py`: iguais aos da etapa 4.

Para rodar no PowerShell, dentro desta pasta e com o Docker Desktop aberto:

```powershell
docker compose build
docker compose run --rm referencias python baixar.py
docker compose run --rm referencias python bronze.py
```

O `baixar.py` traz cerca de 100 MB para `dados/raw`, e o `bronze.py` grava cerca de 210 MB em
`dados/bronze`, quase tudo no CSV do CNES. Rodando de novo, os dois pulam o que já existe. Para outra
UF ou outro ano, use `-e`, como em `docker compose run --rm -e UF=PB referencias python baixar.py`, e
passe o mesmo `-e` ao `bronze.py`.
