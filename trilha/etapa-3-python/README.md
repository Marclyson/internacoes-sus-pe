# Etapa 3: Python

Código esperado ao fim do Módulo 3 (Python do zero) da trilha de estudo da
[Dome Analytics](https://www.domeanalytics.com). Se o seu script travou ou deu resultado diferente,
compare com este.

- `referencias.py`: baixa as tabelas de referência do projeto para `dados/raw` (CID-10, municípios do
  IBGE, CNES e SIGTAP) e pula o que já foi baixado. A UF e o ano vêm das variáveis de ambiente `UF` e
  `ANO`, com Pernambuco e 2024 de padrão.
- `requirements.txt`: as bibliotecas do ambiente virtual, gravadas com `pip freeze` na lição 3.4.

Para rodar no PowerShell, dentro desta pasta:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python referencias.py
```

O script baixa cerca de 55 MB, quase tudo do CNES. Na segunda execução ele não baixa nada. Os 12
arquivos do RD ficam para o Módulo 5.

As funções de download são as mesmas do [ingestao/baixar.py](../../ingestao/baixar.py) do projeto.
