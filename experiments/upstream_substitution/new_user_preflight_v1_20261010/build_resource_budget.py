"""Resource scenarios for 80 enrolled users; no selected cohort or purchase.

Every projection is separated from measured bytes/timing. Storage estimates use
the completed 39-user run; financial cost cannot be asserted without account
GPU/storage/transfer unit prices. Missing/zero effects do not change enrollment.
"""
import collections
import hashlib
import json
from pathlib import Path
import re
import shutil

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
CLOSING=BASE/'paper_closing_v1_20261010'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    manifest=json.loads((HERE/'CANDIDATE_SOURCE_PREFLIGHT_MANIFEST.json').read_text())
    history=json.loads((HERE/'HISTORICAL_ACCESS_ADJUDICATION.json').read_text())
    obs=json.loads((HERE/'REMOTE_RESOURCE_OBSERVATION.json').read_text())
    compute=json.loads((HERE/'GPU_AND_TIMING_OBSERVATION.json').read_text())
    cuda=json.loads((HERE/'CUDA_SMOKE_PREFLIGHT.json').read_text())
    per_user=collections.Counter();counts=collections.Counter()
    for r in manifest['files']:per_user[r['user']]+=r['size'];counts[r['user']]+=1
    assert len(per_user)==history['remaining_metadata_candidates']==127
    ranges=[sum(sorted(per_user.values())[:80]),sum(sorted(per_user.values())[-80:])]
    file_ranges=[sum(sorted(counts.values())[:80]),sum(sorted(counts.values())[-80:])]
    old_source=25141054576
    cache={k:[r*obs['cache_sizes'][k]['bytes']/old_source for r in ranges]
           for k in ['reconstructed/base','reconstructed/tta','features']}
    cache_total=[sum(v[i] for v in cache.values()) for i in [0,1]]
    old_elapsed=float(re.search(r'SECONDS ([0-9.]+)',compute['log_timing_lines'][-1]).group(1))
    linear_gpu=[old_elapsed*r/old_source/3600 for r in ranges]
    # Full retention on remote plus a verified source/cache backup on local D.
    report_allowance=1e9;model_allowance=.5e9;working_margin=10e9
    remote_new=[r+cache_total[i]+report_allowance+model_allowance+working_margin for i,r in enumerate(ranges)]
    local_backup=[r+cache_total[i]+report_allowance+model_allowance+working_margin for i,r in enumerate(ranges)]
    disks={d:{'total':shutil.disk_usage(d+':/').total,'free':shutil.disk_usage(d+':/').free} for d in ['C','D']}
    # Point-in-time remote data free bytes measured before any new source purchase.
    capacity=json.loads((HERE/'REMOTE_CAPACITY_RECHECK_AFTER_USER_UPDATE.json').read_text())
    remote_free=capacity['data_disk']['free']
    throughput=[{'MiB_per_second':rate,'download_source_hours':[r/(rate*2**20)/3600 for r in ranges],
                 'off_host_source_plus_cache_backup_hours':[(r+cache_total[i])/(rate*2**20)/3600 for i,r in enumerate(ranges)]}
                for rate in [.5,1,2,5,10]]
    budget={'status':'FULL_RETENTION_CAPACITY_PASS_PREFLIGHT_CONFIRMATION_PENDING',
            'user_selected_storage_scheme':'expanded_remote_full_source_and_cache_retention',
            'monetary_budget_requested':False,'user_waived_currency_budget':True,
            'planned_enrolled_users':80,'valid_nonzero_pairs_assumed':False,
            'metadata_candidates_after_history_exclusions':127,'source_bytes_range':ranges,
            'source_files_range':file_ranges,'projected_cache_bytes':cache,'projected_cache_total_bytes':cache_total,
            'report_and_score_allowance_bytes':int(report_allowance),'model_runtime_artifact_allowance_bytes':int(model_allowance),
            'working_safety_space_bytes':int(working_margin),'remote_additional_working_bytes_range':remote_new,
            'local_D_backup_bytes_range':local_backup,'local_disk_observations':disks,
            'remote_data_disk_free_bytes_observed':remote_free,'remote_data_disk_total_bytes':capacity['data_disk']['total'],
            'capacity_receipt_sha256':sha(HERE/'REMOTE_CAPACITY_RECHECK_AFTER_USER_UPDATE.json'),
            'remote_fits_full_retention_without_changes':max(remote_new)<=remote_free,
            'local_D_fits_one_off_host_verified_backup':max(local_backup)<=disks['D']['free'],
            'recommended_full_retention_remote_data_total_quota_bytes':120_000_000_000,
            'recommended_local_D_reservation_bytes':70_000_000_000,
            'old_complete_run_source_bytes':old_source,'old_reconstruction_elapsed_seconds':old_elapsed,
            'linear_projection_reconstruction_hours':linear_gpu,
            'conservative_reconstruction_reservation_hours':[4,10],
            'CPU_scoring_table_bootstrap_verification_reservation_hours':2,
            'network_scenarios':throughput,
            'GPU':compute['gpu'].strip(),'CUDA_smoke':cuda,'CPU_numerical_threads':8,
            'memory_limit_bytes':int(cuda['cgroup_memory_max']),
            'financial_unit_prices':{'GPU_hourly':'UNKNOWN','disk_capacity_monthly':'UNKNOWN','transfer':'UNKNOWN'},
            'financial_formula':'GPU price/hour * actual billed instance-hours (including acquisition/backup idle time if billed) + capacity GB-month price * added capacity * retention months + applicable transfer charges',
            'limits':'source subset range, not chosen roster; cache ratio and 1.8-2.3h linear timing are estimates from old users/earlier GPU runtime; 4-10h is a resource allowance, not measured N80 time; network scenarios are not measured throughput; no price quote or purchase',
            'source_manifest_sha256':sha(HERE/'CANDIDATE_SOURCE_PREFLIGHT_MANIFEST.json'),
            'history_adjudication_sha256':sha(HERE/'HISTORICAL_ACCESS_ADJUDICATION.json'),
            'code_sha256':sha(Path(__file__))}
    (HERE/'RESOURCE_BUDGET.json').write_text(json.dumps(budget,indent=2)+'\n')
    def gb(v):return f'{v/1e9:.2f}'
    def span(a):return gb(a[0])+'–'+gb(a[1])
    lines=['# 80 名入组用户：完整资源预算草案', '',
           '**尚未选择或封存用户，也未打开新用户结果。80 名入组不等于 80 个有效非零配对。**', '',
           '先完成项：20-seed 全量独立核验 PASS；论文与可复算代码固定在 `1fc75512698c92d4bd11cf52e660c8814b1ac127`。', '',
           '跨项目历史审计额外排除 HumanEngine 工作流的 7 名已接触用户。当前 193 名官方用户中，56 名已知接触、10 名剩余保护预留排除，127 名仍是待最终资格确认的元数据候选。以下范围来自这些候选的全部预检会话统计，不选取一个 80 人名单。', '',
           '| 项目 | 80 人预算 | 依据 / 身份 |','| --- | --- | --- |',
           f'| 源 HDF5 文件 | {span(ranges)} GB；{file_ranges[0]}–{file_ranges[1]} 个文件 | 元数据与 tar-index 精确范围；非已选名单 |',
           f"| 基础推理缓存 | {span(cache['reconstructed/base'])} GB | 旧 39 人实测比例外推 |",
           f"| TTA 缓存 | {span(cache['reconstructed/tta'])} GB | 同上；保留原四视图方法 |",
           f"| 用户特征缓存 | {span(cache['features'])} GB | 同上 |",
           f'| 三类缓存合计 | {span(cache_total)} GB | 估计；与原始源文件分开 |',
           '| 分数、表格、CI、收据与日志 | 1 GB 预留 | 包含逐用户/类别/seed明细，非新增训练 |',
           '| 冻结模型、依赖代码与运行工件 | 0.5 GB 预留 | 已有环境另占系统盘；不重新拟合 FINAL |',
           '| 临时工作空间与余量 | 10 GB | 不删除原有实验 |',
           f'| 远端新增工作空间 | {span(remote_new)} GB | 完整保留源文件与缓存；不含已有占用 |',
           f'| 本地 D 盘核验备份 | {span(local_backup)} GB | 另存一份源文件、缓存和结果，按未压缩大小计 |',
           f'| 两处合计新增预算 | {span([remote_new[i]+local_backup[i] for i in [0,1]])} GB | 两处均预留余量；不是额外两份本地源副本 |','',
           '## 当前可行性与已选方案','',
           f'收到用户扩容通知后重新实测：远端数据盘总量 {gb(capacity["data_disk"]["total"])} GB（200 GiB），剩余 {gb(remote_free)} GB，**满足完整保留容量预算**。此前 50 GiB / 剩余 26.94 GB 是扩容前记录，予以保留。本地 D 盘现有可用 {gb(disks["D"]["free"])} GB，可容纳一份核验备份；C 盘可用 {gb(disks["C"]["free"])} GB，不用于源文件备份。', '',
           '**用户已选择远端完整保留源文件与缓存；本地 D 盘预留 70 GB。** 当前容量核验通过。每次长任务启动前仍需重新核实剩余空间。本次核验未购买、扩容或删除文件。', '',
           '## 推理与传输时间','',
           f'旧 39 人 / 25.14 GB / 1,356 文件完整基础+TTA重建日志记录 {old_elapsed/3600:.3f} 小时，包括已有源的验证开销。按字节外推为 {linear_gpu[0]:.2f}–{linear_gpu[1]:.2f} 小时；新用户的有效帧比例与当前 GPU 变体不同，不能当作实测耗时。建议预留 **4–10 GPU 小时**用于重建，加 **2 CPU 小时**用于门控评分、统计与独立核验。当前 RTX 5090 D / 32 GB GPU 和 CUDA smoke通过，容器内存限额约 98.78 GB，数值线程保持 8。', '',
           '| 假设有效传输速率 | 拉取源文件 | 回传源+缓存备份 |','| --- | --- | --- |']
    for r in throughput:
        lines.append(f"| {r['MiB_per_second']:g} MiB/s | {r['download_source_hours'][0]:.1f}–{r['download_source_hours'][1]:.1f} 小时 | {r['off_host_source_plus_cache_backup_hours'][0]:.1f}–{r['off_host_source_plus_cache_backup_hours'][1]:.1f} 小时 |")
    lines+=['','这些是速率情景，不是已测吞吐；协议头、逐文件延迟、断点和校验会增加时间。若GPU租赁期间下载和备份也计费，账单实例小时必须包含这些等待时间，不能只计算纯推理小时。', '',
            '## 金额：用户不要求计算','',
            '用户确认预算足够，不要求金额预算，因此账户单价和保存期限不再作为资源规划前置条件。本文件保留容量、计算与传输情景，不编造价格或自动购买。', '',
            '## 数据完整性与历史访问边界','',
            '已对 127 名候选的 4,285 个预检会话文件（77.84 GB）核对官方元数据与 tar-index 哈希、唯一文件名、用户/会话/手别、字节数与边界偏移。逐候选每只手一个文件的 HDF5 schema元数据抽查共 254/254 通过；初次三次 TLS 传输失败记录保留，对同一文件重试后通过，无替换。抽查不证明所有文件完整哈希/时间戳/样本有效性通过。全文件SHA256、有限数值、时间戳对齐、完整有效40行块和实际非零配对数还需在冻结规则下采集/资格阶段核验，不以效果追加或替换用户。', '',
            '历史预检覆盖本地 fingers 根目录（包含隐藏/忽略的来源清单和处理工件文件名），未查看候选结果值。未记录的交互访问、外部目录/远端私有工作流仍不能由本地阴性搜索证明不存在。checkpoint特定训练用户身份 unresolved；不得称 upstream-unseen。', '',
            '预算和预检经用户确认后，才另立冻结入组与统计协议，并执行新的确认。当前保持完整目标未完成。']
    (HERE/'RESOURCE_BUDGET_ZH.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in budget.items() if k in ['status','source_bytes_range','projected_cache_total_bytes','remote_additional_working_bytes_range','local_D_backup_bytes_range','remote_fits_full_retention_without_changes','local_D_fits_one_off_host_verified_backup','linear_projection_reconstruction_hours']}))

if __name__=='__main__':main()
