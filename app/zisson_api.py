from collections import namedtuple
from datetime import datetime, timedelta

from flask import current_app
import lxml.etree
import requests

from .db import get_db
from .parse_xml import subtext, subint


DIURNAL_CYCLE = timedelta(hours=24)

def zisson_api_get(path, params=None):
    if 'ZISSON_API_PASSWORD' not in current_app.config:
        return

    hostname = current_app.config['ZISSON_API_HOST']
    username = current_app.config['ZISSON_API_USERNAME']
    password = current_app.config['ZISSON_API_PASSWORD']
    try:
        response = requests.get(f'https://{hostname}/api/simple/{path}',
                                params=params,
                                auth=(username, password))
        response.raise_for_status()
        return response.content
    except requests.RequestException as err:
        current_app.logger.warn(str(err))
        return None


def dial(from_number, to_number):
    if isinstance(from_number, int):
        from_number = f"+{from_number}"
    if isinstance(to_number, int):
        to_number = f"+{to_number}"
    current_app.logger.info(f"======================================")
    current_app.logger.info(f"Dial from {from_number} to {to_number}")
    current_app.logger.info(f"======================================")
    response = zisson_api_get('Dial',
                   params = {
                       'from': from_number,
                       'to': to_number
                   })
    if response != "1":
        raise RuntimeError(f"Failed to dial from {from_number} to {to_number}")


LogonEvent = namedtuple('LogonEvent', ['agent_id', 'location_id', 'logon', 'timestamp'])

def get_agent_location_map():
    """returns a dict mapping agent_id to location_id"""
    now = (datetime.utcnow() + timedelta(seconds=5)).isoformat(timespec='seconds')+'Z'
    yesterday = (datetime.utcnow() - timedelta(hours=24)).isoformat(timespec='seconds')+'Z'
    xmldata = zisson_api_get('AgentQueueStatusEvents',
                              params = {
                                  'start_date': yesterday,
                                  'end_date': now,
                                  'logon_events': 1
                              })
    if xmldata == None:
        return {}
    data = lxml.etree.fromstring(xmldata)

    logon_events = []
    for logon_event in data.xpath('/AgentQueueStatusEvents/LogonEvents/LogonEvent'):
        logon_events.append(LogonEvent(
            agent_id = subint(logon_event, 'LoginId'),
            location_id = subint(logon_event, 'Userid'),
            logon = (subtext(logon_event, 'EventName') == 'QueueLogon'),
            timestamp = subtext(logon_event, 'ActionTimeStampUtc'),
        ))
    logon_events.sort(key = lambda event: event.timestamp)

    agent_location = {}
    for event in logon_events:
        if event.logon:
            agent_location[event.agent_id] = event.location_id
        elif event.agent_id in agent_location:
            del agent_location[event.agent_id]
    return agent_location


def email_to_current_phone(email):
    try:
        user_id = get_db().execute(
            "select agent_id from agents where agent_email = ?",
            (email,)).fetchone()[0]
        agent_location = get_agent_location_map()
        location_id = agent_location[user_id]
        phone = get_db().execute(
            "select location_number from internal_phones where location_id = ?",
            (location_id, )).fetchone()[0]
        return f"+{phone}"
    except (TypeError, KeyError):
        return None


