> 2026-10-14 发布补记：用户随后授权当前 common-pose 仓库公开并替换旧 commonpose-v1。本文后面的私有同步回执描述 V5.2 完稿时的历史状态；当前访问状态见仓库根 README。稿件正文、作者信息和科学结果未因此修改。

# CommonPose EMBC 2027 — V5.2 投稿候选终稿

2026-10-14。按用户V5.2附件定点修改，作者信息已由用户确认。未执行新训练、推理、选模、调参或阈值优化。AI披露建议按用户指令暂不采纳；未提交论文。

## 交付

- 英文：`output/pdf/CommonPose_EMBC2027_V5_2_EN.pdf`。
- 中文对照：`output/pdf/CommonPose_EMBC2027_V5_2_ZH.pdf`，供导师阅读，非会议提交版本。
- **英文全文源码：`CommonPose_EMBC2027_V5_2_EN.tex`**。摘要、五大章节、四个公式、主表和十条参考文献全部内嵌，没有`input`或外部bibliography依赖。三张矢量PDF图在`figures/`，IEEE类文件随包提供。
- 图形可编辑SVG、矢量PDF、彩色及灰度图在`figures/`；最终页面预览在`qa/`。
- 准确差异、数值/双语映射、模板和引用检查、作者确认及GitHub同步回执在`review/`。

编译英文：在本目录执行`tectonic -X compile CommonPose_EMBC2027_V5_2_EN.tex --outdir build`，先建立`build`目录。也可用标准LaTeX发行版编译该完整.tex；本轮实际验证引擎为Tectonic 0.17.0+20260731。图片已预制，编译不需要运行模型或制图。

中文对照稿为了阅读采用11pt正文，英文投稿候选仍为IEEE 10pt、US Letter和原类文件页边距。中文系统字体仅用于本机编译并嵌入PDF，未在交付包或GitHub分发完整字体文件。

## 放行范围

技术编辑、主要冻结数据检查、五页布局、矢量图、双语内容及作者信息已核对。状态为`READY_FOR_SUPERVISOR_REVIEW`，不是已经提交或已经由导师批准。最终科学责任审阅与投稿系统/PDF预检仍由作者和导师完成。官方网页新模板下载受robots/403限制，当前类文件与用户提供的官方IEEE模板包逐字节一致；此限制已记录。

GitHub仍为私有仓库；进度同步到`codex/progress-20261014`，不更改主分支或本地历史，不创建Release或公开仓库。正文没有虚构公开Code Availability。初始同步逐文件核验1089个文件；最终V5.2追加同步回执见`review/GITHUB_V5_2_SYNC.json`。

`source/generate_figures.py`使用封存CSV；`reproducibility/figure_data/`为制图输入，不是全部原始EMG或模型公开发行包。原训练成员、物理零位、独立同步与线上服务/成本缺口保留为研究解释限制，不以写作修订宣称解决。
