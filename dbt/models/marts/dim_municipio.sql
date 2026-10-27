select cod_municipio, cod_ibge, municipio, uf, regiao, regiao_intermediaria, regiao_imediata
from {{ ref('stg_municipios') }}
