#!/usr/bin/env bash
# Pipeline completo: download -> bronze -> silver (Spark) -> gold (dbt) -> painel
set -euo pipefail
cd "$(dirname "$0")"

echo "== 1/5 Download das fontes públicas"
python baixar.py

echo "== 2/5 Bronze: DBC e ZIP para formatos legíveis"
python bronze.py

echo "== 3/5 Silver: limpeza e tabelas de referência com Spark"
python silver.py

echo "== 4/5 Gold: modelo dimensional e testes com dbt"
mkdir -p dados/gold
(cd dbt && dbt build)

echo "== 5/5 Painel: indicadores da gold num HTML único"
python painel/gerar.py
