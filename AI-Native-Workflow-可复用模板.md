# AI-Native 工作流 · When Consensus Lies 项目版

> **用途**：这是 **When Consensus Lies**（欠定规格下多 Agent 冗余的沉默失效）项目的 AI 协作执行工作流。它把通用的 **Spec-Driven Development + Agent Execution + 独立审计 Gate** 方法论，和本项目 [`AI-Execution-Plan.md`](AI-Execution-Plan.md) 里的 **provenance separation（跨家族模型路由）+ executable gold（可执行金标）+ 指标金标单测 + 预注册** 绑定在一起。
> **核心对偶**：你在用会 sycophancy、会犯相关性错误、会 silent failure 的 AI，去造一个**研究这些失败**的系统——所以论文里的每一个失败模式都会出现在你的施工队里。解药就写在论文里（executable gold + provenance separation），这套工作流把它们**同时用作科学设计和质检手段**。
> **使用前**：先确认 §0 的项目常量；之后所有 issue 都照 §12 的 checklist 跑一遍，质量可复现。若要把本工作流迁到别的项目，把 §0 常量换回占位符即可复用。

---

## 0. 项目常量（本项目已适配）

全文引用同名符号；换项目时把这些值换成你自己的。

| 符号 | 含义 | 本项目值 |
|---|---|---|
| `<REPO>` | 仓库名 | `When-Consensus-Lies` |
| `<REPO_PATH>` | 主 checkout 的绝对路径 | `C:\Users\v-elzhang\Desktop\MyFolder\When Consensus Lies` |
| `<OWNER>` | GitHub owner | `EloiseJulia` |
| `<DEFAULT_BRANCH>` | 主干分支 | `main` |
| `<WORKTREE_ROOT>` | worktree 存放目录 | `<REPO_PATH>/.worktrees` |
| `<AGENT_CLI>` | agent CLI（Copilot Premium，多模型无限 token） | `copilot` |
| `<MODEL>` | 复杂任务默认模型 | 最强长上下文模型（见 §2 角色路由） |
| `<TMUX_SESSION>` | 长驻 agent session 名 | `consensus-t` |
| `<COMPUTE>` | 执行机器 | 本地纯 API 主线；表征分析 §4 用 1× 云 GPU（可推 v2） |
| `<PROJECT_BOARD>` | 项目看板（可选） | 无 |
| `<SPEC_DIR>` | spec 存放目录 | `paper/specs/` |
| `<PLAN_DIR>` | plan 存放目录 | `paper/plans/` |
| `<RESEARCH_DIR>` | 调研报告目录 | `paper/research/` |
| `<REPORT_STORE>` | 重型交付物（图/大文件，git 外） | `~/reports/consensus-lies/` |
| `<COMMIT_TRAILER>` | commit 署名 trailer | `Co-authored-by: copilot <copilot@users.noreply.github.com>` |
| `<BUILD_CMD>` | 环境/包可导入验证 | `pip install -e . && python -c "import common"` |
| `<RUN_CMD>` | 跑真实产物（端到端一条 mock Task） | `python -m harness.run --config sc --smoke` |
| `<TEST_CMD>` | 全量测试（含指标金标单测） | `pytest` |

> 本项目主线是纯 API，无需服务器/GPU；把「长驻 agent」当作「本地终端里跑 agent」即可。唯一需要真金白银的是表征分析（§8.5 / Phase 4）的那张 GPU，可推 v2。

---

## 1. 一句话定位与铁律

**Spec-Driven Development + Agent Execution + 独立审计 Gate + Provenance Separation。**

质量不是靠「用了多少 agent」堆出来的，而是靠**验证机制**守出来的。本项目尤其致命：**造沉默失效检测器的过程本身可能沉默失效**——你的施工队（多编码 agent）会像论文里的被测系统一样，共享先验、互相背书、高置信地一致犯错。所以通用五条铁律之上，本项目再加两条**来自论文本身的**铁律：

