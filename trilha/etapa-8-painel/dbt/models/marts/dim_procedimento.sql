select
    cod_procedimento,
    procedimento,
    grupo,
    subgrupo,
    forma_organizacao,
    qt_dias_permanencia                         as dias_permanencia_tabela,
    valor_sh_tabela,
    valor_sp_tabela
from {{ ref('stg_procedimentos') }}
