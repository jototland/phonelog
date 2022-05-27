from ..db import add_to_schema
from .utils import (
    generate_create_table_sql,
    generate_namedtuple,
    generate_upsert_sql,
)


CallSession_fields = (
    ('call_session_id', str  , 'text primary key'),
    ('start_timestamp', float, 'real not null'   ),
    ('end_timestamp'  , float, 'real'            ))


CallSession = generate_namedtuple('CallSession',
                                  CallSession_fields)


add_to_schema(generate_create_table_sql('call_sessions',
                                        CallSession_fields))


add_to_schema("""\
create index call_sessions_start_timestamp_idx
on call_sessions (start_timestamp);""")


upsert_call_sessions = generate_upsert_sql('call_sessions',
                                      CallSession_fields,
                                      ('call_session_id', ))


CallChannel_fields = (
    ('call_channel_id'  , str  , 'text primary key'),
    ('call_session_id'  , str  , 'text references call_sessions (call_session_id) on delete cascade'),
    ('call_direction'   , str  , 'text not null'    ),
    ('a_number'         , int  , 'integer'          ),
    ('b_number'         , int  , 'integer'          ),
    ('end_point_class'  , str  , 'text not null'    ),
    ('call_state'       , str  , 'text not null'    ),
    ('active'           , int  , 'integer not null' ),
    ('answered'         , int  , 'integer not null' ),
    ('hangup_by'        , str  , 'text'             ),
    ('hangup_reason'    , str  , 'text'             ),
    ('call_timestamp'   , float, 'real not null'    ),
    ('ringing_timestamp', float, 'real'             ),
    ('answer_timestamp' , float, 'real'             ),
    ('hangup_timestamp' , float, 'real'             ),
    ('login_id'         , int  , 'integer'          ),
    ('location_id'      , int  , 'integer'          ),
    ('device_id'        , int  , 'integer'          ),
    ('service_number_id', int  , 'integer'          ))


CallChannel = generate_namedtuple('CallChannel',
                                  CallChannel_fields)


add_to_schema(generate_create_table_sql('call_channels',
                                        CallChannel_fields))

add_to_schema("""\
create index call_channels_call_session_idx
on call_channels (call_session_id);""")

upsert_call_channels = generate_upsert_sql('call_channels',
                                          CallChannel_fields,
                                          ('call_channel_id',))


Recording_fields = (
    ('recording_id', str, 'text primary key'),
    ('call_session_id', str, 'text references call_sessions (call_session_id) on delete cascade'),
    ('call_channel_id', str, 'text references call_channels (call_channel_id) on delete cascade'),
    ('start_timestamp', float, 'real not null'),
    ('stop_timestamp', float, 'real'),
    ('completed', int, 'integer'), # RecordingStatus=Completed (&& Active=false ?)
)

Recording = generate_namedtuple('Recording', Recording_fields)

add_to_schema(generate_create_table_sql('recordings', Recording_fields))

add_to_schema("""\
create index recordings_call_session_id_idx
on recordings (call_session_id);""")

upsert_recordings = generate_upsert_sql('recordings',
                                        Recording_fields,
                                        ('recording_id',))
