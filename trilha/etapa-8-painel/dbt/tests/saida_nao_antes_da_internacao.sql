-- Nenhuma internação pode ter saída antes da entrada
select n_aih, dt_internacao, dt_saida
from {{ ref('fato_internacao') }}
where dt_saida < dt_internacao