| # | 铁律 | 教训 / 出处 |
|---|---|---|
| 1 | **验证真实产物，不只看测试绿** | 关键配置被误删、整条命令失效却通过几十个测试——只有 build + 跑真产物才抓得到 |
| 2 | **独立敌对审计 > 自审** | 自审容易判「都是 pre-existing / PASS」；独立新 agent 常挖出真 bug。**绝不让写代码的模型自己批准自己的代码**——那正是论文里的 verifier-accomplice 失效 |
| 3 | **并行只对「独立切片」，依赖链必须串行** | 硬并行依赖链 = 冲突 + 跨切片一致性 bug 更隐蔽 |
| 4 | **共享基础设施改动标注交 owner，永不自 merge** | env/build/infra/`schema.py` 是 owner 地盘；agent 只测明白、标注醒目，merge 是人的判断 |
| 5 | **知道何时停手** | 一道彻底审计 0 新问题后继续审 = 边际收益趋零的焦虑循环 |
| 6 | **Provenance separation（论文级铁律）** | `constructor ≠ tested ≠ judge ≠ code_reviewer` 必须跨模型家族（§2）。任何「AI 写的代码 / AI 打的标签 / AI 得的结论」都要有**不依赖同一个 AI 的独立验证**：确定性测试 > 跨家族模型复核 > 人工抽检 |
| 7 | **Executable gold + 预注册（论文级铁律）** | 能用可执行 gold（单测/确定数值）就绝不用 LLM-judge；主指标（convergent-delusion）先写**金标单测**、H1/H2 先 git commit 预注册，**之后不许改指标定义**——挡住 AI 迎合式「找效应」 |

外加一条贯穿铁律：**「标注边界 ≠ 修 bug」**——低风险且真超范围的可文档化为「已知边界」；但**会静默丢数据 / 破坏正确性**的（如 interpretation 标签维度缺失、把「各错各的」误算成 convergent-delusion）**必须修**。

> **元层警告**：本项目里「独立敌对审计」和「指标金标单测」不只是工程质检——它们**就是论文的核心方法**（provenance separation + executable gold）。做对了工作流 = 验证了论文主张；做砸了 = 你的检测器自己沉默失效。

---

## 2. 三层文档体系（全部 git 追踪）

| 层 | 位置 | 作用 | 谁拥有 |
|---|---|---|---|
| **执行规范** | `AGENTS.md`（或本文件） | 定义 HOW：worktree 隔离 / PR 流程 / 分支命名 / commit 规范 / auto-merge 策略 / 看板更新 | 人（项目主人） |
| **设计规格** | `<SPEC_DIR>` | 每个 issue 一个 spec：Objective → Non-goals → Surface → Design → Acceptance Criteria → Slice Plan | 人 或 Agent（讨论后写） |
| **执行脚本** | `<PLAN_DIR>` | 每个 slice 一个 plan：架构图 + 数据流 + 分步骤 checklist + 测试步骤 + push 点 | Agent（执行中生成） |
| **调研报告**（可选） | `<RESEARCH_DIR>` | SOTA 调研 / 选型 / license 审查 | Research Agent |

**Spec 与 Plan 都可以由 Agent 写**，但必须**经你确认后 commit**。区别：
- **单 issue 交互模式**：讨论后 Agent 写 spec（人机协作，spec 质量取决于讨论深度）。
- **多 issue 非交互模式**：Agent 自主写 spec，所以 **issue body 质量决定 spec 质量**。

---

## 2.5 模型路由：把「无限多模型」变成方法论资产（provenance separation）

Copilot Premium 跨家族无限 token —— 这恰好**免费满足论文的 provenance separation**。按角色固定不同家族，让「造 benchmark 的」「被测的」「打分的」「复核代码的」永不同源。**这不是可选优化，而是铁律 6**。

```yaml
# common/config.yaml —— 角色 × 模型家族，跨家族是默认，不是可选
roles:
  constructor:   # 造 benchmark / latent spec / 删除式歧义
    family: openai
  tested_agents: # 被测的多 agent / 多 session（核心实验对象）
    homogeneous: [anthropic]                        # 同家族 ×5 测 shared-prior ρ baseline
    heterogeneous: [openai, anthropic, google, qwen, deepseek]
    reasoning: [o3-mini, deepseek-r1]               # 一等条件（测两区制 H1/H2）
  judge:         # 仅在无法用可执行 gold 时才用；且跨家族
    family: google
  code_reviewer: # 复核 AI 写的代码 —— 必须 ≠ 写代码的家族
    family: anthropic
seeds: {global: 20260713}
```

