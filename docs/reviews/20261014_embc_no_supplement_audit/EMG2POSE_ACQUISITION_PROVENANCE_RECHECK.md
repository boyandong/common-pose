# emg2pose拉取记录与02／03／05／06证据重新定位

日期：2026-10-14，Asia/Shanghai。只读查证既有原件并补充公开原文，不重训、不下载完整数据、不连接服务器、不修改论文。

## 结论

可以找到官方来源和我们的拉取记录。不能概括为“当时完全不知道”：官方划分、数据时间对应、关节定义和权重来源有材料，项目早期也明确记录过实际checkpoint成员未闭合及跨源零位无独立锚点。现有记录不能证明每一条资料在最初下载时都被阅读过；记录存在与当时理解／完成验证不同。

此前将06概括成“真实同步未知”过于笼统。官方已有软件时间戳对齐和作者报告的相对延迟上界；应将这层已发表证据与本研究独立验证、下游处理时间语义分开。

## 当时留下了哪些原件

|记录|可确认的信息|不能推出的信息|
|---|---|---|
|`emg2pose_handstate/logs/download_full/metadata_download.log`|第一行记录2026-09-17 22:16:26（+08:00）metadata下载开始。|不是训练run日志。|
|同目录`verify_mini_report.json`|2026-09-17 22:30:16的mini验证记录：30个HDF5，metadata覆盖25,253文件、193用户及划分字段。|30文件验证不等于全量HDF5均下载／通过；metadata覆盖范围与实际下载范围不同。|
|同目录`metadata_analysis.txt`|已有user/session/start/end/side/held_out_user/split/generalization分析；公开train涉及158用户。|文件split=test不等于用户未参与训练，公开划分也不直接绑定当前权重run。|
|`fingers/bootstrap_manifest.json`|记录官方源码commit、数据资产、五个checkpoint摘要；实际regression_vemg2pose为71,878,748字节，SHA256匹配。|此资产搬运清单没有实际预训练成员。|
|`gate4b_multiuser_reliability/GATE4B_PLAN.md`|自述2026-09-22前瞻身份冻结；明确写出上游checkpoint成员UNRESOLVED，禁止宣称上游未见。|不能据此知道是谁最早阅读或发现；文件是项目既有证据边界记录。|
|`gate1_5_reference_zero/artifacts/TRUSTED8_ZERO_COMPATIBILITY.json`|记录NO_INDEPENDENT_ANCHOR、NOT_MEASURED，针对DB9／emg2pose共同零位参考。|不意味着emg2pose本身没有采集校准。|
|`consumer2_target_A_v1_20261011/checkpoint_provenance/OFFICIAL_RELEASE_BINARY_IDENTITY.json`|2026-10-11官方发布包完整成员摘要与所用权重逐字节匹配。|官方发布二进制身份不自动给出训练用户run清单。|
|同目录`OFFICIAL_DATA_VERSION_OBSERVATION.json`|本地metadata与该次官方metadata SHA一致；源tar的ETag和大小与既有来源对应。|版本相同不能证明实际权重训练run使用了此版本。|

原源码版本：`5f6f62b1a0a08426adffe55900842e75a8adb38c`。

所用权重：`regression_vemg2pose.ckpt`，SHA256 `748b1d1ef0ce1985f6fc07225d97eebfb370243429af803b4997d28ecce2424e`。权重检查有epoch85、global_step16856、网络／优化器状态；已有检查未找到user/session/record/data-version清单。来源已确认，实际run成员仍缺直接绑定。

## 官方材料说明了什么

[官方仓库](https://github.com/facebookresearch/emg2pose)说明文件提供时间对齐的EMG和姿态，并列出user、session、held_out_user、split、generalization等metadata字段及预训练下载入口。当前本地官方README也保留了这些说明。

[原论文§3.2与附录B.2](https://arxiv.org/html/2412.02725v1#S3.SS2)描述软件时间戳对齐，作者内部测试报告两设备路径相对延迟低于10ms；光学60Hz、EMG2kHz，姿态线性插值到2kHz。附录B.2还说明采集前每手17个校准动作，用于个体手模型和marker位置估计。因此不能写成“官方未提供同步或校准说明”。

这些是作者报告及公开处理流程，不是本研究重新测得每文件残余同步误差，也不认证DB9／CeTI／SHOW／KIN与emg2pose的共同绝对零位。原论文的在线变体另使用缓存机制，附录C.5说明该实现未开源；也不能用其在线结果认证我们的whole-record路径。

## 四项应该如何重新表述

|项目|现在有依据的部分|仍缺的准确部分|处理|
|---|---|---|---|
|02|官方checkpoint身份、公开metadata版本、公开配方文件／会话／区间重合已审计。|将权重SHA与实际train记录、数据版本、预训练／微调过程绑定的run原件。|不再称权重来源不明；保留实际训练暴露未直接确认。|
|03|公开held_out_user/generalization及用户划分可恢复。|实际checkpoint层的成员确认。|可以报告“按公开配方”的分组；不能去掉限定语称实际权重严格未见。|
|05|emg2pose有个体校准与IK／UmeTrack定义；源域也有各自标定说明。|跨设备／模型的共同物理零位及严格等价锚点。|不再泛称没有校准；缺口是跨源可比性。|
|06|原数据有官方时间对齐，软件时间戳及作者报告<10ms上界；本地索引检查、滞后／聚合敏感性已完成。|本研究独立残余误差、推理插值／裁切后的时间对应边界、源／目标聚合差异及完整因果在线路径。|原数据同步说明这一层已有文献证据；不能继续把所有层统称未知，也不升级为整条路径已独立验证。|

不同源数据用于训练消费者，不是与目标记录同步采集的第二条流。“跨源时间对齐”不应让读者误以为需要在DB9与emg2pose之间寻找同一时刻；Flip的一一对应发生于同一目标记录的测量／估计姿态路径，源／目标窗口差异则是另一项迁移条件。

## 依据入口

- [早期metadata分析](<HISTORICAL_WORKSPACE>/logs/download_full/metadata_analysis.txt)
- [mini下载验证记录](<HISTORICAL_WORKSPACE>/logs/download_full/verify_mini_report.json)
- [早期资产搬运清单](<USER_HOME>/Desktop/fingers/bootstrap_manifest.json)
- [2026-09-22身份冻结计划](<PROJECT_ROOT>/experiments/upstream_substitution/gate4b_multiuser_reliability/GATE4B_PLAN.md)
- [当时checkpoint来源审计](<PROJECT_ROOT>/experiments/upstream_substitution/gate4b_multiuser_reliability/artifacts/UPSTREAM_CHECKPOINT_PROVENANCE.json)
- [实际发布权重身份核验及剩余缺口](<PROJECT_ROOT>/experiments/multi_consumer/consumer2_target_A_v1_20261011/CHECKPOINT_PROVENANCE_ZH.md)
- [跨源物理定义审计](<PROJECT_ROOT>/experiments/multi_consumer/physical_equivalence_audit_20261012/REPORT_ZH.md)

本次结果只精确缩小缺口，没有恢复不存在的run成员或独立物理观测。27项目标总文件与活动清单同步附上本次发现，保留原编号。
