Read PROJECT_SPEC.md, AGENTS.md, docs/architecture.md, docs/data-model.md, docs/workflows.md, and docs/acceptance.md first. Treat them as the system of record. Then implement the project incrementally, keeping the repository runnable at every step. Prefer building legible artifacts, strong validation, and feedback loops over clever hidden logic.


You are building a new project called MindVault.

Before coding, read these files and treat them as the system of record:
- PROJECT_SPEC.md
- AGENTS.md
- docs/architecture.md
- docs/data-model.md
- docs/workflows.md
- docs/acceptance.md

Your job is to implement MindVault as an AI-first self-growing knowledge operating system.

Important constraints:
1. Do not build this as a simple CRUD app.
2. Do not collapse raw, extracted, canonical, and governance layers.
3. Do not convert raw text directly into canonical facts.
4. Preserve provenance and evidence for all canonical knowledge.
5. Keep the project runnable after each milestone.
6. Prefer legible artifacts, validation, and feedback loops over hidden logic.
7. Use Python only for runtime, orchestration, validation, persistence, and rendering infrastructure.
8. Put evolving business intelligence into prompts, policies, agent definitions, and reviewable artifacts where appropriate.

Implementation goals:
1. Create a runtime core for ingestion, artifact routing, model routing, storage, and trace logging.
2. Create source adapters for at least:
   - chat text
   - webpage text
   - document/markdown text
3. Implement extracted artifacts:
   - claims
   - entity candidates
   - relation candidates
   - event candidates
   - schema candidates
4. Implement canonical artifacts:
   - entities
   - relations
   - events
   - insights
   - schema
   - taxonomy
5. Implement governance artifacts:
   - conflicts
   - placeholders
   - schema candidate queue
   - confidence scoring results
6. Implement snapshots and changelogs.
7. Implement a minimal dashboard that exposes both knowledge and governance state.
8. Include sample data and example outputs.
9. Add validation and basic tests.

Development approach:
- Work incrementally.
- For each milestone, implement the smallest coherent slice that keeps the repo runnable.
- Update README and docs as needed.
- Produce example workspace artifacts after each major step.

Do not ask for broad re-clarification unless repository docs are contradictory.
When in doubt, choose the option that improves inspectability, provenance, and governance.
```

---

# 我建议你让 Codex 分 4 个阶段做

OpenAI 讲 Codex 的最佳实践时，反复强调**长任务不是靠一个超长 prompt 一次干完，而是靠清晰的 harness、工具反馈、验证和持续修复**。([OpenAI Developers][3])
所以别一口气让它“完成所有功能”。让它按下面 4 阶段推进最稳。

## 阶段 1：骨架

让它先完成：

* runtime
* workspace artifact store
* source ingestion
* 3 个 adapter
* raw/extracted/canonical/governance 目录结构

## 阶段 2：知识中间层

让它完成：

* claim model
* entity/relation/event candidates
* parser
* extracted artifact validation

## 阶段 3：建库和治理

让它完成：

* canonical merge
* confidence
* conflicts
* placeholders
* schema candidates
* snapshots/changelog

## 阶段 4：界面和使用

让它完成：

* dashboard
* graph export
* report generation
* basic tests
* sample workspace

---

# 你还可以顺手让它做一个 Skill / 仓库规范包

Codex 现在支持 **Skills**，也就是可复用的指令与资源包，能帮助它更稳定地完成特定开发任务。OpenAI 官方产品页和 changelog 都提到了这一点。([OpenAI][4])
所以你可以再要求它加一个：

* `.codex/skills/mindvault-builder/`
* 或者 `skills/mindvault-builder/`

里面放：

* repo conventions
* architecture reminders
* artifact naming rules
* dashboard quality bar
* schema evolution rules

这会让后面每次你继续让 Codex 干活时，稳定很多。

你可以额外给它这一条：

```text
Also create a reusable Codex skill for this repository called mindvault-builder that captures repository conventions, architecture principles, artifact naming rules, and governance requirements so future Codex tasks can reuse the same standards.
```

---

# 最后一句最重要 **把你的想法变成仓库里的结构化真相。**