**双重用途**：
- **科学设计**：若 cross-family 构造下 `convergent-delusion` 依然显著，就当场堵死「你的 ρ 是构造模型伪影」这一最强质疑。
- **质检手段**：每个 slice 的 **Audit Agent（§4）用 `code_reviewer` 家族**，且 ≠ 写该 slice 代码的家族——把「独立敌对审计」落到模型家族层面。

> 详细分工表 / 仓库结构 / schema / 分阶段计划见本项目 [`AI-Execution-Plan.md`](AI-Execution-Plan.md)。本工作流负责「怎么执行 + 怎么把关」，执行计划负责「做什么 + 做成什么样」。

---

## 3. 全生命周期总览

```
① 调研(可选) → ② Issue 准备 → ③ 拆分+依赖分析 → ④ 每 slice 执行
                                                        ↓
        ⑦ 交付给你(不 merge) ← ⑥ 整体 PR-Audit ← ⑤ 独立敌对审计(每 slice)
                    ↓
        你决定 → mark ready → 交 owner review + merge
```

**不可跳过的 gate：**
- 每个 slice 完 → ④自检 + ⑤独立敌对审计
- 全部 slice 完 → ⑥整体 PR-Audit（build 真产物 + 全量测试 + diff 卫生）
- 交付前 → ⑦先发你，不 ready、不 merge

**本项目把 `AI-Execution-Plan.md` 的 Phase 映射成一串 issue/slice：**

| 执行计划 Phase | 对应 issue/slice | 本工作流的关键 gate |
|---|---|---|
| Phase 0 脚手架 `common/` + `tests/` | 阻塞其余，最先做 | 你亲手锁 `schema.py`（冻结接口）；mock Task 端到端跑通 |
| Phase 1 Benchmark（code⟂data⟂policy） | 3 个**独立切片 → 并行** | 先 50 题 MVP，**你抽检 10 题**（歧义真吗 / gold 对吗）；constructor 家族 ≠ tested |
| Phase 2 Harness + 指标 | 依赖 Phase 0，**串行**接真数据 | **指标金标单测你签字**；确认主指标是 convergent-delusion 而非 binary ρ |
| Phase 3 检测器（Hypothesis Surfacing） | schema 定后起 | 无歧义控制集上的 false-surfacing rate；定报警阈值 |
| Phase 4 表征分析（需 GPU） | 独立，可推 v2 | 只在同一开源模型内做 patching；ML 细节你判断可信度 |
| Phase 5 模拟用户 | 依赖 Phase 2 | framing 红线：只写「模拟决策者」，绝不写人类心理结论 |
| Phase 6 统计 & 图 | 有数据后 | **预注册 H1/H2 + 锁指标 → 再跑全量**（防迎合式找效应） |
| Phase 7 写作 | 持续 | claim / 叙事 / venue 归你 |

> 依赖链（Phase 0→2→5→6）**串行**；独立切片（Phase 1 三域、Phase 4）**并行**——严格执行铁律 3。

---

## 4. 角色总表

| 角色 | 何时用 | 位置 | 关键约束 |
|---|---|---|---|
| **你（人）** | 全程 | 本地 / 浏览器 | 唯一强制触发点；判断题的最终裁决者；merge 决定 |
| **Research Agent**（可选） | 技术路线/选型不明 | 独立 session，doc-only | 输出 research md，直接 commit `<DEFAULT_BRANCH>`；不写代码 |
| **Manager Agent** | 多 slice / 多 issue | 长驻 session（`<COMPUTE>`） | **先画依赖图**；只有它碰 git/topic；永不碰主 checkout、永不 merge 进主干 |
| **Sub-Agent（执行）** | 每个 slice | 独立 worktree + session | 只在自己 worktree；spec→plan→执行；自检 gate；**用某一固定家族写代码，记录在 PR body** |
| **Audit Agent（独立敌对）** | 每 slice 完 + 整体 | **全新 session、无上下文** | 目标是挑毛病；不信任何既有结论；只报不修；**必须用 ≠ 写代码家族的 `code_reviewer` 模型**（provenance separation） |

**两种规模：**
- **单 issue（日常默认）**：不需要 Manager。你在 worktree 里起一个交互 session，讨论 → spec → plan → 执行 → review。
- **多 issue 并行（高级）**：才需要 Manager Agent 编排多个 Sub-Agent。

---

## 阶段 0 · 调研（可选，技术路线不明时）

