with limites as (
    select min(dt_internacao) as inicio, max(dt_saida) as fim
    from {{ ref('stg_internacoes') }}
)
select
    cast(d as date)                             as data,
    year(d)                                     as ano,
    month(d)                                    as mes,
    strftime(d, '%Y-%m')                        as ano_mes,
    ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'][month(d)] as mes_abrev,
    isodow(d)                                   as dia_semana,
    ['seg','ter','qua','qui','sex','sáb','dom'][isodow(d)] as dia_semana_abrev
from limites, range(date_trunc('year', inicio), date_trunc('year', fim) + interval 1 year, interval 1 day) t(d)
