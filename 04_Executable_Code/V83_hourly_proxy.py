#!/usr/bin/env python3
"""RTS-GMLC 2020 source-based DC ED with ramp and *static* reserve headroom proxy.

Scope: continuous economic dispatch, not UC, not full seven-product response-time reserve cooptimization.
Paired counterfactuals are solved with identical parameters, loads, network and initial states.
Proof obligations are checked from primal trajectories and saved as results.
"""
import argparse, csv, json, io, zipfile, time, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import linprog

SOURCE=str(Path(__file__).resolve().parent.parent/'05_Source_Inputs'/'V77_RTS_SELECTED_UPLOAD.zip')
CARBON_PRICES=[0,25,75,200]

def read(z,k):return pd.read_csv(io.BytesIO(z.read(k)))

def prepare_all(zip_path):
 z=zipfile.ZipFile(zip_path)
 pre='RTS_Data/timeseries_data_files/'
 g=read(z,'RTS_Data/SourceData/gen.csv');bus=read(z,'RTS_Data/SourceData/bus.csv');br=read(z,'RTS_Data/SourceData/branch.csv');reserves=read(z,'RTS_Data/SourceData/reserves.csv')
 ld=read(z,pre+'Load/DAY_AHEAD_regional_Load.csv')
 arrays={k:read(z,pre+path) for k,path in {'wind':'WIND/DAY_AHEAD_wind.csv','pv':'PV/DAY_AHEAD_pv.csv','rtpv':'RTPV/DAY_AHEAD_rtpv.csv','hydro':'Hydro/DAY_AHEAD_hydro.csv'}.items()}
 nT=len(ld); assert nT==8784
 buses=bus['Bus ID'].astype(int).tolist();bid={k:i for i,k in enumerate(buses)};N=len(bus);K=len(br)
 assert N==73 and K==120 and len(g)==158 and buses[0]==101
 fix=np.zeros((nT,N))
 lookup=g.set_index('GEN UID')
 for k in ['rtpv','hydro']:
  for uid in arrays[k].columns[4:]:
   fix[:,bid[int(lookup.loc[uid]['Bus ID'])]] += arrays[k][uid].to_numpy(float)
 load=np.zeros((nT,N))
 for area in (1,2,3):
  ix=np.flatnonzero(bus['Area'].to_numpy()==area)
  load[:,ix]=ld[str(area)].to_numpy(float)[:,None]* (bus['MW Load'].to_numpy(float)[ix]/bus['MW Load'].to_numpy(float)[ix].sum())[None,:]
 cand=g[g['Fuel'].isin(['NG','Coal','Oil','Nuclear','Wind','Solar']) & (~g['Category'].isin(['Solar RTPV','CSP']))].copy().reset_index(drop=True)
 G=len(cand);pm=np.zeros((nT,G));cost=np.zeros(G);ef=np.zeros(G);efCH4=np.zeros(G);efN2O=np.zeros(G)
 genbus=np.zeros(G,dtype=int); thermal=[]; elig=[];regions=[]
 for j,row in cand.iterrows():
  uid=row['GEN UID']; genbus[j]=bid[int(row['Bus ID'])]; regions.append(int(bus.iloc[genbus[j]]['Area']))
  if row['Fuel'] in ('Wind','Solar'):
   pm[:,j]=arrays['wind' if row['Fuel']=='Wind' else 'pv'][uid].to_numpy(float)
  else:
   pm[:,j]=float(row['PMax MW'])
   hr=float(row['HR_avg_0'])/1000
   cost[j]=hr*float(row['Fuel Price $/MMBTU'])+float(row['VOM'])
   ef[j]=hr*float(row['Emissions CO2 Lbs/MMBTU'])*0.45359237/1000
   efCH4[j]=hr*float(row['Emissions CH4 Lbs/MMBTU'])*0.45359237/1000
   efN2O[j]=hr*float(row['Emissions N2O Lbs/MMBTU'])*0.45359237/1000
  if row['Fuel'] in ('NG','Coal','Oil'):
   thermal.append(j)
  if row['Category'] in ['Gas CT','Gas CC','Oil CT','Oil ST','Coal','Solar PV','Wind','CSP']:
   elig.append(j)
 ramp=np.array([max(0,float(x))*60 for x in cand['Ramp Rate MW/Min'].fillna(0)],float)
 resval={r['Reserve Product']:float(r['Requirement (MW)']) for _,r in reserves.iterrows()}
 assert (reserves['Reserve Product'].nunique()==7)
 frombus=np.array([bid[int(x)] for x in br['From Bus']],dtype=int)
 tobus=np.array([bid[int(x)] for x in br['To Bus']],dtype=int)
 stamps=ld[['Year','Month','Day','Period']].to_numpy(int)
 return dict(T=nT,G=G,N=N,K=K,gen=cand,bus=bus,br=br,load=load,fixed=fix,pmax=pm,cost=cost,ef=ef,efCH4=efCH4,efN2O=efN2O,genbus=genbus,frombus=frombus,tobus=tobus,x=br['X'].to_numpy(float),limits=br['Cont Rating'].to_numpy(float),thermal=np.array(thermal,dtype=int),eligible=np.array(elig,dtype=int),region=np.array(regions,dtype=int),ramp=ramp,reserves=resval,stamps=stamps,source_zip_sha256=hashlib.sha256(Path(zip_path).read_bytes()).hexdigest())