**何时需要**：选模型 / 定算法路线 / 审 license / 比 SOTA。

**启动模板：**
```bash
<AGENT_CLI> --name research-<topic> --model <MODEL> \
  -i 'Research SOTA for <topic> (issue #<N>). Compare: <候选 A/B/C>.
For each: accuracy/benchmark, LICENSE (permissive vs restrictive), input/output
format, runtime cost, integration fit with our <现有框架>.
Read AGENTS.md §<相关章节> first.
Output <RESEARCH_DIR>/<date>-<topic>.md with a comparison TABLE + a clear
recommendation + rationale + honest caveats.
Commit directly to <DEFAULT_BRANCH> (doc-only). Trailer: <COMMIT_TRAILER>'
```

**关键**：让它输出**对比表 + 推荐 + 诚实 caveat**（尤其 license：可商用 vs 仅研究用途）。

**能做 / 不能做**：能搜文献/仓库/官方文档、比公开 benchmark、审 license、读本仓库理解集成约束；**不能**跑重型 benchmark（那要执行 agent）、不能保证结论绝对准（你最终判断）。

---

## 阶段 1 · Issue 准备

| 情况 | 做法 |
|---|---|
| 已有合适 open issue | 确认 body 够详细 |
| body 太简单 | 先补 body（acceptance criteria + 相关文件/模块 + Non-goals + parent epic 链接） |
| 全新工作 | 创建 issue，写清 body |

**「body 够详细」=**：① 说清做什么（acceptance criteria）② 提到相关文件/模块/现有模式 ③ parent epic 链接 ④ Non-goals（告诉 agent 什么不要动）。

> 单 issue 交互模式下 body 可以不完整（讨论时补）；**Manager 非交互模式下 body 必须完整**（没有讨论机会）。

**（可选）登记看板 `<PROJECT_BOARD>`**：设 Status=In progress，填 Agent 字段（谁在干、worktree 路径、session 引用），方便你随时知道谁在做什么。

---

## 阶段 2 · 拆分 + 依赖分析（最容易出错的一步）

**先画依赖图，再决定并行还是串行。**

```
对每个候选 slice 问：它读/写哪些文件、哪些模块、哪些数据结构？
  ├─ 两个 slice 改同一批文件 / 后者依赖前者产物  → 串行（依赖链）
  └─ 完全独立（不同文件、无产物依赖）           → 并行（独立切片）
```

- **依赖链**（如：建结构 → 扩展 → 改上游接口）：**串行**。硬并行会冲突，且跨切片的一致性 bug 更隐蔽。
- **独立切片**（如多个互不相关的 bug fix）：**并行**，各自独立 worktree；重型任务受资源上限约束（如一张 GPU 一个 agent）。

**产物**：Manager 写 spec + per-slice plan，标明每个 slice 的**依赖关系 + 并行/串行编排**，commit 到 topic 分支。

---

## 阶段 3 · 每个 Slice 执行

### 3.1 脚手架
```bash
git -C <REPO_PATH> worktree add <WORKTREE_ROOT>/<name> -b feature/<N>-<name> <DEFAULT_BRANCH>
cd <WORKTREE_ROOT>/<name>
git commit --allow-empty -m "bootstrap #<N>

<COMMIT_TRAILER>"                    # 空分支开不了 PR，先引导提交
git push -u origin feature/<N>-<name>
# 开 draft PR（用你的 PR 工具），base=<DEFAULT_BRANCH>，body 写 "WIP. Refs #<N>."
```
> **早开 draft PR** 拿 CI + owner 可见性；**但不 mark ready、不 merge**。

### 3.2 执行流程（spec → plan → code）
1. 贴**开场 prompt**（§使用方法 A）→ agent 读代码 + 问 ≤5 个澄清问题
2. 你答问 → agent 写 **spec** → 你确认
3. agent 写 **plan** → 你确认
4. agent 执行：写代码 → 跑测试 → 自检 → push（累积在 draft PR）

**你在关口把关**：spec 看 Acceptance Criteria + Non-goals + 拆分；plan 看是否覆盖验收 + 有测试步骤 + 有 push 点。**判断题（选哪个方案、要不要扩范围）由你拍板，不让 agent 闷头猜。**

