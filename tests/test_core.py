from datetime import datetime, timedelta, timezone
from xaita_ot.core.schemas import DetectionEvent
from xaita_ot.core.btae import reconstruct
from xaita_ot.core.attribution import assess

def events():
    t=datetime.now(timezone.utc)
    return [DetectionEvent(f'e{i}',t+timedelta(seconds=i*5),'PLC1','modbus','unauthorized_command',0.9) for i in range(4)]

def test_btae_reconstructs_episode():
    eps=reconstruct(events(),threshold=.5,temporal_window=60)
    assert len(eps)==1 and len(eps[0].events)==4

def test_attribution_interval():
    out=assess(['H1'],{'H1':{'DC':.9,'BSS':.8,'ECS':.7,'EC':.8,'MAS':.6}},{'DC':.7,'BSS':.8,'ECS':.9,'EC':.8,'MAS':.6})
    assert 0<=out[0].belief<=out[0].plausibility<=1
