"""Execute the directly approved N80 hash selection, without reading outcomes."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
DEST=HERE.parent/'new_user_confirmation_v1_20261010'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,obj):
    p=DEST/name
    if p.exists():raise RuntimeError('refuse overwrite '+str(p))
    p.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    p.with_suffix(p.suffix+'.sha256').write_text(sha(p)+'  '+p.name+'\n')

def main():
    review=json.loads((HERE/'REVIEW_PACKET_MANIFEST.json').read_text())
    for n,h in review['review_documents_sha256'].items():assert sha(HERE/n)==h,n
    precheck=json.loads((HERE/'PRECHECK_VERIFICATION.json').read_text())
    for n,h in precheck['artifact_sha256'].items():assert sha(HERE/n)==h,n
    assert precheck['status']=='SCOPED_METADATA_AND_RESOURCE_PRECHECK_VERIFIED'
    history=json.loads((HERE/'HISTORICAL_ACCESS_ADJUDICATION.json').read_text())
    source=json.loads((HERE/'CANDIDATE_SOURCE_PREFLIGHT_MANIFEST.json').read_text())
    users=history['candidate_users'];assert len(set(users))==len(users)==127
    rank=sorted(users,key=lambda u:(hashlib.sha256(('COMMONPOSE_NEW_USER_CONFIRMATION_V1|20261010|'+u).encode()).hexdigest(),u))
    selected=rank[:80]
    files=sorted((r for r in source['files'] if r['user'] in selected),key=lambda r:(r['user'],r['source_member']))
    with (HERE/'IDENTITY_REGISTRY_PRECHECK.csv').open(encoding='utf-8',newline='') as f:
        registry={r['user_id']:r for r in csv.DictReader(f)}
    assert len({r['user'] for r in files})==80
    assert all(registry[u]['status']=='METADATA_ELIGIBLE_PENDING_FULL_ACCESS_AUDIT' for u in selected)
    DEST.mkdir(exist_ok=True)
    auth={'source':'direct human reply to the review approval question',
          'answer':'确认，按草案封存并执行','recorded_utc':datetime.now(timezone.utc).isoformat(),
          'approved_draft_sha256':sha(HERE/'DRAFT_PROTOCOL_FOR_CONFIRMATION.md'),
          'review_packet_sha256':sha(HERE/'REVIEW_PACKET_MANIFEST.json'),
          'enrollment':80,'replacement_allowed':False,'effect_dependent_addition_allowed':False}
    write('AUTHORIZATION.json',auth)
    protocol=(HERE/'DRAFT_PROTOCOL_FOR_CONFIRMATION.md').read_text(encoding='utf-8')
    protocol=protocol.replace('# 新用户强基线确认：待确认草案','# 新用户强基线确认：已授权冻结协议')
    protocol=protocol.replace('状态：**DRAFT / 未封存、未选择入组名单、未运行新用户预测或读取效果。**','状态：**FROZEN / 用户已直接确认预算、预检边界与协议；入组80人按规定确定，封存时未运行新用户预测或读取效果。**')
    protocol=protocol.replace('本草案将既有样本量规划具体化。预算与预检经用户确认后，才生成正式协议、80 人名单及输入/代码哈希封存。','本协议将已确认草案具体化。正式协议、80 人名单及输入/代码哈希在新用户预测/效果读取前封存。')
    protocol=protocol.replace('**本草案不计算这个排序、不产出名单。**','排序和名单已按该规则写入 ENROLLMENT_MANIFEST.json，后续不改变。')
    protocol=protocol.replace('**待用户确认预算、预检边界与本草案后**，才封存候选池/80 人名单、全部协议和输入哈希，并执行下载、完整资格核验、固定推理和独立结果核验。','**用户已确认预算、预检边界及草案**；本协议据此封存候选池/80 人名单、全部协议和输入哈希，随后执行下载、完整资格核验、固定推理和独立结果核验。')
    p=DEST/'SCIENTIFIC_SPEC.md'
    if p.exists():raise RuntimeError('refuse overwrite protocol')
    p.write_text(protocol,encoding='utf-8');p.with_suffix('.md.sha256').write_text(sha(p)+'  '+p.name+'\n')
    write('ENROLLMENT_MANIFEST.json',{
        'status':'FROZEN_BEFORE_NEW_USER_PREDICTIONS_OR_EFFECTS','selection_namespace':'COMMONPOSE_NEW_USER_CONFIRMATION_V1|20261010|',
        'selection_rule':'ascending SHA256 hex, user ID as tie break; first 80 of the frozen 127 metadata candidates',
        'enrolled_users':selected,'candidate_users':sorted(users),'enrollment_count':80,
        'sessions':{u:registry[u]['preflight_session_id'] for u in selected},
        'files':files,'total_files':len(files),'total_bytes':sum(r['size'] for r in files),
        'source_url':source['source_url'],'etag':source['etag'],'archive_bytes':source['archive_bytes'],
        'canonical_seed':20261009,'conditional_seed_range':[20261009,20261028],
        'protocol_sha256':sha(p),'authorization_sha256':sha(DEST/'AUTHORIZATION.json'),
        'candidate_source_manifest_sha256':sha(HERE/'CANDIDATE_SOURCE_PREFLIGHT_MANIFEST.json'),
        'history_adjudication_sha256':sha(HERE/'HISTORICAL_ACCESS_ADJUDICATION.json'),
        'selection_code_sha256':sha(Path(__file__)),'no_replacement':True,
        'upstream_training_membership':'UNRESOLVED','valid_nonzero_pairs_assumed':False})
    print(json.dumps({'status':'N80_ENROLLMENT_AND_PROTOCOL_FROZEN','users':80,'files':len(files),'bytes':sum(r['size'] for r in files),'cohort_sha256':sha(DEST/'ENROLLMENT_MANIFEST.json'),'protocol_sha256':sha(p)}))

if __name__=='__main__':main()