### 3.3 自检 gate（agent mark ready 之前必须自答）
- 目标产物真的能跑（不只是 import / 单测）？
- 幂等？重跑收敛（全局 seed + API 缓存，同输入不重复烧 token）？
- **身份维度完整**（`AgentRun` 主键含 task_id × config × model_role × model_id × seed → 避免不同配置静默撞车）？
- **指标定义没被偷改**（convergent-delusion 仍是「共识在同一个错误 I_k 上」，不是 binary ρ）？
- 无依赖 / 空输入优雅降级？
- diff 只动该动的，无残留 debug / 无误删 / 没碰冻结的 `schema.py`？

---

## 阶段 4 · 独立敌对审计（质量皇冠，每 slice 完做）

**必须是全新 session、无上下文、抱着「我一定要挑出毛病」的心态**——写代码的 agent 审自己有偏见。

审计 prompt（§使用方法 D）核心：
- 「你没写这份代码，把 PR 描述和一切既有结论当**不可信**，从源码重新验证」；**审计模型家族 ≠ 写代码家族**
- **先读代码找逻辑 bug**（身份维度缺失 / 静默丢行 / 坐标/数值缩放 / 注入 / 多步写原子性 / 旁路校验），再跑验证
- **本项目专属逻辑 bug 类**（务必逐条查）：
  - `label.py` 把「各错各的 I1/I2/I3」误算成 convergent-delusion（应低，却报高）？
  - 用了 LLM-judge 打 interpretation 标签，而非可执行 gold 信号？
  - `metrics.py` 主指标偷偷退化成 binary ρ？
  - constructor 与 tested 家族串了（provenance 泄漏 → ρ 变构造伪影）？
  - `gold/` checker 其实不确定（依赖模型输出而非单测/确定数值）？
- **验证真实产物**（build + run，不只单测）
- **独立归因测试失败**（clean `<DEFAULT_BRANCH>` 对比复现，禁止「猜 pre-existing」）
- 输出 **ranked findings**（BLOCKER/MAJOR/MINOR/UNVERIFIED）+ 明确 verdict；**只报不修**

**审计回来后分诊：**
- 我们代码 + 修法清楚 → 修
- 共享 infra / `schema.py` / owner 说过别动 → **不擅改，文档 + follow-up issue，交 owner**
- 会静默丢数据 / 破坏正确性（含指标误算、provenance 泄漏）→ **必须修**（哪怕它自称「边界」）

---

## 阶段 5 · 整体 PR-Audit（全部 slice 完，合并前一次总检）

| 面 | 查什么 |
|---|---|
| **A 真实产物** | `<BUILD_CMD>` + `<RUN_CMD>` 跑通；其它产物消费者没被连累 |
| **B 幂等/共存** | 重跑 0 新副作用；多配置共存不撞；超限报错不静默丢；`--force`/重置干净 |
| **C 结构/接口** | 统一视图/接口单值不 fan-out；约束真强制；下游消费者不被破坏 |
| **D 正确性** | 数值/坐标 round-trip；无依赖优雅 skip；空输入不崩 |
| **E 全量回归** | 跑**整个**测试套（不只子集）；每个失败 clean-main 独立归因 |
| **F diff 卫生** | 逐行看配置/依赖文件，防「误删」；无 throwaway/debug 残留；worktree 干净 |
| **G review 闭环** | 所有 review thread 回复 + 真修（不只回复）；lint |
| **H 指标金标** | `tests/test_metrics_golden.py` 绿：全错在同一 I1 → convergent-delusion=1.0；各错各的 → <0.5（即使 binary ρ 高）|
| **I provenance** | `config.yaml` 里 constructor / tested / judge / code_reviewer 家族两两不同；gold 全可执行 |
| **J 预注册** | 若本次要 scale 全量：H1/H2 + 主指标 + 相图预期已 git commit 冻结，且事后未改指标定义 |

**产出**：PASS/FAIL 表 + ranked findings。确认的 bug 修，判断题标注交你/owner。

---

## 阶段 6 · 交付（先发你，不 merge）

- **先发你**：报告 / `git diff <DEFAULT_BRANCH>...feature/<N>` / PASS-FAIL 表。**不 mark ready、不 merge。**
- 你审完 → 才 mark PR ready → 交 owner review + merge。
- 共享 infra 改动在 PR body/commit 里**单独标注 "needs your sign-off"**。
- **（可选）图文报告**：结果 + 可视化 + 指标 + **诚实的精度验证**。
  - 别 overclaim：无 ground truth 时说清「是合理性/一致性/稳定性验证，不是误差 vs 真值」；要真误差就用**带 GT 的标定数据集**，并写明域差距。
  - 重型产物（图/大文件）放 `<REPORT_STORE>`（git 外），只把摘要发 PR。

