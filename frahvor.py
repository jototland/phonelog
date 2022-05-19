from collections import namedtuple
from datetime import datetime, timedelta

import requests

from app import create_app
from app.db import get_db
import lxml.etree

_app = create_app(minimal_app=True)
_app.app_context().push()
_db = get_db()

zisson_credentials = (_app.config['ZISSON_API_USERNAME'],
                      _app.config['ZISSON_API_PASSWORD'])
diurnal_cycle = timedelta(hours=24)

now = datetime.utcnow().isoformat(timespec='seconds', sep=' ')
yesterday = (datetime.utcnow() - diurnal_cycle).isoformat(timespec='seconds', sep=' ')
response = requests.get(
    'https://api.zisson.com/api/simple/AgentQueueStatusEvents',
    auth = zisson_credentials,
    params = {
        'start_date': yesterday,
        'end_date': now,
        'logon_events': '1'
    })
response.raise_for_status()
xmldata = response.content
data = lxml.etree.fromstring(xmldata)

logon_events = []
LogonEvent = namedtuple('LogonEvent', ['agent_id', 'location_id', 'logon', 'timestamp'])
for logon_event in data.xpath('/AgentQueueStatusEvents/LogonEvents/LogonEvent'):
    agent_id = int(logon_event.xpath('LoginId')[0].text)
    location_id = int(logon_event.xpath('Userid')[0].text)
    logon = logon_event.xpath('EventName')[0].text == 'QueueLogon'
    time = logon_event.xpath('ActionTimeStampUtc')[0].text
    logon_events.append(LogonEvent(agent_id, location_id, logon, time))

logon_events.sort(key=lambda event: event.timestamp)

agent_location = {}
for event in logon_events:
    if event.logon:
        agent_location[event.agent_id] = event.location_id
    elif event.agent_id in agent_location:
        del agent_location[event.agent_id]


for agent_id,location_id in agent_location.items():
    agent_first_name, agent_last_name, agent_email = _db.execute(
        'select agent_first_name, agent_last_name, agent_email from agents where agent_id = ?',
        (agent_id, )).fetchone()
    location_number, location_name = _db.execute(
        'select location_number, location_name from internal_phones where location_id = ?',
        (location_id, )).fetchone()
    print(f"{agent_first_name} {agent_last_name} ({agent_email}): {location_name} ({location_number})")
