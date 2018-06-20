import copy
import json

from opentaxi import iot, geo, validate


validator = validate.get_validator('./schemas/ot_location_broadcast.json')


def handler(event, context):
    if not validate.is_valid_message(validator, event):
        return {} # Discard event

    client = iot.get_client()

    # Send search topics to driver
    search_range_meters = event['range_meters']
    search_levels = [12, 16]
    search_max_cells = 20
    search_cellids = geo.get_cellids_in_range(
        event['lat_lng'][0],
        event['lat_lng'][1],
        search_range_meters,
        search_levels[0], search_levels[1],
        search_max_cells,
        2
    )
    search_topics = []
    for cellid in search_cellids:
        tokens = geo.get_hierarchy_as_tokens(cellid, placeholder=None)
        subtopics = '/'.join(map(str, tokens))
        wildcard = '/#' if len(tokens) < 4 else ''
        search_topics.append(f'ot/riders/searching/{subtopics}{wildcard}')
    search_topics.sort(key=len)

    reply_topic = event['reply_topic']
    reply_message = {
        'type': 'riders_in_range',
        'device_time': event['device_time'],
        'range_meters': search_range_meters,
        'lat_lng': event['lat_lng'],
        'topics': search_topics
    }
    client.publish(reply_topic, json.dumps(reply_message), 1)

    # Broadcast to one cell
    # FUTURE: multiple cells along predicted line of travel
    broadcast_cellid = geo.get_cellid_at_level(
        event['lat_lng'][0],
        event['lat_lng'][1],
        16
    )
    broadcast_message = copy.deepcopy(event)
    del broadcast_message['auth_client_id']
    del broadcast_message['range_meters']
    broadcast_tokens = geo.get_hierarchy_as_tokens(broadcast_cellid)
    broadcast_subtopics = '/'.join(map(str, broadcast_tokens))
    broadcast_topic = f'ot/drivers/available/{broadcast_subtopics}'
    client.publish(broadcast_topic, json.dumps(broadcast_message), 1)

    return {}
