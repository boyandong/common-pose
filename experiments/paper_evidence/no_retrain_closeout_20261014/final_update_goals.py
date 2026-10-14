"""One final consolidated-goal update after verified no-retrain work."""
import json,re,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
AUDIT=ROOT/'docs/reviews/20261014_embc_no_supplement_audit'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    receipt=HERE/'FINAL_GOALS_UPDATE_RECEIPT.json';assert not receipt.exists(),'Final update already recorded; do not repeat'
    v=json.loads((HERE/'INDEPENDENT_VERIFICATION.json').read_text());assert v['status']=='PASS'
    target=AUDIT/'ALL_27_REVISION_GOALS_AND_FINDINGS.md'
    assert target.read_bytes()==(HERE/'GOALS_BEFORE_FINAL_UPDATE.md').read_bytes()
    before=sha(target);text=target.read_text(encoding='utf-8')
    notes={
      '02':'**无重训工作终态（2026-10-14）：** 已重新核对本地权重及metadata摘要，连接早期下载、资产、checkpoint检查与官方release成员；完成限定范围的本地run原件搜索和公开入口检查。仍未建立权重SHA绑定的实际训练清单。当前六消费者A20按公开配方为16/20有train记录；历史FINAL的18/20不能移用。N80仍为70/80。session标签是官方metadata标识，不自行认证连续物理采集。来源追溯完成，实际暴露保留UNKNOWN。',
      '03':'**无重训工作终态（2026-10-14）：** 冻结结果按公开配方分组已经计算并独立复核：384单元、8142参与者配对差值，覆盖A20/N80、四预算、两个基线及U/B，所有区间独立复算。实际A20为16/4，与历史FINAL完全不相交；N80为70/10。A20无train组含2名test-only、2名val-only；N80含6名test-only、4名val-only，不能称为纯独立测试或确证未见。N80无train组主预算CeTI两项、KIN的U区间跨0；SHOW B改善−29.261pp [−33.406,−9.024]，仍为恶化。A20小组n4明确低支持；DB9 posture小组B不可计算。没有按结果选组、修改模型或推断泄漏。',
      '05':'**无重训工作终态（2026-10-14）：** 已整理六消费者×八关节的48行实际选列、单位和校准证据；用本地16个SHOW原profile重新核对hash、拓扑、轴，并用独立atan2几何计算复核rest bend，与旧记录一致。八角轴cosine最小0.97425195；个体rest差异确认。官方自身校准有文献依据；这些几何事实仍不是实测共同零位，也不认证跨设备数值等价。旧锚点判决NO_INDEPENDENT_ANCHOR保持，无拟合offset/scale。',
      '06':'**无重训工作终态（2026-10-14）：** 已复核10个冻结上游关键源码hash；实际缓存代码中预测与GT均对齐裁去1790行后的相同40行区间，time采用块末，首块剔除与尾截断、GT mask单独记录。10个固定长度的绝对行号/ramp/块末对应共223,348项索引代数检查通过，短长度仅为代数边界，不认证脚本可接受或物理同步。官方<10ms是作者报告；895ms是启动历史，20ms是块网格，19.5ms是块内首末跨度，都不是实测延迟。既有whole-record未来依赖和窗口差异保留；无重训代码/索引工作完成，独立传感器误差及完整在线认证仍未完成。',
      '24':'**无重训工作终态（2026-10-14）：** 已汇总692条成本记录（590历史行、60组特征模型、42字段移除），区分重复/复用，未把旧重复行相加当研发总成本。60新模型记录累计12.416秒涵盖fit+序列化；42新模型记录累计47.397秒还包括hash及DEV阈值评价/选择，不能都称纯fit或直接同比。GPU/CPU已有36/6次阶段计时、源域复现和缓存/controller墙钟已单列，无额外计时重跑。离线日志整理完成，完整历史成本及因果在线延迟仍未知。',
      '04':'**本轮补充：** 泛化表述必须区分当前A20（公开train16/20）与历史FINAL（18/20），以及CommonPose门控开发外用户、公开配方留出用户、实际checkpoint未见用户三个层级。公开val-only用户也不能当作纯独立最终测试。',
      '07':'**本轮补充：** 原数据有官方同步/个体校准说明，不能泛称“没有校准或同步证据”。尚未认证的是跨源共同物理零位、独立残余同步误差和我们整条处理路径的因果性。',
      '10':'**本轮补充：** 新增条件分组、48接口矩阵、16profile几何、时间索引和成本范围均已封存，正文可按主线取舍。A20/历史FINAL必须使用正确队列命名，不把所有内部材料当作必须提交的附件。',
      '13':'**本轮补充：** 本轮公开配方分组是事后探索，384单元不是384次独立确认；n4小组、val-only成分、跨零及B不可评估单元保留。19,749项程序核验不是科学样本量。',
      '15':'**本轮补充：** SHOW类别反向结果也出现在N80无公开train记录的10人条件组（B恶化29.261pp），但该组含4名val-only且实际权重成员未知；不能据此宣称独立训练外确认。'
    }
    chunks=re.split(r'(?=^## \d{2}｜)',text,flags=re.M);result=[]
    for chunk in chunks:
        m=re.match(r'## (\d{2})｜',chunk)
        if m and m.group(1) in notes:chunk=chunk.rstrip()+'\n\n'+notes[m.group(1)]+'\n\n'
        result.append(chunk)
    text=''.join(result)
    text=text.replace('更新日期：2026-10-14（Asia/Shanghai）。','最后更新：2026-10-14（Asia/Shanghai），本轮无重训工作已封存。')
    text=text.replace('**状态：P0；未闭合。**','**状态：P0；无重训条件分组完成，实际权重成员未闭合。**',1)
    text=text.replace('本地统计、源域复现、服务器消融和敏感性实验已完成。','无重训最终轮另完成公开配方条件分组、定义/几何、索引及成本核查，19,749项独立检查通过；02/03/05/06/24的原件/独立观测残余缺口仍保留。\n\n本地统计、源域复现、服务器消融和敏感性实验已完成。',1)
    link='<PROJECT_ROOT>/experiments/paper_evidence/no_retrain_closeout_20261014/REPORT_ZH.md'
    text+='\n## 本轮最终更新说明\n\n用户要求的不重训可执行工作已完成，本文件在独立核验后统一更新一次；27编号全部保留。当前活动数量仍为17，未因审计完成删除真实原件/独立测量缺口。\n\n[无重训最终核查报告]('+link+')含实际队列分组、全部有符号结果、失败/纠正记录、来源范围、几何/时间验证及成本口径。论文和原图未修改；模型、阈值、adapter及原队列未改变。\n'
    assert re.findall(r'^## (\d{2})｜',text,re.M)==[f'{i:02d}' for i in range(1,28)]
    assert text.count('**当前发现：**')==27
    target.write_text(text,encoding='utf-8');(HERE/'GOALS_AFTER_FINAL_UPDATE.md').write_bytes(target.read_bytes())
    value={'status':'COMPLETE_SINGLE_FINAL_27_GOALS_UPDATE','before_sha256':before,'after_sha256':sha(target),'goal_count':27,'independent_checks':v['checks'],'source_report_sha256':sha(HERE/'REPORT_ZH.md'),'models_fitted':0,'inference_rerun':False,'paper_edited':False,'external_evidence_gaps_preserved':True}
    receipt.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
if __name__=='__main__':main()
