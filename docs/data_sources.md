# 数据来源与校验

## 数据源优先级

1. Official：中国体育彩票官方开奖网关 `webapi.sporttery.cn`。
2. Trusted fallback：只在官方接口不可用时由维护者明确启用，且必须标记来源。
3. Local cache：`data/raw/` 中最近一次完整、通过 JSON 解析的官方响应。

`scripts/initialize_data.py` 负责一次性初始化，`scripts/update_draws.py` 只增量获取。原始响应先写临时文件、执行 `fsync`，再用原子替换覆盖缓存；SQLite 更新在事务中完成。

## 校验

检查号码数量、号码范围、同区重复、期号重复、日期倒序、销售额异常和规则版本不匹配。不同来源冲突时应写入 `data_warnings`，不允许静默覆盖。

`verified=1` 表示记录通过本地结构校验并来自标记的数据源；它不意味着第三方独立复核已经完成。