---

## 7. 贯穿原则 · Gate · 陷阱速查

| 类别 | 要点 |
|---|---|
| **只读主 checkout** | agent 永不改 `<REPO_PATH>` 主 checkout；只 `git worktree add` / 只读 inspect（`git log/status/diff`） |
| **禁止在主 checkout 上 test-checkout** | 临时 checkout 某 commit 也不行（会留 detached HEAD）；要看某 commit 用临时 worktree |
| **PR-first 但不 merge** | 早开 draft 拿 CI/可见性；ready/merge 是人的动作 |
| **commit trailer** | 每个 commit 带 `<COMMIT_TRAILER>` |
| **空分支陷阱** | 0-commit 开不了 PR → 先 `git commit --allow-empty` 引导提交 |
| **删 worktree 陷阱** | 先 `cd <REPO_PATH>` 再 `git worktree remove`，否则后续 shell 找不到 cwd 报 ENOENT |
| **身份维度陷阱** | 主键/identity 要包含「所有影响输出的维度」（strategy/size/config），否则静默撞车 |
| **验证真实产物** | 测试绿 ≠ 产物能用；build + 跑真产物 |
| **别猜 pre-existing** | 任何「预先存在的失败」结论必须 clean-main 复现坐实 |
| **何时停** | 一道彻底审计 0 新问题 → 交付；别无限自证 |
| **squash 进 topic 的隐患** | slice squash-merge 进 topic 会压平历史，topic→main 可能报 dirty；优先 `--merge` 或 squash 后立即 `git merge --no-ff origin/<DEFAULT_BRANCH>` 补桥 |
| **provenance 泄漏（本项目）** | constructor/tested/judge/code_reviewer 一旦同家族 → ρ 与结论都可能是伪影；`config.yaml` 是接口契约，改动交 owner |
| **迎合式找效应（本项目）** | 无预注册、指标事后可改 → AI「帮你」找出不存在的效应；scale 前 git commit 冻结 H1/H2 + 指标 |
| **judge 循环（本项目）** | 用 LLM-judge 打 interpretation 标签 = 与被测共享盲区；能用可执行 gold 就绝不用 judge |

---

## 8. 分支命名约定

| 类型 | 格式 | 示例 |
|---|---|---|
| 新功能 | `feature/<short-name>` | `feature/123-add-cache` |
| Bug fix | `fix/<short-name>` | `fix/456-null-deref` |
| 重构 | `refactor/<short-name>` | `refactor/config-loader` |
| 实验 | `experiment/<short-name>` | `experiment/new-algo` |
| 多 slice 伞状 | `topic/<name>` | `topic/123-search-rework` |
| sub-agent slice | `slice/<topic>-S<N>` | `slice/123-S1-index` |

**Topic 模式**（多 sub-agent 并行）：
```
topic/xxx（伞状，Manager 维护）
  ├── slice/xxx-S1（Sub-Agent 1，auto-merge 进 topic）
  ├── slice/xxx-S2（Sub-Agent 2，auto-merge 进 topic）
  └── topic → <DEFAULT_BRANCH>（人工 approve 一次）
```

**auto-merge 策略**：slice → topic 可由 Manager 验证后 auto-merge；topic → 主干**永远需要人 approve**，即使 CI 全绿。

---

## 9. Agent 运维（监控 + 故障处理）

**监控**：
- 长驻 session 直接看（`tmux attach-session -t <TMUX_SESSION>`）
- 若 CLI 支持远程可见性，用浏览器监控 session（SSH 断开不影响）
- 看 PR 状态（draft = 工作中；non-draft = 自检通过等 review）
- 看看板 Status

**卡住 / 需要回应**：Agent 会在 blocking question 前 stop（不瞎猜）。用 `tmux send-keys` 或远程 session 页面回应。

**崩溃恢复**：找到 session ID → 用 CLI 的 resume 能力从断点继续，已 push 的 commits 不重做。

