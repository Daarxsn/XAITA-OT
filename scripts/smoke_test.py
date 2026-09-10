from pathlib import Path
from xaita_ot.config import load_config
from xaita_ot.pipeline.demo import demo_events, make_demo_csv
from xaita_ot.pipeline.engine import XAITAEngine
from xaita_ot.cti.generator import write_json

cfg=load_config(); make_demo_csv('data/demo/swat_like.csv',3000,cfg.seed)
out=XAITAEngine(cfg).analyze_events(demo_events())
write_json(out,'artifacts/smoke_cti.json')
print('Smoke OK:',len(out),'incident(s) -> artifacts/smoke_cti.json')
