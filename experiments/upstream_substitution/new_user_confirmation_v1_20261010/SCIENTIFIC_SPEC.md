# 新用户强基线确认：已授权冻结协议

状态：**FROZEN / 用户已直接确认预算、预检边界与协议；入组80人按规定确定，封存时未运行新用户预测或读取效果。**
本协议将已确认草案具体化。正式协议、80 人名单及输入/代码哈希在新用户预测/效果读取前封存。旧 FINAL 结果已用于研究设计，不能再作为本协议的独立确认。

## 目标与证据边界

检验已冻结 CommonPose 门控在新的、未记录参与既往门控/跨项目科学工作流的用户上，能否在相同接受预算下优于事前指定的强基线。Flip 是冻结 trusted8 LDA consumer 对 GT 表示与预测表示的输出不一致，不是独立手势标签错误。该确认仍不能证明 checkpoint 从未训练过这些用户：上游具体训练成员身份 unresolved。

论文和本地复算版本固定为 Git `1fc75512698c92d4bd11cf52e660c8814b1ac127`。20-seed 独立核验 PASS；score-only 继续暂缓，不为新确认新增模块或拟合门控。

## 入组与数据规则

1. 入组人数固定 **80**。不会将 80 名入组等同于 80 个有效非零配对，也不会根据效果增加、替换用户或改比较方法。
2. 候选池使用 `HISTORICAL_ACCESS_ADJUDICATION.json` 的 127 名用户及其 SHA256：排除 49 名原 CommonPose 接触用户、7 名 HumanEngine 既往工作流接触用户、10 名剩余保护预留用户。旧开发、旧 FINAL 和保护用户全部排除。
3. 封存前完成候选历史范围复核；任何新发现的既往科学接触需有 provenance 证据，并在选择前公开修正候选池。已有本地审计包含隐藏/忽略的清单与处理工件文件名；未保存的交互、目录外和私有远端历史不能由阴性搜索证明不存在。用户若知有其他接触，应在封存前说明。不得将未知写为未接触事实。
4. 从最终封存候选池按 SHA256 UTF-8 字符串 `COMMONPOSE_NEW_USER_CONFIRMATION_V1|20261010|<user_id>` 的十六进制摘要升序取前 80；相同摘要以 user_id 升序。排序和名单已按该规则写入 ENROLLMENT_MANIFEST.json，后续不改变。 不按文件大小、预期表现或候选结果选择。
5. 每个用户采用 `IDENTITY_REGISTRY_PRECHECK.csv` 已记录的 `preflight_session_id`，该会话左右手全部官方文件，与 `CANDIDATE_SOURCE_PREFLIGHT_MANIFEST.json` 对应。不得另选会话以改善效果。
6. 在读取新用户效果前，先封存官方 metadata、tar-index、ETag、全部选定 member/偏移/尺寸、代码、模型与运行环境。下载使用精确 Range、ETag 与长度核验；逐文件 SHA256 建立完整收据。公开 tar 没有独立官方 member SHA256，本地/远端相同哈希证明转移一致性，不应声称官方逐文件真值哈希认证。
7. 文件结构须为一维 timeseries，emg 16 通道、joint_angles 20 维、time 一维；长度超过 1790+80；时间有限且严格递增。GT 有效性沿用 V1：对齐后每行有限且非全零、40 行完整有效块、首块剔除；每会话累计有效 50Hz 块至少 10,000。源 EMG 非有限、结构/时序/对齐不一致、文件缺失或校验冲突立即停止并留痕，不插值修复或替换用户。只读元数据抽查通过不能代替这些全量检查。
8. 结构失败、运行失败、类别支持缺失均保留在 80 人流程报告，不补人。纯传输失败允许对同一 member 续传/重试并记录，不改变科学规则；科学资格失败不得借重试换数据。可在修复纯执行错误后重跑完全相同的封存输入，原尝试保留。

## 冻结方法与执行顺序

沿用原 checkpoint、canonical16 表示、trusted8 consumer、alignment、Fisher scale、四视图 TTA、特征列与已持久化 DEV-only 模型；新用户上没有训练、校准或阈值优化。

| 依赖 | SHA256 |
| --- | --- |
| regression_vemg2pose checkpoint | `748b1d1ef0ce1985f6fc07225d97eebfb370243429af803b4997d28ecce2424e` |
| trusted8 LDA consumer | `b0ef8caf8e390a480fa2a3b448f79ccf14f75c71265ef925ee299a5e9e660386` |
| canonical_hand.py | `24694cfda80604148490485d47bf5eddc8e20479d1b55d522ca5d0199b649193` |
| Fisher reference scale | `d15997aa56e5264bdede56c10727a910f94b2c7e32ab8137a6e8e9e45c39c667` |
| U full gate | `ca06d630e40fc44687bec5ac12c83d9b20aa7c48fe200d89e48d583f9d09f035` |
| B full gate | `535828304087d511402c8224ea0276d55e58e0a0c1cba0562bafe7d2d1147b66` |
| U class_model | `1d08ebfb338919488c2e4e8e5f72a29777a475ccd70d89e4ee12ebb84a56140e` |
| B class_model | `39f0cb7963cec31c6df647664a91b37bc13a266e37f9a65c8e8ef0f766ef249f` |

