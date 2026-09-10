import argparse,json
from pathlib import Path
from xaita_ot.cti.stix import to_stix_bundle
p=argparse.ArgumentParser(); p.add_argument('--cti',required=True); p.add_argument('--out',default='artifacts/cti_bundle.json'); a=p.parse_args()
obj=json.loads(Path(a.cti).read_text()); obj=obj[0] if isinstance(obj,list) else obj
Path(a.out).write_text(json.dumps(to_stix_bundle(obj),indent=2)); print(a.out)
