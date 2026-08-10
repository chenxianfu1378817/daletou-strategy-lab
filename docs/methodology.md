# 方法论

## 研究问题

系统只回答一个问题：在单期 0–100 元的现实预算限制下，某策略是否在严格样本外、跨窗口和随机分布比较中稳定改善净收益。提高普通中奖次数而长期净亏损仍然是失败策略。

## Atomic Bets

单式与复式的共同底层都是最基础的 5+2 号码组合。复式仅是高度相关原子注的打包，会改变奖金分布与组合相关性，不会提高某个具体号码被摇中的概率。成本、覆盖、奖金、ROI 和仿真都按 Atomic Bets 计算。

## 数据分层

- Training：特征和模型拟合。
- Validation：Rolling-origin 参数比较和模型选择。
- Locked Holdout：模型、参数、特征、优化器冻结后只验收一次。
- Forward Paper：开奖前写入不可变预测，开奖后自动结算。

## 随机基准

- Baseline A：投注期、预算和结构相同，只换随机号码。
- Baseline B：号码策略不变，改为固定预算。
- Baseline C：随机号码、固定预算、固定频率。
- Coverage Baseline：随机号码加相同覆盖优化。

正式比较至少使用 100 个随机种子；研究报告应升级到 1000 个。只有超过随机高分位且通过稳定性与多重检验校正，才可能进入 Candidate。

## 防伪规律

特征默认无效。Permutation、Bootstrap、稳定性检验和 Benjamini–Hochberg FDR 用于减少 P-hacking；`number_of_hypotheses_tested` 必须随报告保存。

## Bet/Skip

Bet Score 只使用样本外超额收益、随机百分位、跨窗口稳定性、Forward 表现、模型分歧和不确定性。连续未中、累计亏损与“回本”需求从不提高预算。

