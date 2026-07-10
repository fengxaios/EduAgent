# Pipeline 通信协议对比

## 纯文本模式
```

    定积分的知识点有牛顿莱布尼茨公式、定积分概念、定积分应用。
    建议先学极限和导数，再学定积分。学生容易搞混不定积分和定积分。
    
```
**问题**: 无状态标记、无置信度、无摘要，下游 Agent 盲猜质量。

## 结构化协议（PentAGI 式）
```json
{
  "agent_name": "knowledge_mapper",
  "task": "拆解定积分知识点",
  "status": "success",
  "artifact": "## 知识树\n- 定积分概念 (★☆☆)\n- 牛顿-莱布尼茨公式 (★★☆)\n- 定积分应用 (★★★)",
  "summary": "定积分拆解为3个层级，覆盖概念→公式→应用",
  "confidence": 0.85,
  "metadata": {
    "knowledge_count": 3,
    "has_dependencies": true,
    "has_warnings": true
  },
  "timestamp": "2026-07-10T13:26:08.553519"
}
```
**优势**: 状态显式、置信度可量化、摘要即取即用、元数据指导重试。