**完成后清理**（避免 worktree 堆积）：
```bash
cd <REPO_PATH>                                          # 先离开 worktree！
git worktree remove --force <WORKTREE_ROOT>/<name>
git branch -D feature/<N>-<name>                        # PR 已 merge 时
# 关掉对应长驻 pane
```

---

## 10. 明确不存在的东西（避免误解）

| 不存在 | 说明 |
|---|---|
| Goal → Spec 全自动 | issue 仍需人判断业务价值后创建 |
| 独立「Planner Agent」角色 | Manager 兼任规划职能 |
| 持久化向量记忆 / 知识图谱 | 仅有文件式 handoff 记忆（`docs/<date>-handoff.md`，git 追踪，session 间接力）|
| Agent 自主 approve 自己的 PR 进主干 | 平台限制 + 本规范明确禁止 |

---

## 11. 使用方法 · Prompt 模板全集

### A. Sub-Agent 开场 prompt（单 slice 执行）
```
You are working on issue #<N> (slice <k>), branch feature/<N>-<name>, draft PR
#<PR>. Full flow: read context, ask ≤5 questions, write a SHORT spec, wait for
my confirm, write a plan, wait for my confirm, THEN execute.

Read ALL before asking:
- issue #<N> (+ parent epic)
- AGENTS.md §<相关章节>
- <相关现有代码文件 + 1-2 个同类已完成实现作模板>

Scope/guardrails: <要做什么 + 明确 NOT touch>.
Constraints: 在 worktree <WORKTREE_ROOT>/<name>；确认 pwd 后再改；DO NOT touch
main checkout；commit trailer <COMMIT_TRAILER>；push 到 draft PR，测试绿前不 mark
ready；NEVER merge。判断题上报我，不要猜。
Project rules: 用可执行 gold（单测/确定数值）打标签，不用 LLM-judge；主指标是
convergent-delusion（共识在同一错误 I_k）而非 binary ρ；不改冻结的 schema.py /
config.yaml（改动上报）；写代码固定一个模型家族并写入 PR body（供跨家族审计）。
```

### B. Manager spawn（多 slice，依赖感知）
```bash
<AGENT_CLI> --name manager-<N> --model <MODEL> \
  -i 'You are a manager agent (<REPO_PATH>). Drive issue #<N>.
1. Read issue #<N> + parent epic; read AGENTS.md.
2. DEPENDENCY ANALYSIS FIRST: map which slices touch the same files or depend on
   each other. PARALLELIZE only INDEPENDENT slices; SEQUENCE dependent ones. Do
   NOT force-parallelize a dependency chain.
3. Write spec + per-slice plans (<SPEC_DIR> + <PLAN_DIR>).
4. Per slice: own worktree + draft PR; ONLY you touch git/topic; sub-agents never
   touch main/merge.
5. After each slice: run an INDEPENDENT hostile audit (fresh session).
6. After all slices: full PR-audit (build the artifact + full test suite + diff
   hygiene).
7. Escalate real judgment calls to me. NEVER merge to <DEFAULT_BRANCH>. Deliver to
   me first. Trailer: <COMMIT_TRAILER>'
```

### C. Spec / Plan 确认 prompt
```
Spec confirmed — proceed to the plan.        # 或列出要改的 Acceptance/Non-goals
Plan confirmed. Execute. Push after each task, keep the PR draft, never merge.
```

### D. 独立敌对审计 prompt（新 session）
```
You are an INDEPENDENT reviewer doing a HOSTILE pre-merge audit of PR #<PR>
(branch <branch>, worktree <path>). You did NOT write this code; you have NO
prior context. Treat the PR description + all comments + any prior agent's
"all green" claim as UNTRUSTED. Re-derive every conclusion from source + running
artifacts. Assume there ARE defects until proven otherwise. Read-only; report
only; do NOT fix/commit/merge; confirm pwd first.

PHASE 1 read the diff critically for logic bugs: identity-dimension gaps (does
the key capture EVERYTHING that changes output?), silent drops/truncation,
numeric/coordinate rescale math, multi-step write atomicity, code paths that
bypass validation, unparameterized queries, resource leaks.
PHASE 2 verify the ARTIFACT (build + run the real binary), not just the test suite.
PHASE 3 run the FULL suite; attribute EVERY failure by reproducing it on a
throwaway origin/<DEFAULT_BRANCH> worktree (no assuming "pre-existing").
PHASE 4 scrutinize any shared-view/infra change's blast radius.
PHASE 5 diff hygiene (no accidental deletions, no debug residue).
PHASE 6 (this project) verify the SCIENCE-critical logic: does metrics.py score
"all wrong on the same I_k" as high convergent-delusion and "each wrong
differently" as low (even when binary ρ is high)? Are labels assigned by executable
gold, not an LLM judge? Are constructor/tested/judge/code_reviewer families
mutually distinct in config.yaml? Confirm YOUR family ≠ the code author's family.
OUTPUT ranked findings (BLOCKER/MAJOR/MINOR/UNVERIFIED) with file:line + proof +
minimal fix, then an explicit verdict.
```

