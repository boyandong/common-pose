# CommonPose V5.2 candidate handover

## Objective
按用户V5.2附件完成定点终稿候选，暂不加AI披露，先同步私有GitHub进度，交付中英文PDF和完整英文.tex。

## Frozen decisions
不新训练/推理/选模/阈值优化；不改变模型、队列、指标、缓存或主结果；保留V5.1及更早版本；不投稿；不公开仓库/Release。作者信息由用户直接确认保留。

## Verified state
完整英文.tex内含正文、四公式、主表及十参考文献；三矢量PDF图片随包。中英文编译成功，英文明确四页正文＋第五页参考。冻结数字/双语映射/模板类字节/图形及页图检查在review目录。普通编辑项本轮完成，等待导师审阅。

## Scientific evidence
六主效应及CI、SHOW同79人相反方向、DB9 22→3、真实B共同支持人数保留。CeTI grasp直接Full/U对Score-only/U为3.789756pp [2.773887,4.691233] n80，取冻结CSV，没有新bootstrap。U/B不同权重并不认证具体机制。

## Unknown / contaminated state
实际checkpoint训练manifest/seen-unseen、共同物理零位、独立残余同步、在线因果服务和端到端成本未认证。AI披露建议用户暂不采纳，不能声称出版政策认证。最终导师责任审阅与门户PDF检查未完成。中文系统字体只在本机编译，不分发完整字体。

## External runtime state
没有连接/更改实验服务器。普通Git网络失败，改用GitHub Git API；私有进度快照2bbeb010396ab6f8d55fc76494e2e2840a1b56a5逐文件核验1089项。专用分支codex/progress-20261014，main和本地历史未改；最终V5.2追加回执见GITHUB_V5_2_SYNC.json。新会话必须重新核实远端分支，不假定旧会话状态。

## Worktree state
本地main既有47提交，仍有原来的未提交研究修改及未跟踪材料。同步快照不声称逐个推送41个本地ahead提交；没有改写历史。含凭据的历史传输脚本未同步，原文件保留。新增V5.2为独立dated lane。

## Next actions
导师阅读中英文PDF，作者依据放行记录确认最终责任和投稿门户检查。如仅需发布公开代码，另确认实际发布范围/访问版本与许可，不将私有快照写成公开可用。

## Do NOT
不发布原始信号/模型/凭据/系统字体；不为排版改数据；不自动新建V5.3；不把Flip解释为真实动作准确率或在线性能；不以已查看队列作为新独立确认。

## Session health / recommended session
本轮跨过终稿候选和GitHub同步阶段，已产生独立交接。建议后续导师反馈或正式投稿使用新会话`CommonPose-SUBMISSION-20261014-V5-2-REVIEW`。本轮网络恢复只检查/续传不可变blob，未重复未知分支修改；以后发生连续两次未知可变操作结果或崩溃时按AGENTS停止事故会话执行。
