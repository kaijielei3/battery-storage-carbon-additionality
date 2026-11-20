#!/usr/bin/env python3
"""Regenerate publication graphics exclusively from archived numeric results.
Run: python 04_Executable_Code/plot_from_archive.py --root . --out 08_Audit/Plots_Rerun
"""
from pathlib import Path
import argparse
import pandas as pd,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('--root',default=str(Path(__file__).resolve().parent.parent));p.add_argument('--out',default='')
a=p.parse_args();root=Path(a.root).resolve();out=Path(a.out).resolve() if a.out else root/'08_Audit'/'Plots_Rerun';out.mkdir(parents=True,exist_ok=True)
annual=pd.read_csv(root/'06_Results'/'Annual_Overview'/'V84_Annual_Main_Results.csv')
monthly=pd.read_csv(root/'06_Results'/'Annual_Overview'/'V84_Monthly_Results.csv')
season=pd.read_csv(root/'07_Seasonal_Results'/'Seasonal_Overview'/'V84_Seasonal_Seven_Product_Pairs.csv')
plt.rcParams.update({'font.family':'DejaVu Serif','font.size':10,'axes.labelsize':11,'axes.linewidth':.8,'savefig.dpi':210})
fig,ax=plt.subplots(figsize=(6.8,3.25));v=[float(annual.set_index('price').loc[i,'avoided_CO2_t']) for i in (0,25)]
ax.bar([0,1],v,color=['#9a9a9a','#292929'],edgecolor='#222',width=.44,linewidth=.5)
ax.axhline(0,color='#444',linewidth=.75);ax.set_xticks([0,1],['USD 0/t CO$_2$','USD 25/t CO$_2$']);ax.set_ylabel('Annual avoided combustion CO$_2$ (t)')
for i,x in enumerate(v):ax.text(i,x+(110 if x>=0 else -150),f'{x:+,.1f}',ha='center',va='bottom' if x>0 else 'top')
ax.set_ylim(-1600,5150);ax.spines[['top','right']].set_visible(False);fig.tight_layout();fig.savefig(out/'figure1_annual.png',bbox_inches='tight');plt.close(fig)
fig,ax=plt.subplots(figsize=(7.7,3.5))
for p,c,s in [(0,'#888888','o'),(25,'#222222','s')]:
 x=monthly[monthly.price==p].sort_values('Month');ax.plot(x.Month,x.avoided_CO2_t,marker=s,color=c,linewidth=1.5,markersize=4,label=f'USD {p}/t')
ax.axhline(0,color='#444',linewidth=.8);ax.set_xticks(range(1,13));ax.set_xlabel('Month of 2020');ax.set_ylabel('Avoided combustion CO$_2$ (t per month)');ax.legend(frameon=False,ncol=2);ax.spines[['top','right']].set_visible(False);fig.tight_layout();fig.savefig(out/'figure2_monthly.png',bbox_inches='tight');plt.close(fig)
fig,ax=plt.subplots(figsize=(7.5,3.7));xx=np.arange(4);seasons=['January','April','July','October']
for i,(p,c) in enumerate(zip((0,25,75,200),['#bbbbbb','#888888','#555555','#171717'])):
 d=season[season.price==p].set_index('season_label');v=[d.loc[k,'avoided_CO2_t'] for k in seasons]
 ax.bar(xx+(i-1.5)*.19,v,width=.185,color=c,edgecolor='#222',linewidth=.2,label=f'USD {p}/t')
ax.set_xticks(xx,seasons);ax.axhline(0,color='#555',linewidth=.8);ax.set_ylabel('Avoided combustion CO$_2$ (t per 168 h)');ax.legend(ncol=4,frameon=False,loc='upper left',fontsize=8.5);ax.spines[['top','right']].set_visible(False);fig.tight_layout();fig.savefig(out/'figure3_seasonal.png',bbox_inches='tight');plt.close(fig)
print('Three grayscale figures reconstructed from archived numeric CSVs:',out)
