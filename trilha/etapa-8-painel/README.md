# Etapa 8: painel e pipeline

Código esperado ao fim do Módulo 8 (Painel e fechamento) da trilha de estudo da
[Dome Analytics](https://www.domeanalytics.com). São os arquivos da pasta de prática no fim do módulo,
para você comparar com os seus. É o último marco da trilha.

- `painel/`: o `gerar.py`, que resume a gold com consultas do DuckDB (lição 8.1), e os arquivos do
  visual: `template.html`, `painel.css`, `painel.js` e `logo.webp`. O `gerar.py` troca os marcadores
  do template pelo CSS, pelo JavaScript, pelo logo em base64 e pelos dados em JSON, e grava um HTML
  único em `dados/painel/index.html` (lição 8.2). São os mesmos arquivos da [pasta painel](../../painel/)
  do projeto.
- `pipeline.sh`: roda as cinco etapas em sequência, do download ao painel, e para na primeira que
  falhar (lição 8.3).
- `baixar.py`, `bronze.py`, `silver.py`, `dbt/`, `Dockerfile`, `requirements.txt`,
  `docker-compose.yml`, `.dockerignore` e `referencias.py`: iguais aos da [etapa 7](../etapa-7-gold/).

Para rodar no PowerShell, dentro desta pasta e com o Docker Desktop aberto:

```powershell
docker compose build
docker compose run --rm referencias bash pipeline.sh
```

Numa pasta nova, depois do `build`, o pipeline baixou cerca de 100 MB e terminou em 2 min 13 s. O
`dbt build` roda os mesmos 42 passos da etapa 7, com 41 aprovados e 1 aviso, o do diagnóstico N18.5.
No fim, abra `dados\painel\index.html` no navegador. O arquivo tem 244 KB, traz recorte próprio para os
40 hospitais com mais internações e abre sem servidor e sem internet. Rodar de novo reaproveita o que
já está em `dados/raw` e `dados/bronze` e refaz a silver, a gold e o painel em menos de um minuto.

Para outro estado ou outro ano, defina `UF` ou `ANO` antes de rodar, como `$env:UF = "PB"`, e volte
ao padrão com `Remove-Item Env:UF`.

O `pipeline.sh` precisa do fim de linha do Linux (LF). O `.gitattributes` do repositório garante isso
no clone. Se você salvar o arquivo com o fim de linha do Windows (CRLF), o bash para logo na terceira
linha com `invalid option name`. No VS Code, troque CRLF por LF na barra de status e salve.

No projeto, os scripts ficam nas pastas `ingestao/` e `spark/`, e o serviço `pipeline` do
`docker-compose.yml` já roda o `pipeline.sh` sem precisar do `bash pipeline.sh` no comando. As
respostas às perguntas de entrevista da lição 8.3 estão nas seções Decisões e aprendizados e Limites
do [README do projeto](../../README.md).
