from ..db import add_to_schema
from .utils import (
    generate_create_table_sql,
    generate_namedtuple,
    generate_upsert_sql,
)


InternalPhone_fields = (
    ('location_id'          , int     , 'integer primary key'),
    ('location_number'      , int|None, 'integer unique'     ),
    ('location_name'        , str|None, 'text'               ),
    ('location_description' , str|None, 'text'               ),
    ('location_last_updated', float   , 'real'               ),
)

InternalPhone = generate_namedtuple('InternalPhone', InternalPhone_fields)


add_to_schema(generate_create_table_sql('internal_phones',
                                        InternalPhone_fields))


add_to_schema("""\
create index internal_phones_location_number_idx
on internal_phones (location_number);""")


upsert_internal_phones = generate_upsert_sql(
    'internal_phones',
    InternalPhone_fields,
    ('location_id', ))


ServiceNumber_fields = (
    ('service_number_id'          , int     , 'integer primary key'),
    ('service_number'             , int|None, 'integer unique'     ),
    ('service_number_description' , str|None, 'text'               ),
    ('service_number_last_updated', float   , 'real'               ),
)

ServiceNumber = generate_namedtuple('ServiceNumber',
                                    ServiceNumber_fields)
add_to_schema(generate_create_table_sql('service_numbers',
                                        ServiceNumber_fields))
add_to_schema("""\
create index service_numbers_service_number_idx
on service_numbers (service_number);
""")


upsert_service_numbers = generate_upsert_sql(
    'service_numbers',
    ServiceNumber_fields,
    ('service_number_id', ))


Agent_fields = (
    ('agent_id'          , int     , 'integer primary key'),
    ('agent_first_name'  , str|None, 'text'               ),
    ('agent_last_name'   , str|None, 'text'               ),
    ('agent_email'       , str|None, 'text'               ),
    ('agent_last_updated', float   , 'real'               ),
)


Agent = generate_namedtuple('Agent', Agent_fields)


add_to_schema(generate_create_table_sql('agents',
                                        Agent_fields))

upsert_agents = generate_upsert_sql(
    'agents',
    Agent_fields,
    ('agent_id', ))
