from dataclasses import dataclass
import numpy as np
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score
from sklearn.ensemble import RandomForestClassifier
from .preprocess import OTPreprocessor
from ..models.trainer import Detector

@dataclass
class Split:
    train: object
    val: object
    test: object

def chronological_split(df, train=0.70, val=0.15):
    n=len(df); a=int(n*train); b=int(n*(train+val))
    return df.iloc[:a].copy(), df.iloc[a:b].copy(), df.iloc[b:].copy()

def binary_metrics(y,p):
    pred=(p>=.5).astype(int)
    pr,re,f1,_=precision_recall_fscore_support(y,pred,average='binary',zero_division=0)
    fp=((pred==1)&(y==0)).sum(); tn=((pred==0)&(y==0)).sum()
    auc=roc_auc_score(y,p) if len(np.unique(y))>1 else float('nan')
    return {'precision':float(pr),'recall':float(re),'f1':float(f1),'fpr':float(fp/max(1,fp+tn)),'auroc':float(auc)}

def expected_calibration_error(y,p,bins=10):
    y=np.asarray(y); p=np.asarray(p); edges=np.linspace(0,1,bins+1); ece=0
    for lo,hi in zip(edges[:-1],edges[1:]):
        mask=(p>=lo)&(p<(hi if hi<1 else hi+1e-9))
        if not mask.any(): continue
        ece += mask.mean()*abs(y[mask].mean()-p[mask].mean())
    return float(ece)

def train_baselines(train_wd,val_wd,test_wd,cfg):
    out={}
    # Conventional ML baseline.
    rf=RandomForestClassifier(n_estimators=120,random_state=cfg.seed,n_jobs=-1,class_weight='balanced')
    rf.fit(train_wd.X.reshape(len(train_wd.X),-1),train_wd.y)
    p=rf.predict_proba(test_wd.X.reshape(len(test_wd.X),-1))[:,1]
    out['conventional_ml']=binary_metrics(test_wd.y,p)
    # CNN-LSTM.
    det=Detector(train_wd.X.shape[-1],cfg.model)
    det.fit(train_wd.X,train_wd.y,cfg.model.epochs,cfg.model.batch_size,cfg.model.learning_rate)
    p=det.predict_proba(test_wd.X); out['cnn_lstm']=binary_metrics(test_wd.y,p)
    out['cnn_lstm']['ece']=expected_calibration_error(test_wd.y,p)
    return out
