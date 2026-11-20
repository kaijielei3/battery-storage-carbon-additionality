#!/usr/bin/env python3
"""2020 RTS-GMLC source-based 7-product hourly reserve DC ED sensitivity.

Independent generator-product reserve allocations with shared up/down headroom,
regional spin eligibility, and source response-time/ramp deliverability.
Continuous economic dispatch only: NOT UC, deliverability in the network under
contingencies, or a tested storage reserve product. Battery is energy only.
"""
import io, zipfile, json, argparse, hashlib, time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import linprog
from importlib.machinery import SourceFileLoader
HERE=Path(__file__).resolve().parent
BASE=SourceFileLoader('v83base',str(HERE/'V83_hourly_proxy.py')).load_module()
PRODS=['Spin_Up_R1','Spin_Up_R2','Spin_Up_R3','Flex_Up','Flex_Down','Reg_Up','Reg_Down']
UP=np.array([0,1,2,3,5]); DOWN=np.array([4,6]);RTOL=3e-5

def load_model(source,reserve):
 m=BASE.prepare_all(source)
 with zipfile.ZipFile(reserve) as z: d=pd.read_csv(io.BytesIO(z.read('V82_RTS_RESERVE_HOURLY.csv')))
 assert len(d)==8784 and np.array_equal(d[['Year','Month','Day','Period']].to_numpy(dtype=int),m['stamps'])
 if d[PRODS].isna().any().any() or (d[PRODS]<0).any().any():raise ValueError('Invalid reserve demand')
 m['hourly_reserves']=d
 with zipfile.ZipFile(source) as z:
  metadata=pd.read_csv(io.BytesIO(z.read('RTS_Data/SourceData/reserves.csv')))
 m['reserve_parameters']=metadata.set_index('Reserve Product').loc[PRODS]
 return m

