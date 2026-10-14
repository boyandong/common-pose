# CommonPose N80 科学判决：冻结主比较阳性，score-only 增量证据不足

本记录解释已独立核验的冻结结果，不新增终点、检验、模型、阈值、类别集合或成功标准。

## Verified fact：两个原主要终点均通过

80 名固定入组用户全部通过源资格核验；两个主要终点均有80个完整、非零配对，无缺失或零效应。canonical seed20261009、名义接受预算30%、每用户向上取整；用户是统计单位。

| 预注册比较 | 风险定义 | 正/零/负用户 | 配对效应中位数 pp | 描述性95% CI pp | 双侧 exact sign p | 判决 |
| --- | --- | --- | --- | --- | --- | --- |
| U：full vs boundary_distance | ordinary Flip risk | 68/0/12 | 3.472 | [1.867, 4.758] | 1.201648635082027e-10 | POSITIVE |
| B：full vs class_model | 原七方法固定共同类别上的等权风险 | 79/0/1 | 9.144 | [8.123, 10.950] | 1.3400325923359048e-22 | POSITIVE |

效应为每用户 comparator risk减full risk，正值有利于full。这里是配对效应的中位数，不能替换为两个独立风险中位数之差。两个终点各alpha=.025，联合判决POSITIVE；bootstrap区间是20,000次用户抽样的描述性区间，并非同时覆盖两终点的familywise区间。

## Verified fact：新增score-only控制没有建立full的稳定增量优势

score-only是事前独立封存的描述性secondary，复用旧DEV-only模型，不是第三primary。两项均80/80完整、非零配对。

| 描述性比较：score_only risk减full risk | 正/零/负用户 | 配对效应中位数 pp | 描述性95% CI pp | 未调整描述性sign p |
| --- | --- | --- | --- | --- |
| U | 42/0/38 | 0.115 | [-0.331, 0.670] | 0.7375543089843226 |
| B，保持原固定共同集合 | 45/0/35 | 0.103 | [-0.031, 0.220] | 0.31430657986393706 |

两项区间均跨0。因此原primary阳性不能扩展成“full稳定优于匹配的consumer-score特征控制”，也不能扩展成姿态/Fisher/TTA特征有已确认的增量贡献。没有注册等效性界值或等效性检验，不能把这些结果称为已证明等效。score-only含预测类别、consumer决策分数、margin、entropy和boundary，共19列；它不只是一个标量置信度。

全部七覆盖、20条件性tie seeds、原DEV固定阈值部署、类别内接受及支持诊断均保留。全体canonical secondary配对可计算，B原共同类没有score-only零支持；U的两个用户存在原共同类接受块数低于30，报告仍保留这些诊断。种子未汇总成独立用户，未选择最好种子；no_tta等阴性/近零对照也保留，不能作因果姿态/TTA分解。

## 证据边界与完成证据

Flip是一个冻结consumer在测量姿态和预测姿态上的输出不一致，不是独立标注手势精度。checkpoint训练成员身份UNRESOLVED。历史审计限于已保存的本地provenance，不能证明未保存、范围外或私有远端历史不存在。旧FINAL曾参与设计，不是新独立确认；现在已审视的N80也不能再次充当修订方法的独立确认。

原方案和score-only分别独立重算模型分数、排序、支持、风险、效应和规定统计行，均PASS；验证没有独立重跑神经推断。所有科学阶段及新接续控制器真实exit0。原丢失控制器退出原因/退出码仍UNKNOWN，旧terminal未伪造。source2768文件/50213536592bytes与新增17573项缓存、依赖、模型、结果/3333538048bytes在D盘逐项SHA256核验PASS；旧私有恢复档案、历史种子证据也另有核验D副本。

原七方法报告的历史score-only deferral字节保留。独立secondary和integrated报告明确更新为后来授权的补充lane。审阅时发现原renderer的支持类别列表未转义Markdown竖线，另存仅格式修正的可读副本；原renderer、原报告、全部数值和集合均未改。两张PNG已实际查看，13项full-goal audit PASS。固定Git/最终备份闭环以另行封存的release receipt为准。

## 冻结判决

这条lane已完成所规定的科学检验：支持原两个比较；没有建立full相对score-only的稳定增量优势。保留阳性、阴性、近零与未知边界，不做救援重设计。若进入新方法/机制研究，应开新决策会话并另行预注册；不得以本N80再次确认修订方法。
