select cod_cid, diagnostico, cod_categoria, categoria, grupo_cid, num_capitulo, capitulo
from {{ ref('stg_diagnosticos') }}