def solve(m,start,hours,price,bess,timeout=100,initial_soc=20.,terminal_soc=20.,prev_generation=None):
 nT=m['T'];T=min(hours,nT-start);N=m['N'];K=m['K'];G=m['G'];E=m['eligible'];R=len(E);Q=len(PRODS)
 L=m['load'][start:start+T];fix=m['fixed'][start:start+T];pm=m['pmax'][start:start+T]
 # [gen G, line K, voltage N-1, charge, discharge, SOC, shed N, reserve R*Q]
 f=G;angle=f+K;charge=angle+N-1;dis=charge+1;soc=dis+1;shed=soc+1;rr=shed+N;B=rr+R*Q
 vi=lambda t,k:B*t+k
 n=B*T;obj=np.zeros(n);lo=np.full(n,-np.inf);hi=np.full(n,np.inf)
 eta=np.sqrt(.85);tmp=m['reserve_parameters'];region=m['region'][E];categories=m['gen'].iloc[E]['Category'].to_numpy()
 eligible_mask=np.zeros((R,Q),bool);lim=np.zeros((R,Q))
 for j in range(R):
  for q,key in enumerate(PRODS):
   trow=tmp.loc[key]
   regions=str(trow['Eligible Regions'])
   allowed={1,2,3} if '(' in regions else {int(regions)}
   eligible_mask[j,q] = region[j] in allowed and categories[j] in str(trow['Eligible Device SubCategories'])
   lim[j,q] = max(0.,m['ramp'][E[j]])*float(trow['Timeframe (sec)'])/60.
 for t in range(T):
  beg=vi(t,0);lo[beg:beg+G]=0;hi[beg:beg+G]=pm[t];obj[beg:beg+G]=m['cost']+price*m['ef']
  lo[vi(t,f):vi(t,f+K)]=-m['limits'];hi[vi(t,f):vi(t,f+K)]=m['limits']
  lo[vi(t,charge):vi(t,dis+1)]=0;hi[vi(t,charge):vi(t,dis+1)]=10 if bess else 0
  lo[vi(t,soc)]=8 if bess else 20;hi[vi(t,soc)]=40 if bess else 20
  lo[vi(t,shed):vi(t,shed+N)]=0;obj[vi(t,shed):vi(t,shed+N)]=1e6
  for j in range(R):
   for q in range(Q):
    ix=vi(t,rr+j*Q+q);lo[ix]=0;hi[ix]=min(pm[t,E[j]],lim[j,q]) if eligible_mask[j,q] else 0
 eqr=[];eqc=[];eqd=[];rhs=np.zeros(T*(N+K+1)+1)
 def ae(i,j,v):eqr.append(i);eqc.append(j);eqd.append(v)
 for t in range(T):
  off=t*(N+K+1);rhs[off:off+N]=L[t]-fix[t]
  for j in range(G):ae(off+int(m['genbus'][j]),vi(t,j),1.)
  for k in range(K):
   a=int(m['frombus'][k]);b=int(m['tobus'][k]);ae(off+a,vi(t,f+k),-1.);ae(off+b,vi(t,f+k),1.)
   x=100./m['x'][k];row=off+N+k;ae(row,vi(t,f+k),1.)
   if a:ae(row,vi(t,angle+a-1),-x)
   if b:ae(row,vi(t,angle+b-1),x)
  ae(off,vi(t,dis),1.);ae(off,vi(t,charge),-1.)
  for b in range(N):ae(off+b,vi(t,shed+b),1.)
  sr=off+N+K;ae(sr,vi(t,soc),1.);ae(sr,vi(t,charge),-eta);ae(sr,vi(t,dis),1/eta)
  if t:ae(sr,vi(t-1,soc),-1.)
  else:rhs[sr]=initial_soc
 ae(len(rhs)-1,vi(T-1,soc),1.);rhs[-1]=terminal_soc
 Aeq=sparse.coo_matrix((eqd,(eqr,eqc)),shape=(len(rhs),n)).tocsr()
 ur=[];uc=[];ud=[];bv=[]
 def le(terms,b):
  r=len(bv);bv.append(float(b))
  for i,v in terms:ur.append(r);uc.append(i);ud.append(v)
 for t in range(T):
  req=m['hourly_reserves'].iloc[start+t]
  # each reserve service separately meets its source regional/national requirement
  for q,key in enumerate(PRODS):
   le([(vi(t,rr+j*Q+q),-1.) for j in range(R) if eligible_mask[j,q]],-float(req[key]))
  # reserve up and down products compete for same feasible headroom in each direction
  for j,g in enumerate(E):
   le([(vi(t,int(g)),1.)]+[(vi(t,rr+j*Q+int(q)),1.) for q in UP],pm[t,g])
   le([(vi(t,int(g)),-1.)]+[(vi(t,rr+j*Q+int(q)),1.) for q in DOWN],0.)
  for g in m['thermal']:
   ramp=float(m['ramp'][g]);assert ramp>=0.
   if t:
    le([(vi(t,int(g)),1.),(vi(t-1,int(g)),-1.)],ramp)
    le([(vi(t,int(g)),-1.),(vi(t-1,int(g)),1.)],ramp)
   elif prev_generation is not None:
    prev=float(prev_generation[int(g)])
    le([(vi(t,int(g)),1.)],prev+ramp)
    le([(vi(t,int(g)),-1.)],ramp-prev)
 Aub=sparse.coo_matrix((ud,(ur,uc)),shape=(len(bv),n)).tocsr()
 began=time.monotonic()
 res=linprog(obj,A_eq=Aeq,b_eq=rhs,A_ub=Aub,b_ub=np.array(bv),bounds=list(zip(lo,hi)),method='highs',options={'time_limit':timeout,'primal_feasibility_tolerance':1e-7,'dual_feasibility_tolerance':1e-7})
 meta=dict(start_hour=start,hours=T,price=price,bess=int(bess),success=bool(res.success),status=int(res.status),message=str(res.message),seconds=round(time.monotonic()-began,3),nvariables=n,neq=Aeq.shape[0],nineq=Aub.shape[0],reserve_model='product_specific_shared_headroom_ramp_response')
 if not res.success:return meta,None,None
 a=res.x.reshape(T,B);gen=a[:,:G];P=a[:,rr:rr+R*Q].reshape(T,R,Q)
 e=gen@m['ef'];eqr0=np.abs(Aeq@res.x-rhs).max();ubr0=(Aub@res.x-np.array(bv)).max()
 per=[];reserve_short=0.
 for t in range(T):
  row=dict(start_hour=start,hour_index=start+t,Year=int(m['stamps'][start+t,0]),Month=int(m['stamps'][start+t,1]),Day=int(m['stamps'][start+t,2]),Period=int(m['stamps'][start+t,3]),price=price,bess=int(bess),CO2_t=float(e[t]),direct_GWP100_t=float(e[t]+27*(gen[t]@m['efCH4'])+273*(gen[t]@m['efN2O'])),fuel_cost_USD=float(gen[t]@m['cost']),charge_MW=float(a[t,charge]),discharge_MW=float(a[t,dis]),SOC_MWh=float(a[t,soc]),load_shed_MW=float(np.sum(a[t,shed:shed+N])),max_line_ratio=float(np.max(np.abs(a[t,f:f+K])/m['limits'])))
  for q,key in enumerate(PRODS):
   row[key+'_provided_MW']=float(P[t,:,q].sum());row[key+'_required_MW']=float(m['hourly_reserves'].iloc[start+t][key])
  per.append(row)
 meta.update(CO2_t=float(e.sum()),direct_GWP100_t=float(np.sum(gen@m['ef']+27*(gen@m['efCH4'])+273*(gen@m['efN2O']))),objective_USD=float(res.fun),fuel_cost_USD=float(np.sum(gen@m['cost'])),load_shed_MWh=float(a[:,shed:shed+N].sum()),soc_start=initial_soc,soc_end=float(a[-1,soc]),max_eq_residual=float(eqr0),max_ineq_violation=float(ubr0),max_line_ratio=float(np.max(np.abs(a[:,f:f+K])/m['limits'])),min_product_surplus_MW=float(min(np.min(P[:,:,q].sum(axis=1)-m['hourly_reserves'][key].to_numpy(float)[start:start+T]) for q,key in enumerate(PRODS))),simultaneous_battery_hours=int(np.sum((a[:,charge]>1e-6)&(a[:,dis]>1e-6))))
 assert meta['max_eq_residual']<RTOL and meta['max_ineq_violation']<RTOL and meta['min_product_surplus_MW']>-RTOL
 return meta,pd.DataFrame(per),gen[-1]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',default=str(HERE.parent/'05_Source_Inputs'/'V77_RTS_SELECTED_UPLOAD.zip'));ap.add_argument('--reserves',default=str(HERE.parent/'05_Source_Inputs'/'V82_RTS_RESERVES_UPLOAD.zip'));ap.add_argument('--out',default=str(HERE.parent/'RECOMPUTED_seasonal'));ap.add_argument('--starts',default='0,2184,4392,6576');ap.add_argument('--hours',type=int,default=24);ap.add_argument('--prices',default='0,25');ap.add_argument('--timeout',type=int,default=90)
 opt=ap.parse_args();out=Path(opt.out);out.mkdir(parents=True,exist_ok=True)
 m=load_model(opt.source,opt.reserves);audits=[];hours=[]
 for start in map(int,opt.starts.split(',')):
  for price in map(int,opt.prices.split(',')):
   for bess in (0,1):
    meta,h,_=solve(m,start,opt.hours,price,bess,timeout=opt.timeout)
    audits.append(meta)
    if h is not None:hours.append(h)
    pd.DataFrame(audits).to_csv(out/'V84_solver_log.csv',index=False,encoding='utf-8-sig')
    if h is not None:h.to_csv(out/f'V84_hour_{start:05d}_p{price:03d}_b{bess}.csv',index=False)
    print('V84',start,price,bess,meta['success'],meta.get('CO2_t'),meta['seconds'],meta['message'][:100],flush=True)
 if hours:pd.concat(hours).to_csv(out/'V84_hourly_all.csv',index=False,encoding='utf-8-sig')
 rows=[]
 for start in map(int,opt.starts.split(',')):
  for price in map(int,opt.prices.split(',')):
   pair=[x for x in audits if x['start_hour']==start and x['price']==price and x['success']]
   if len(pair)==2:
    a=next(x for x in pair if x['bess']==0);b=next(x for x in pair if x['bess']==1)
    rows.append(dict(start_hour=start,hours=opt.hours,price=price,baseline_CO2_t=a['CO2_t'],storage_CO2_t=b['CO2_t'],avoided_CO2_t=a['CO2_t']-b['CO2_t'],avoided_direct_GWP100_t=a['direct_GWP100_t']-b['direct_GWP100_t'],objective_saving_USD=a['objective_USD']-b['objective_USD'],both_zero_shedding=a['load_shed_MWh']<1e-6 and b['load_shed_MWh']<1e-6,both_optimal=True))
 pd.DataFrame(rows).to_csv(out/'V84_pairs.csv',index=False,encoding='utf-8-sig')
 (out/'V84_scope.json').write_text(json.dumps(dict(assumptions=['seven separate reserve products, source response-time ramp bounds, generator category/region qualification, shared up and down headroom','source hydro and rooftop PV fixed; DC power flows, 85 percent BESS efficiency, SOC starts and ends 20 MWh','thermal ramp and continuous ED, without binary UC, minimum output, startup or hydro reservoir balance','energy-only battery: not counted toward reserve capacity','no network contingency deliverability or stochastic reserve activation','source Emissions CO2 numeric fields used with source HR_avg_0, CH4 AR6 fossil 27, N2O 273 for illustrative direct combustion GWP100'],official_rts_sha256=hashlib.sha256(Path(opt.source).read_bytes()).hexdigest(),reserve_sha256=hashlib.sha256(Path(opt.reserves).read_bytes()).hexdigest()),indent=2),encoding='utf8')
 print('PAIRS',len(rows))
if __name__=='__main__':main()
