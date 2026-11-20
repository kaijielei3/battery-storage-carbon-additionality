#!/usr/bin/env python3
"""Restartable chronological annual paired LP with seven source hourly reserve products.
One 168-hour implemented window at a time; terminal SOC=20 in every window.
All outputs are implementation results of this fixed-window policy, NOT a globally
optimal full-horizon LP and not a thermal UC. Unfinished runs never make an annual claim.
"""
from pathlib import Path
import json, argparse, hashlib, datetime, time
import numpy as np,pandas as pd
from V84_seven_product_ED import load_model,solve

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--source',default=str(Path(__file__).resolve().parent.parent/'05_Source_Inputs'/'V77_RTS_SELECTED_UPLOAD.zip'))
 ap.add_argument('--reserves',default=str(Path(__file__).resolve().parent.parent/'05_Source_Inputs'/'V82_RTS_RESERVES_UPLOAD.zip'))
 ap.add_argument('--out',default=str(Path(__file__).resolve().parent.parent/'RECOMPUTED_annual'))
 ap.add_argument('--prices',default='0,25')
 ap.add_argument('--max-windows',type=int,default=53,help='Maximum consecutive windows to compute per arm from the beginning, safe to rerun')
 ap.add_argument('--timeout',type=int,default=120)
 a=ap.parse_args();o=Path(a.out);o.mkdir(parents=True,exist_ok=True)
 model=load_model(a.source,a.reserves)
 source_sha=hashlib.sha256(Path(a.source).read_bytes()).hexdigest();reserve_sha=hashlib.sha256(Path(a.reserves).read_bytes()).hexdigest()
 prices=[int(x) for x in a.prices.split(',')]
 nwin=(8784+167)//168
 for price in prices:
  for b in (0,1):
   directory=o/f'p{price:03d}_b{b}';directory.mkdir(exist_ok=True)
   prev=None;last_end=0
   for i,start in enumerate(range(0,8784,168)):
    if i>=a.max_windows:break
    H=min(168,8784-start);stem=f'h{start:05d}'
    meta_f=directory/(stem+'.json');hour_f=directory/(stem+'.csv');state_f=directory/(stem+'.npz')
    if meta_f.exists() and hour_f.exists() and state_f.exists():
     prevstate=np.load(state_f)['generator'];meta=json.loads(meta_f.read_text())
     valid=(bool(meta.get('success')) and meta.get('start_hour')==start and meta.get('hours')==H and meta.get('source_sha256')==source_sha and meta.get('reserve_sha256')==reserve_sha and meta.get('prev_state_sha256')==hashlib.sha256(np.asarray(prev if prev is not None else [],dtype=float).tobytes()).hexdigest())
     if valid:
      d=pd.read_csv(hour_f)
      if len(d)==H and d.hour_index.iloc[0]==start and abs(float(d.CO2_t.sum())-meta['CO2_t'])<1e-5:
       prev=prevstate;last_end=start+H;print('REUSED',price,b,start,flush=True);continue
    meta,df,lastgen=solve(model,start,H,price,b,timeout=a.timeout,prev_generation=prev)
    meta.update(source_sha256=source_sha,reserve_sha256=reserve_sha,prev_state_sha256=hashlib.sha256(np.asarray(prev if prev is not None else [],dtype=float).tobytes()).hexdigest(),fixed_terminal_soc_MWh=20)
    meta_f.write_text(json.dumps(meta,indent=2),encoding='utf-8')
    if not meta['success']:
     print('STOP_FAILED',price,b,start,meta['message'],flush=True);break
    df.to_csv(hour_f,index=False);np.savez_compressed(state_f,generator=lastgen)
    prev=lastgen;last_end=start+H;print('SOLVED',price,b,'end',last_end,'co2',round(meta['CO2_t'],3),'sec',meta['seconds'],flush=True)
   print('ARM_STATUS',price,b,'completed',last_end,'of 8784',flush=True)
   files=sorted(directory.glob('h*.csv'))
   runs=[];hourly=[]
   for f in files:
    jf=f.with_suffix('.json')
    if not jf.exists():continue
    v=json.loads(jf.read_text());h=pd.read_csv(f)
    if v.get('success') and h.hour_index.iloc[0]==v['start_hour']:
     runs.append(v);hourly.append(h)
   if runs and len(hourly)>0:
    pd.DataFrame(runs).to_csv(o/f'V84_p{price:03d}_b{b}_windows.csv',index=False)
    x=pd.concat(hourly,ignore_index=True).sort_values('hour_index')
    if len(x)==int(x.hour_index.nunique()) and x.hour_index.iloc[0]==0 and (x.hour_index.to_numpy()==np.arange(len(x))).all():
     x.to_csv(o/f'V84_p{price:03d}_b{b}_chronological.csv',index=False)
     (o/f'V84_p{price:03d}_b{b}_status.json').write_text(json.dumps({'hours_completed':len(x),'required_hours':8784,'complete':len(x)==8784,'CO2_partial_t':float(x.CO2_t.sum()),'direct_GWP100_partial_t':float(x.direct_GWP100_t.sum()),'nwindows':len(runs),'model':'seven-product DC ED with ramp and 168h end SOC; not UC','source_sha256':source_sha,'reserve_sha256':reserve_sha},indent=2),encoding='utf8')
  # only construct a true annual pair after BOTH complete
  p0=o/f'V84_p{price:03d}_b0_status.json';p1=o/f'V84_p{price:03d}_b1_status.json'
  if p0.exists() and p1.exists():
   x=json.loads(p0.read_text());y=json.loads(p1.read_text())
   if x['complete'] and y['complete']:
    pd.DataFrame([{'price':price,'hours':8784,'avoided_CO2_t':x['CO2_partial_t']-y['CO2_partial_t'],'avoided_direct_GWP100_t':x['direct_GWP100_partial_t']-y['direct_GWP100_partial_t'],'interpretation':'chronological 168h dispatch policy'}]).to_csv(o/f'V84_ANNUAL_PAIR_p{price:03d}.csv',index=False)
if __name__=='__main__':main()
