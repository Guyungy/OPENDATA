---
title: 测试数据 (test1.md) 提取结果
date: 2026-03-08
author: 佳宜的AI助手
---

# MindVault 测试文档提取报告

佳宜，我已经将 `test1.md` 转换并作为数据源输入给 MindVault 进行了测试运行，以下是提取结果：

1. **整体处理统计**：
   - 数据源片段 (Chunks)：72
   - 解析陈述 (Claims)：74
   - **实体 (Entities)：3 个**
   - 提取事件 (Events)：0

2. **具体提取到的实体**：
   在 `workspaces/testdoc_run/canonical/current.json` 中，系统成功识别并提取了 3 个实体：
   - **S222** 
   - **S666**
   - **S858**
   （这三个实体实际上是文档中提到的技师代号。）

3. **效果分析**：
   系统从这份长文档中分离了 72 个文本块，并解析出了 74 个主张声明，但最终转换为标准对象的只有 3 个代号实体。这说明当前 MindVault 的默认实体提取提示（Prompt）或意图意向（Intent）偏向于寻找标准人物或机构（如前一次的 Atlas 等）。对于像服务评测这样较口语化或非标准的术语，可能需要进一步在 `intent.json` 中自定义配置 `preferred_entity_types` 等偏好规则，才能达到更高的解析命中率。

我已经为你更新了 `topic_01.svg` 和 `topic_02.svg` 幻灯片，直观展示了本次测试的提取数据和建议反馈。
