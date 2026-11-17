# 主动式自我进化 (Proactive Self-Improving Agent - Chinese Variant)

Chinese-language self-improvement variant with safety guards and structured changelog.

## 核心差异点
- 完整的CHANGELOG.md JSONL操作日志（每次写入都追加记录）
- ADL协议（Anti-Drift Limits）防止经验漂移
- VFM协议（Value-First Modification）晋升打分机制

## CHANGELOG.md 格式

每条记录是JSONL格式：
```jsonl
{"ts":"2026-03-02T11:00:00+08:00","action":"add","type":"learning","id":"LRN-20260302-001","summary":"API需要3s间隔防限流"}
{"ts":"2026-03-02T14:30:00+08:00","action":"add","type":"error","id":"ERR-20260302-001","summary":"扫描版PDF返回空文本"}
{"ts":"2026-03-03T09:00:00+08:00","action":"promote","type":"learning","id":"LRN-20260302-001","summary":"API限流规则","target":"TOOLS.md"}
```

| action | 含义 |
|--------|------|
| add | 新增记录 |
| promote | 晋升到永久文件 |
| extract | 提取为独立skill |
| resolve | 标记已解决 |

## ADL协议（Anti-Drift Limits）
- ❌ 不为了"看起来聪明"而增加复杂度
- ❌ 不做无法验证效果的改动
- ❌ 不用"直觉""感觉"作为改动理由
- ❌ 不为了新奇牺牲稳定性
- 优先级：稳定性 > 可解释性 > 可复用性 > 可扩展性 > 新奇性

## VFM协议（Value-First Modification）

晋升/提取前打分：

| 维度 | 权重 | 问题 |
|------|------|------|
| 检索复用性 | 3x | 未来会反复用到吗？ |
| 错误预防 | 3x | 能避免同样错误吗？ |
| 分析质量 | 2x | 能提升产出深度吗？ |
| 效率提升 | 2x | 能节省未来时间吗？ |

加权总分 < 50 → 不晋升。

## 坚韧原则（Relentless Resourcefulness）
操作失败时尝试5-10种方法后再考虑求助。
