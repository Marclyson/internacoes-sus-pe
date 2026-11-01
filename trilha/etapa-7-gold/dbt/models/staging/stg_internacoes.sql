-- Só a AIH principal (tipo 1). A AIH tipo 5 é a continuação de uma internação de longa permanência
-- e contaria a mesma internação duas vezes.
select
    n_aih,
    make_date(ano_cmpt, mes_cmpt, 1)          as competencia,
    dt_internacao,
    dt_saida,
    cnes,
    munic_res,
    munic_mov,
    proc_realizado                            as cod_procedimento,
    diag_principal                            as cod_cid,
    sexo                                      as cod_sexo,
    raca_cor                                  as cod_raca_cor,
    carater_atendimento                       as cod_carater,
    espec_leito                               as cod_especialidade,
    complexidade                              as cod_complexidade,
    idade_anos,
    faixa_etaria,
    dias_permanencia,
    coalesce(dias_uti, 0)                     as dias_uti,
    obito,
    valor_total,
    valor_servicos_hosp,
    valor_servicos_prof,
    valor_uti
from {{ source('silver', 'internacoes') }}
where tipo_aih = '1'
