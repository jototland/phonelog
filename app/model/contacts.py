from ..db import add_to_schema
from .utils import (
    generate_create_table_sql,
    generate_namedtuple,
    generate_upsert_sql,
)

Contact_fields = (
    ('contact_id'          , int      , 'integer primary key'),
    ('first_name'          , str|None , 'text'               ),
    ('last_name'           , str|None , 'text'               ),
    ('email'               , str|None , 'text'               ),
    ('pstn_number'         , int|None , 'integer'            ),
    ('gsm_number'          , int|None , 'integer'            ),
    ('company'             , str|None , 'text'               ),
    ('comments'            , str|None , 'text'               ),
    ('title'               , str|None , 'text'               ),
    ('department'          , str|None , 'text'               ),
    ('address'             , str|None , 'text'               ),
    ('editable'            , bool|None, 'integer'            ),
    ('contact_last_updated', float    , 'real'               ),
)

Contact = generate_namedtuple('Contact', Contact_fields)


add_to_schema(generate_create_table_sql('contacts', Contact_fields))


add_to_schema("""\
create index contacts_pstn_number_idx on contacts (pstn_number);
create index contacts_gsm_number_idx on contacts (gsm_number);
""")


upsert_contacts = generate_upsert_sql(
    'contacts',
    Contact_fields,
    ('contact_id',)
)
