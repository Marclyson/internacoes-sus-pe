-- Reconciliação: o fato precisa ter exatamente as AIH principais da camada silver
with silver as (
    select count(*) as n from {{ source('silver', 'internacoes') }} where tipo_aih = '1'
), fato as (
    select count(*) as n from {{ ref('fato_internacao') }}
)
select silver.n as silver, fato.n as fato
from silver, fato
where silver.n <> fato.n