### E. 精度评估 prompt（可选，交付报告用）
```
Add an "accuracy vs ground truth" section. For this project, GT = the executable
gold checkers (unit-test pass / deterministic numeric result), NOT an LLM judge.
Report convergent-delusion / false-consensus rate, marginal ρ(phi) as a secondary
theory bridge only, A_maj, ECE. Be HONEST: for policy_qa with no executable GT,
say clearly it is a rubric-based / consistency check, not error-vs-truth; simulated
decision-maker results are stated as effects on a SIMULATED user, never as human
psychology (cite Lost in Simulation caveat). Pre-register H1/H2 + metrics (git
commit) BEFORE full-scale runs. Outputs stay local (git-out), no commits, no merge.
```

### F. Agent CLI 常用 flag（按你的 CLI 对应替换）
| 意图 | 说明 |
|---|---|
| 禁止自动升级 | 防升级中断长任务 |
| 放开权限 | 非交互运行必须（仅用于受信任 prompt） |
| 远程可见 | 浏览器可监控 session，SSH 断开不影响 |
| 命名 session | 标签在 session 列表 / 看板可见 |
| 选模型 / 高强度 | 复杂任务用最强长上下文模型 + 高 effort |

---

## 12. 一页 Checklist（每个 issue 跑一遍）

```
调研(可选)
  □ 对比表 + 推荐 + license/可商用性 + 诚实 caveat

Issue 准备
  □ body 够详细(验收/文件/Non-goals/epic)  □ (可选)登记看板

拆分
  □ 画了依赖图  □ 独立→并行, 依赖→串行(没硬并行一条链)

每 slice 执行
  □ worktree + draft PR(不 ready)  □ spec 你确认  □ plan 你确认
  □ 自检: 真产物能跑 / 幂等 / 身份维度全 / 优雅降级 / diff 干净

独立敌对审计(每 slice)
  □ 新 session 无上下文  □ 先读代码找逻辑 bug  □ 验真产物  □ 失败 clean-main 归因
  □ 审计家族 ≠ 写代码家族  □ ranked findings + verdict

整体 PR-Audit
  □ A 真产物 build+run  □ B 幂等/共存  □ C 结构/接口  □ D 正确性
  □ E 全量测试+归因  □ F diff 卫生  □ G review 闭环
  □ H 指标金标单测绿  □ I provenance 四角色跨家族  □ J (scale 前)预注册已冻结

交付
  □ 先发你(不 merge)  □ 共享 infra/schema/config 标注 sign-off  □ (可选)图文+精度报告
  □ 你确认 → mark ready → 交 owner merge

铁律自检
  □ 验证了真实产物(不只测试)  □ 上了独立敌对审计  □ 并行只对独立切片
  □ 共享 infra 交 owner  □ 该修的修了(没拿"边界"糊弄)  □ 知道何时停
  □ provenance separation(四角色跨家族)  □ executable gold 而非 LLM-judge
  □ 主指标是 convergent-delusion 非 binary ρ  □ scale 前预注册 H1/H2 + 锁指标
```

---

> **一句话收尾**：这套流程的价值不在「用了多少 agent」，而在**每个交付物都过了「独立敌对审计 + 验证真实产物 + 跨家族 provenance」三道 gate，且每一处未验证/有意为之的边界都写清楚了**。对 **When Consensus Lies** 这个项目而言，这套工作流不只是质检手段——它就是论文主张的实践验证：**你能否当好那个「不被 AI 共识带偏」的首席怀疑者，本身就是诺验。** 若要把本工作流迁到别的项目，把 §0 常量换回占位符 + 去掉 §2.5/铁律 6-7 的项目专属部分即可复用。
