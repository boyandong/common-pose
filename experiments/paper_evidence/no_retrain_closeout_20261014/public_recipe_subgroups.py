"""Describe frozen results under conditional public-recipe membership."""
import csv,json,hashlib
from collections import defaultdict
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
LOCAL=ROOT/'experiments/paper_evidence/local_closeout_20261014'
IDENTITY=ROOT/'docs/reviews/20261011_identity_runtime_causality_audit/USER_IDENTITY_INTERSECTION.csv'
NAMES={('db9_scoreonly_v3_20261011','C1_primary'):'DB9 posture',('db9_scoreonly_v3_20261011','C2_primary'):'DB9 grasp',('ceti_age_scoreonly_v3_20261012','C1_primary'):'CeTI posture',('ceti_age_scoreonly_v3_20261012','C2_primary'):'CeTI grasp',('show3d_scoreonly_v3_20261012','C1_primary'):'SHOW instruction',('kinmus_uji_scoreonly_v3_20261012','C1_primary'):'KIN phase'}
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def table(p,rows):
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def interval(cohort,paired):
    if not paired:return None,None,None
    users=[r['user'] for r in paired];x=np.array([r['difference_pp'] for r in paired]);n=len(x)
    seed=int.from_bytes(hashlib.sha256(('20261014|'+cohort+'|'+'|'.join(users)).encode()).digest()[:8],'little')
    ix=np.random.default_rng(seed).integers(0,n,size=(10000,n),dtype=np.int32)
    lo,hi=np.quantile(np.median(x[ix],axis=1),[.025,.975]);return float(np.median(x)),float(lo),float(hi)
def main():
    metadata=read(ROOT.parent/'emg2pose_handstate/data/priority_pose_subset/raw/emg2pose_metadata.csv')
    by_user=defaultdict(list)
    for r in metadata:by_user[r['user']].append(r)
    members=[];pairs=[];summary=[];service=[]
    for cohort,expected in [('A20',20),('N80',80)]:
        rows=read(LOCAL/'reproduction_bundle/input'/(cohort+'_USER_COVERAGE_SERVICE.csv'))
        rows=[r for r in rows if r['goal']=='U' and r['mode']=='offline_equal_coverage'];users=sorted({r['user'] for r in rows});assert len(users)==expected
        groups={}
        for user in users:
            rr=by_user[user];assert rr
            n=sum(r['split']=='train' for r in rr)
            group='PUBLIC_RECIPE_TRAIN_OVERLAP' if n else 'PUBLIC_RECIPE_NO_TRAIN_RECORDS'
            groups[user]=group;members.append({'cohort':cohort,'user':user,'public_recipe_group':group,'official_train_records':n,'official_split_profile':'|'.join(sorted({r['split'] for r in rr})),'held_out_user_values':'|'.join(sorted({r['held_out_user'] for r in rr})),'actual_checkpoint_membership':'UNKNOWN','group_is_checkpoint_membership':False})
        lookup={(NAMES[(r['lane'],r['condition'])],r['user'],r['method'],r['nominal_retention']):r for r in rows}
        for group in ['PUBLIC_RECIPE_TRAIN_OVERLAP','PUBLIC_RECIPE_NO_TRAIN_RECORDS']:
            group_users=[u for u in users if groups[u]==group]
            for consumer in NAMES.values():
                for q in ['0.1','0.3','0.5','0.7']:
                    for metric in ['U','B']:
                        for baseline in ['boundary','score_only']:
                            paired=[]
                            for user in group_users:
                                a=lookup[(consumer,user,baseline,q)];b=lookup[(consumer,user,'full',q)]
                                if a[metric] and b[metric]:
                                    r={'cohort':cohort,'public_recipe_group':group,'consumer':consumer,'retention':q,'baseline':baseline,'metric':metric,'user':user,'difference_pp':100*(float(a[metric])-float(b[metric])),'actual_checkpoint_membership':'UNKNOWN'}
                                    paired.append(r);pairs.append(r)
                            md,lo,hi=interval(cohort,paired)
                            summary.append({'cohort':cohort,'public_recipe_group':group,'consumer':consumer,'retention':q,'baseline':baseline,'metric':metric,'group_users':len(group_users),'paired_users':len(paired),'median_reduction_pp':md,'CI95_low_pp':lo,'CI95_high_pp':hi,'status':'UNDEFINED' if not paired else 'LOW_SUPPORT' if len(paired)<10 else 'EXPLORATORY_CONDITIONAL_POINTWISE','actual_checkpoint_membership':'UNKNOWN'})
                        for method in ['all','boundary','score_only','full']:
                            rr=[lookup[(consumer,u,method,q)] for u in group_users] if method!='all' else []
                            if not rr:continue
                            vals=[float(r[metric]) for r in rr if r[metric]]
                            service.append({'cohort':cohort,'public_recipe_group':group,'consumer':consumer,'retention':q,'method':method,'metric':metric,'group_users':len(group_users),'evaluable_users':len(vals),'median_risk':float(np.median(vals)) if vals else None,'actual_checkpoint_membership':'UNKNOWN'})
    assert len(summary)==384 and len(members)==100
    table(HERE/'PUBLIC_RECIPE_MEMBERSHIP.csv',members);table(HERE/'PUBLIC_RECIPE_PAIRED_DIFFERENCES.csv',pairs);table(HERE/'PUBLIC_RECIPE_SUBGROUP_SUMMARY.csv',summary);table(HERE/'PUBLIC_RECIPE_SUBGROUP_SERVICE.csv',service)
    print('PUBLIC_RECIPE_SUBGROUPS_COMPLETE',len(summary),len(pairs))
if __name__=='__main__':main()
