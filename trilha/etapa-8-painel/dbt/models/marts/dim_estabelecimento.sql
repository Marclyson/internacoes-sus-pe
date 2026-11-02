select
    e.cnes,
    coalesce(e.estabelecimento, e.razao_social) as estabelecimento,
    e.razao_social,
    e.cod_municipio,
    m.municipio,
    e.esfera_administrativa,
    e.latitude,
    e.longitude
from {{ ref('stg_estabelecimentos') }} e
left join {{ ref('stg_municipios') }} m on m.cod_municipio = e.cod_municipio
