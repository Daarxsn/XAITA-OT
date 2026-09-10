from datetime import datetime, timezone
import json


def generate_cti(incident_id, detection, episode, context, attribution, xai, risk):
    provenance = [e.event_id for e in episode.events]
    observation_ids = [e.observation_id for e in episode.events if e.observation_id]
    event_trace = [
        {
            'event_id': e.event_id,
            'observation_id': e.observation_id,
            'timestamp': e.timestamp.isoformat(),
            'asset': e.asset,
            'protocol': e.protocol,
            'source': e.source,
            'destination': e.destination,
            'label': e.label,
            'detection_confidence': e.detection_confidence,
            'attack_context': [c for c in context if c.get('event_id') == e.event_id],
        }
        for e in episode.events
    ]
    return {
      'schema_version': 'XAITA-OT-CTI-1.0',
      'incident_id': incident_id,
      'generated_at': datetime.now(timezone.utc).isoformat(),
      'detection': detection,
      'behavior': {
          'episode_id': episode.episode_id,
          'event_ids': provenance,
          'correlation_strength': episode.correlation_strength,
          'stages': episode.stages,
          'event_trace': event_trace,
          'correlation_edges': episode.correlation_edges,
      },
      'context': context,
      'attribution': attribution,
      'xai': xai,
      'risk': risk,
      'provenance': provenance,
      'provenance_links': {
          'observations': observation_ids,
          'detections': provenance,
          'episodes': [episode.episode_id],
          'attack_context': [c.get('technique_id') for c in context if c.get('technique_id')],
      },
      'human_validation_required': True,
      'autonomous_ot_action': False,
    }


def write_json(obj, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, default=str)
