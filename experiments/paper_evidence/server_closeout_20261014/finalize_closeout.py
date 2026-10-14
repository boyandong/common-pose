"""Update audit documents only after successful local evidence delivery."""
from pathlib import Path
import json
import hashlib
import csv

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
AUDIT=ROOT/'docs/reviews/20261014_embc_no_supplement_audit'

def main():
    core=json.loads((HERE/'verified_remote/LOCAL_DELIVERY_VERIFICATION.json').read_text())
    field=json.loads((HERE/'verified_remote/field_delivery/LOCAL_DELIVERY_VERIFICATION.json').read_text())
    assert core['new_models']==60 and field['new_models']==42
    paper=json.loads((AUDIT/'PAPER_UNCHANGED_HASHES.json').read_text())
    assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in paper.items())
    p=AUDIT/'REVISION_CHECKLIST.md';s=p.read_text(encoding='utf-8')
    s='\n'.join(line for line in s.split('\n') if not line.startswith('|23|'))
    s=s.replace('证据问题：6项','证据问题：5项')
    s=s.replace('|24|P2|完整运行成本|现有fit_seconds、共享四视图缓存成本有记录；N80共享阶段6642.5058秒包含读取/哈希/存储/推理，不是纯GPU推理时间。完整研发/采集成本及流式逐输入延迟仍UNKNOWN。离线定位下可报告已有成本并保留范围。|','|24|P2|成本范围之外的历史成本与在线延迟|离线拟合、固定3记录GPU推理、读取/视图/聚合及CPU特征+参考/评分计时已完成，无需重复。历史研发/采集成本缺原记录；因果在线延迟需新的在线分支，仍UNKNOWN。本项仅保留这些未闭合部分，不将整记录耗时换算成在线保证。|')
    s=s.replace('完整独立对齐和实时因果路径未认证，','固定±40ms滞后与20/200/800ms窗口敏感性已完成。完整独立对齐和实时因果路径未认证，')
    s=s.replace('01、08、11、12、14、17、21、22共8项','01、08、11、12、14、17、21、22、23共9项')
    s=s.replace('当前18项活动任务：6项证据问题、12项文字/正文整合、图表及复现仓库任务。','当前17项活动任务：5项证据问题、12项文字/正文整合、图表及复现仓库任务。')
    s+='\n服务器闭合更新：23的P/F/T完整8组合（60新拟合、36原实例复用）及7组基础分数字段移除（42新拟合）均已完成并独立核验、下载封存。全部有符号结果保留，不选择新赢家；旧队列上的新变体是探索性证据。23移出重复实验清单，其必要呈现并入10/25。24仅部分闭合，原件缺口保留。原论文187文件hash再次全部匹配。详见 `experiments/paper_evidence/server_closeout_20261014/COMPUTATIONAL_CLOSEOUT_REPORT.md`。\n'
    p.write_text(s,encoding='utf-8')
    p=HERE/'COMPUTATIONAL_CLOSEOUT_REPORT.md';s=p.read_text(encoding='utf-8')
    s=s.replace('基础分数字段七组移除的42个补充拟合以独立终态回执为准，尚不由本段宣告完成。',f"基础分数字段七组移除42个补充拟合全部完成：预测类别one-hot、判别分数、top-two gap、熵、边界距离、四视图dispersion、plane SD。独立服务器{field['remote_independent_checks']:,}项检查通过，24,720个参与者评价行；本地另独立核对所有有符号配对中位数并复算42个主预算区间。完整结果见 `verified_remote/field_delivery/results/score_field_ablation/REPORT.md` 与CSV。")
    s+='\n## 最终交付与清单状态\n\n102个新模型、36个复用实例均有封存回执；主包与字段补充包已下载并逐文件核验。新模型没有替换原Full/U。清单12与23移出重复实验；24只闭合离线测量部分，历史成本和在线延迟仍在活动清单。其余待改写、论文图和GitHub发布均未执行。\n'
    p.write_text(s,encoding='utf-8')
    receipt={'status':'COMPLETE_ALL_PRESPECIFIED_EXISTING_DATA_COMPUTATIONS','new_models':102,'original_instances_reused':36,'core_checks':core['remote_independent_checks'],'field_checks':field['remote_independent_checks'],'field_local_summary_checks':field['local_summary_checks'],'paper_files_unchanged':len(paper),'active_checklist_items':17,'external_evidence_not_certified':True,'paper_edited':False,'public_repo_published':False}
    (HERE/'COMPUTATIONAL_CLOSEOUT_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__=='__main__':main()