def solve(m,start,hours,price,bess,initial_soc=20.0,prev_thermal=None,terminal_soc=20.0,static_reserves=True,ramp=True,timeout=180):
 t0=time.monotonic();N,K,G=m['N'],m['K'],m['G'];T=min(hours,m['T']-start)
 E=m['eligible'];R=len(E);L=m['load'][start:start+T];fixed=m['fixed'][start:start+T];pmax=m['pmax'][start:start+T]
 # segment p,flow,angle,ch,dis,soc,load-shed,rup,rdn
 f=G;ang=f+K;ch=ang+N-1;dis=ch+1;soc=dis+1;shed=soc+1;rup=shed+N;rdn=rup+R;B=rdn+R
 def v(t,j): return B*t+j
 idx=lambda j: np.arange(T)*B+j
 nvars=B*T;obj=np.zeros(nvars);lo=np.full(nvars,-np.inf);hi=np.full(nvars,np.inf)
 eta=np.sqrt(.85)
 for t in range(T):
  s=v(t,0); obj[s:s+G]=m['cost']+price*m['ef'];lo[s:s+G]=0;hi[s:s+G]=pmax[t]
  lo[v(t,f):v(t,f+K)]=-m['limits'];hi[v(t,f):v(t,f+K)]=m['limits']
  lo[v(t,ch):v(t,dis+1)]=0;hi[v(t,ch):v(t,dis+1)]=10 if bess else 0
  lo[v(t,soc)]=8 if bess else 20;hi[v(t,soc)]=40 if bess else 20
  lo[v(t,shed):v(t,shed+N)]=0;obj[v(t,shed):v(t,shed+N)]=1e6
  lo[v(t,rup):v(t,rdn+R)]=0
  if not static_reserves:hi[v(t,rup):v(t,rdn+R)]=0
 eqrows=[];eqcols=[];eqdat=[];rhs=np.zeros(T*(N+K+1)+1)
 def add(r,c,val):eqrows.append(r);eqcols.append(c);eqdat.append(val)
 for t in range(T):
  row=t*(N+K+1);rhs[row:row+N]=L[t]-fixed[t]
  for g in range(G):add(row+int(m['genbus'][g]),v(t,g),1)
  for l in range(K):
   a=int(m['frombus'][l]);b=int(m['tobus'][l]);add(row+a,v(t,f+l),-1);add(row+b,v(t,f+l),1)
   r=row+N+l;x=100/m['x'][l];add(r,v(t,f+l),1)
   if a: add(r,v(t,ang+a-1),-x)
   if b: add(r,v(t,ang+b-1),x)
  add(row,v(t,dis),1);add(row,v(t,ch),-1)
  for j in range(N):add(row+j,v(t,shed+j),1)
  r=row+N+K;add(r,v(t,soc),1);add(r,v(t,ch),-eta);add(r,v(t,dis),1/eta)
  if t:add(r,v(t-1,soc),-1)
  else:rhs[r]=initial_soc
 add(len(rhs)-1,v(T-1,soc),1);rhs[-1]=terminal_soc
 eq=sparse.coo_matrix((eqdat,(eqrows,eqcols)),shape=(len(rhs),nvars)).tocsr()
 # inequalities for capacity headroom and thermal ramp. No reserves time response or UC.
 irow=[];icol=[];idat=[];bup=[]
 def row_ineq(items,b):
  i=len(bup);bup.append(b)
  for col,val in items:irow.append(i);icol.append(col);idat.append(val)
 if static_reserves:
  for t in range(T):
   for j,g in enumerate(E):
    row_ineq([(v(t,int(g)),1),(v(t,rup+j),1)],float(pmax[t,g]))
    row_ineq([(v(t,int(g)),-1),(v(t,rdn+j),1)],0)
   req=m.get('hourly_reserves')
   up_req=sum(float(req.iloc[start+t][k]) if req is not None else m['reserves'][k] for k in ['Spin_Up_R1','Spin_Up_R2','Spin_Up_R3','Flex_Up','Reg_Up'])
   dn_req=sum(float(req.iloc[start+t][k]) if req is not None else m['reserves'][k] for k in ['Flex_Down','Reg_Down'])
   row_ineq([(v(t,rup+j),-1) for j in range(R)],-up_req)
   row_ineq([(v(t,rdn+j),-1) for j in range(R)],-dn_req)
   for region in (1,2,3):
    k=f'Spin_Up_R{region}';row_ineq([(v(t,rup+j),-1) for j,g in enumerate(E) if m['region'][g]==region],-(float(req.iloc[start+t][k]) if req is not None else m['reserves'][k]))
 if ramp:
  for t in range(T):
   for g in m['thermal']:
    r=float(m['ramp'][g]);
    if t:
     row_ineq([(v(t,int(g)),1),(v(t-1,int(g)),-1)],r)
     row_ineq([(v(t,int(g)),-1),(v(t-1,int(g)),1)],r)
    elif prev_thermal is not None:
     prev=float(prev_thermal[int(g)]);row_ineq([(v(t,int(g)),1)],prev+r);row_ineq([(v(t,int(g)),-1)],r-prev)
 ub=sparse.coo_matrix((idat,(irow,icol)),shape=(len(bup),nvars)).tocsr() if bup else None
 try:res=linprog(obj,A_eq=eq,b_eq=rhs,A_ub=ub,b_ub=bup if bup else None,bounds=list(zip(lo,hi)),method='highs',options={'time_limit':timeout,'primal_feasibility_tolerance':1e-7,'dual_feasibility_tolerance':1e-7})
 except Exception as e:return {'success':False,'error':str(e),'start':start,'T':T,'price':price,'bess':bess},None,None
 meta=dict(success=bool(res.success),status=int(res.status),message=str(res.message),start=start,hours=T,price=price,bess=bool(bess),wall_s=round(time.monotonic()-t0,3),variables=nvars,equalities=eq.shape[0],inequalities=len(bup))
 if not res.success:return meta,None,None
 a=res.x.reshape(T,B);gen=a[:,:G];co=gen@m['cost'];eCO2=gen@m['ef'];eCH4=gen@m['efCH4'];eN2O=gen@m['efN2O'];flow=a[:,f:f+K];S=a[:,soc];shedtot=a[:,shed:shed+N].sum(1)
 maxeq=float(np.max(abs(eq@res.x-rhs)));maxub=float(np.max(ub@res.x-np.array(bup))) if bup else 0
 # independently evaluated reserve headroom by product and region
 ru=a[:,rup:rup+R];rd=a[:,rdn:rdn+R]
 spin={i:ru[:,m['region'][E]==i].sum(1) for i in (1,2,3)}
 dt=m['stamps'][start:start+T]
 records=[]
 for t in range(T):
  records.append(dict(hour_index=start+t,Year=int(dt[t,0]),Month=int(dt[t,1]),Day=int(dt[t,2]),Period=int(dt[t,3]),price=price,bess=int(bess),CO2_t=eCO2[t],CH4_t=eCH4[t],N2O_t=eN2O[t],GWP100_direct_t=eCO2[t]+27*eCH4[t]+273*eN2O[t],fuel_cost_USD=co[t],charge_MW=a[t,ch],discharge_MW=a[t,dis],SOC_MWh=S[t],load_shed_MW=shedtot[t],max_line_ratio=float(np.max(abs(flow[t])/m['limits'])),reserve_up_MW=ru[t].sum(),reserve_down_MW=rd[t].sum(),spin_R1_MW=spin[1][t],spin_R2_MW=spin[2][t],spin_R3_MW=spin[3][t]))
 meta.update(objective_USD=float(res.fun),CO2_t=float(eCO2.sum()),CH4_t=float(eCH4.sum()),N2O_t=float(eN2O.sum()),direct_GWP100_t=float((eCO2+27*eCH4+273*eN2O).sum()),fuel_cost_USD=float(co.sum()),shed_MWh=float(shedtot.sum()),max_eq_residual=maxeq,max_ub_violation=maxub,SOC_end_MWh=float(S[-1]),SOC_min_MWh=float(S.min()),SOC_max_MWh=float(S.max()),charge_MWh=float(a[:,ch].sum()),discharge_MWh=float(a[:,dis].sum()),max_line_ratio=float(np.max(abs(flow)/m['limits'])),simultaneous_hours=int(((a[:,ch]>1e-6)&(a[:,dis]>1e-6)).sum()),thermal_ramp_max_violation_MW=float(max([0]+[float(np.max(abs(np.diff(gen[:,m['thermal']],axis=0))-m['ramp'][m['thermal']]))] if T>1 else [0])))
 return meta,pd.DataFrame.from_records(records),gen[-1].copy()

