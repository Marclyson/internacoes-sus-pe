select n_aih, valor_total, dias_permanencia
from {{ ref('fato_internacao') }}
where valor_total < 0 or dias_permanencia < 0 or dias_uti < 0
