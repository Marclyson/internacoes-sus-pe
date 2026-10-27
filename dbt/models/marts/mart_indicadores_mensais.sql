-- Indicadores por mês e hospital, a base das páginas de visão geral do painel.
select
    f.competencia,
    f.cnes,
    count(*)                                            as internacoes,
    sum(f.obito::int)                                   as obitos,
    round(100.0 * sum(f.obito::int) / count(*), 2)      as taxa_mortalidade_pct,
    round(avg(f.dias_permanencia), 2)                   as permanencia_media_dias,
    sum(f.usou_uti::int)                                as internacoes_com_uti,
    sum(f.valor_total)                                  as valor_total,
    round(sum(f.valor_total) / count(*), 2)             as valor_medio,
    sum((f.tipo_entrada = 'Urgência')::int)             as internacoes_urgencia
from {{ ref('fato_internacao') }} f
group by 1, 2