def test_selected(zip_path,out_dir,firsts=(0,2184,4392,6576),T=168,timeout=180):
 out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
 m=prepare_all(zip_path); metas=[];allhours=[]
 for first in firsts:
  for p in CARBON_PRICES:
   for b in (False,True):
    meta,h,g=solve(m,first,T,p,b,timeout=timeout)
    metas.append(meta)
    if h is not None:allhours.append(h)
    print('CASE',first,p,b,meta['success'],meta['wall_s'],round(meta.get('CO2_t',0),3),'shedding',meta.get('shed_MWh','NA'),flush=True)
 pd.DataFrame(metas).to_csv(out/'V79_solver_summary.csv',index=False,encoding='utf-8-sig')
 if allhours:pd.concat(allhours,ignore_index=True).to_csv(out/'V79_hourly_results.csv',index=False,encoding='utf-8-sig')
 pairs=[]
 for first in firsts:
  for p in CARBON_PRICES:
   both=[r for r in metas if r['start']==first and r['price']==p and r['success']]
   if len(both)==2:
    r0=next(r for r in both if not r['bess']);r1=next(r for r in both if r['bess'])
    pairs.append(dict(start_hour=first,price=p,baseline_CO2_t=r0['CO2_t'],storage_CO2_t=r1['CO2_t'],avoided_CO2_t=r0['CO2_t']-r1['CO2_t'],avoided_direct_GWP100_t=r0['direct_GWP100_t']-r1['direct_GWP100_t'],operating_cost_savings_USD=r0['objective_USD']-r1['objective_USD'],zero_load_shed=abs(r0['shed_MWh'])<1e-7 and abs(r1['shed_MWh'])<1e-7))
 pd.DataFrame(pairs).to_csv(out/'V79_paired_effects.csv',index=False,encoding='utf-8-sig')
 (out/'V79_model_scope.json').write_text(json.dumps({'source_sha256':m['source_zip_sha256'],'scenario':'static seven-product aggregated headroom; fossil ramp; 73 bus DC energy-only ED','caveats':['No start/shutdown or unit commitment','Source reserve static requirements, not original 2020 hourly reserve trajectories','Reserve response times not enforced; only headroom','No thermal minimum stable output or segmented heat rates','Fixed hydro/rooftop PV, no reservoir process','Direct GWP100 uses 27 for fossil combustion CH4 and 273 for N2O; no upstream','Annual runs require chronological year'], 'prices':CARBON_PRICES,'sample_hour_starts':list(firsts)},ensure_ascii=False,indent=2),encoding='utf-8')
 return metas,pairs

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--zip',default=SOURCE);p.add_argument('--out',default='V79_run');p.add_argument('--firsts',default='0,2184,4392,6576');p.add_argument('--hours',type=int,default=168);p.add_argument('--timeout',type=int,default=180)
 a=p.parse_args();test_selected(a.zip,a.out,[int(x) for x in a.firsts.split(',')],a.hours,a.timeout)