正式 manifest 同时封存 helper、upstream 97 文件 tree、no_tta 模型、两份 SUPPLEMENT_INSTANCE 的 empirical rates / 全部部署阈值和原 producer 代码；此处摘要表不代替完整输入封存。

数值环境使用 Python 3.10.13、NumPy 1.26.4、SciPy 1.13.1、scikit-learn 1.5.2、joblib 1.4.2、threadpoolctl 3.7.0，OMP/OPENBLAS/MKL 线程数均 8。启动前重验 exact versions、模型/代码哈希、CUDA、磁盘容量。已知 1-thread 控制会改变极小分数排序，不作为可互换执行环境。

所有七种原方法一并输出：class_empirical、margin、entropy、boundary_distance、full、no_tta、class_model。固定名义接受比例 `[.3,.5,.6,.7,.8,.9,1]`。对每个用户/方法取排序前 `ceil(coverage*n)` 个块；分数升序优先，tie 使用原 SHA256 `seed|FINAL|user|block_index` 前 8 字节大端 uint64，block_index 沿用原确定性文件与块顺序。canonical seed 固定 `20261009`。`full` 指完整特征门控，不是 100% coverage。

先完成来源与有效性收据，再生成特征、七方法分数及类别支持。B 的固定共同类别集合只依照 canonical 30% 接受下七方法各类别支持均至少 30 块确定，不使用 flip 选择类别；随后保存集合哈希，再计算并打开效果。整个序列在正式协议里固定，不能看到 B 结果后修改集合。

## 两个共同主要终点

| 终点 | 事前固定比较 | 每用户风险与效应 |
| --- | --- | --- |
| U | 30% full 对 boundary_distance | ordinary flip risk；效应 = baseline risk − full risk |
| B | 30% full 对匹配 class_model | 两方法均在上述固定共同类别集合上等权平均 flip risk；效应 = baseline risk − full risk |

正值表示 full 更好。普通风险和固定类别等权风险不混用；不以 100% coverage 的无筛选服务为主要强基线。该比较来自封存前的研究设计，并明确披露旧数据曾参与设计。

以用户为独立分析单位，两个终点各采用双侧 exact sign test：非零配对中 positive 数服从零假设 Binomial(n_nonzero,.5)，用 `min(1,2*min(P[X<=positive],P[X>=positive]))`；每终点 alpha `.025`，Bonferroni 两终点 family `.05`。仅在正向且 p≤.025 时判该终点成功，两个均成功才支持共同主要结论。全零时 p=1、失败；不把 seed 或块数充当独立样本量。

每终点报告 80 人入组数、资格通过数、完整风险对数、正/零/负效应数和 n_nonzero。零效应保留在配对中位数描述、只从 sign test 分母移除；缺失不填零、不插补。若存在任何入组用户主要终点不可计算，完整队列确认判为 evidence_insufficient；可报告可计算子集的描述性中位数/CI与标明条件性的 p，但不能替代完整队列确认。

报告配对用户效应中位数及 20,000 次用户 bootstrap percentile 95% CI（seed 20261009），明确这是描述性精度区间而非同时覆盖两个终点的 familywise CI。无需 CI 门槛替代事前 sign test。没有根据阶段性效果停止、扩样或补人。

## 次要分析与报告规则

原七种方法/七覆盖曲线、原 DEV 固定阈值的实际部署覆盖率/绝对风险、class_empirical 与 no_tta 控制、类别内等比例接受、ordinary/dynamic/fixed-common 风险分别报告。缺失类别记为 missing，不置零。新用户上 20-seed `[20261009..20261028]` 只作为条件性 tie 敏感性；主要结论只来自 canonical，不选择最好 seed，不汇总为 80×20 独立样本。B 集合固定在 canonical，不随 seed 改。

发布包括完整流程与全部正/负/零/缺失结果、绝对风险、接受数、类别支持与 frozen-set hash；既有阴性分支保留。负结果不触发重新拟合、修改消费者、标签定义、阈值、用户或终点。score-only 不在此协议新增。

源文件、基础/TTA/特征缓存、分数与收据远端完整保留，本地 D 盘另有经 SHA256 核验的备份；目录与保留条件在正式 manifest 中明确，不删除旧实验。

## 当前预检与正式封存前的门槛

`PRECHECK_VERIFICATION.json` 已通过限定范围的元数据/历史/预算独立核验：127 名候选、4,285 个源记录边界、254/254 双手 schema 抽查、三次同文件 TLS-only 重试留痕。远端重新实测 200 GiB / 剩余约 188.00 GB，本地 D 盘能容纳 70 GB 预留，用户不要求金额预算。

**用户已确认预算、预检边界及草案**；本协议据此封存候选池/80 人名单、全部协议和输入哈希，随后执行下载、完整资格核验、固定推理和独立结果核验。全文件 SHA256、样本有效性及实际有效非零配对数目前 NOT_YET_AUDITED。
