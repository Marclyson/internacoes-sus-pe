-- Uma linha por internação (AIH principal) aprovada no SIH/SUS.
-- Os códigos pequenos (sexo, raça/cor, caráter, leito, complexidade) já entram decodificados pelos seeds.
select
    i.n_aih,
    i.competencia,
    i.dt_internacao,
    i.dt_saida,
    i.cnes,
    i.munic_res                                 as cod_municipio_residencia,
    i.munic_mov                                 as cod_municipio_internacao,
    i.cod_procedimento,
    i.cod_cid,
    coalesce(sx.sexo, 'Ignorado')               as sexo,
    coalesce(rc.raca_cor, 'Sem informação')     as raca_cor,
    ca.carater_atendimento,
    ca.tipo_entrada,
    el.especialidade_leito,
    cx.complexidade,
    i.idade_anos,
    i.faixa_etaria,
    i.dias_permanencia,
    i.dias_uti,
    i.dias_uti > 0                              as usou_uti,
    i.obito,
    i.munic_res <> i.munic_mov                  as internado_fora_do_municipio,
    i.valor_total,
    i.valor_servicos_hosp,
    i.valor_servicos_prof,
    i.valor_uti
from {{ ref('stg_internacoes') }} i
left join {{ ref('sexo') }} sx                  on sx.codigo = i.cod_sexo
left join {{ ref('raca_cor') }} rc              on rc.codigo = i.cod_raca_cor
left join {{ ref('carater_atendimento') }} ca   on ca.codigo = i.cod_carater
left join {{ ref('especialidade_leito') }} el   on el.codigo = i.cod_especialidade
left join {{ ref('complexidade') }} cx          on cx.codigo = i.cod_complexidade
