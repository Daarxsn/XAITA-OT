import argparse, json
from pathlib import Path
from .config import load_config
from .pipeline.demo import make_demo_csv, demo_events
from .pipeline.engine import XAITAEngine
from .cti.generator import write_json

def main():
    p=argparse.ArgumentParser(prog='xaita')
    sub=p.add_subparsers(dest='cmd',required=True)
    d=sub.add_parser('demo'); d.add_argument('--out',default='artifacts/demo_cti.json')
    s=sub.add_parser('synthetic-data'); s.add_argument('--out',default='data/demo/swat_like.csv'); s.add_argument('--rows',type=int,default=3000)
    args=p.parse_args(); cfg=load_config(); engine=XAITAEngine(cfg)
    if args.cmd=='synthetic-data': print(make_demo_csv(args.out,args.rows,cfg.seed))
    elif args.cmd=='demo':
        result=engine.analyze_events(demo_events()); write_json(result,args.out); print(args.out)
