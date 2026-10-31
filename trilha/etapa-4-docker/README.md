# Etapa 4: Docker

Código esperado ao fim do Módulo 4 (Docker) da trilha de estudo da
[Dome Analytics](https://www.domeanalytics.com). São os arquivos da pasta de prática no fim do módulo,
para você comparar com os seus.

- `Dockerfile`: monta a imagem `estudos` a partir de `python:3.12-slim-bookworm`, instala as
  bibliotecas do `requirements.txt` e copia o script (lição 4.2).
- `.dockerignore`: deixa fora da imagem o `.venv`, a pasta `dados` e o clone `internacoes-sus-pe`
  (lição 4.2).
- `docker-compose.yml`: o serviço `referencias`, com esta pasta ligada a `/app` e a UF e o ano lidos
  das variáveis `UF` e `ANO` (lição 4.3).
- `referencias.py`: o script da [etapa 3](../etapa-3-python/), com o comentário da primeira linha
  mudado na lição 4.2.
- `requirements.txt`: igual ao da etapa 3.

Para rodar no PowerShell, dentro desta pasta e com o Docker Desktop aberto:

```powershell
docker compose run --rm referencias
```

Na primeira vez, o Compose monta a imagem antes de rodar. Os downloads, cerca de 55 MB, vão para
`dados/raw` nesta pasta, e na segunda execução o script não baixa nada. Para outro ano, use
`docker compose run --rm -e ANO=2023 referencias`.
