# When Consensus Lies — AI-Driven Execution Playbook
**面向：单人研究者 + Copilot Premium（多模型无限 token）+ 多 agent / 多 session 并行**
**目标：把"欠定规格下多 Agent 冗余的沉默失效"从 idea report 落地为可投稿的代码实验**

> 阅读顺序：先读 §0 心智模型 → §1 分工 → §2 模型路由 → §3 仓库结构 → §4 分阶段计划 → §5 验证策略（最重要）→ §6 风险表 → §7 你每周要做的事。
> prose 用中文，所有 **repo 结构 / 接口 / 指标名 / agent prompt 模板用英文**（直接喂给 agent）。

---

## 0. 心智模型（先建立这个，否则会翻车）

- **你在用会 sycophancy、会犯相关性错误、会 silent failure 的 AI，去造一个研究这些失败的系统。** 你论文的每一个失败模式都会出现在你的施工队里。
- **解药就写在你论文里**：`executable gold`（单测过不过、确定数值）+ `provenance separation`（构造/被测/评判用不同模型家族）。把它们同时用作**科学设计**和**质检手段**。
- **你的新身份 = 施工队长 + 首席怀疑者 + 集成者。** Agent 产出代码，你产出**判断**：这个数是真的还是 bug？这个效应是真的还是伪影？
- **黄金法则**：任何"AI 写的代码 / AI 打的标签 / AI 得的结论"，都必须有一个**不依赖同一个 AI 的独立验证**（确定性测试 > 跨家族模型复核 > 人工抽检）。**绝不让写代码的模型自己批准自己的代码**——那正是你论文里的 verifier-accomplice 失效。

---

## 1. AI 能全包 vs 必须你把关（分工表）

| 工作 | 谁做 | 自动化度 | 你的检查点 |
|---|---|---|---|
| 仓库脚手架 / API 封装 / schema / 日志 / 缓存 | AI | 95% | 跑通 + 读一遍接口 |
| Benchmark 构造（删除式歧义 + 可执行 gold） | AI | 85% | **抽检 10 题**：歧义真吗？gold 对吗？ |
| Agent 跑批（single/SC/MAD/verifier/diverse） | AI | 95% | 抽看几条 trace |
| 指标实现（convergent-delusion / ρ / A_maj / ECE） | AI 写，**你验** | 70% | **金标单测必须你签字**（§5） |
| 检测器（Hypothesis Surfacing） | AI | 85% | 定义"报警"判据、看 FP 率 |
| 模拟用户研究（simulated decision-maker） | AI | 90% | 确认表述不越界成"人类心理" |
| 统计（mixed-effects logistic + bootstrap） | AI | 90% | 预注册 H1/H2；防 p-hack |
| 画图（相图 / heatmap） | AI | 95% | 看图是否讲对了故事 |
| 表征分析（activation patching，需 GPU） | AI 写代码 + 你租 GPU | 50% | ML 工程细节、可推 v2 |
| **判断"真效应 vs 伪影" / provenance 设计 / claim / 叙事 / venue** | **你** | **0%（不可外包）** | 全程 |

---

## 2. 模型路由：把"无限多模型"变成方法论资产

你有跨家族无限 token —— 这恰好**免费满足 §7.7 的 provenance separation**。按角色固定不同家族：

```yaml
# common/config.yaml  —— 角色 × 模型家族，跨家族是默认，不是可选
roles:
  constructor:   # 造 benchmark / latent spec / 删除式歧义
    family: openai        # e.g. GPT-5 class
  tested_agents: # 被测的多 agent / 多 session（核心实验对象）
    homogeneous: [anthropic]              # 同家族 ×5 测 shared-prior ρ baseline
    heterogeneous: [openai, anthropic, google, qwen, deepseek]
    reasoning: [o3-mini, deepseek-r1]     # 一等条件（测 §8.2 两区制）
  judge:         # 只在无法用可执行 gold 时才用；且跨家族
    family: google
  code_reviewer: # 复核 AI 写的代码 —— 必须 ≠ 写代码的家族
    family: anthropic   # 若代码由 openai 写，则用 anthropic 复核
seeds: {global: 20260713}
```

**要点**：`constructor ≠ tested ≠ judge ≠ code_reviewer` 家族。若 cross-family 构造下 `convergent-delusion` 依然显著，就当场堵死"你的 ρ 是构造模型伪影"这一最强质疑。

---

## 3. 仓库结构 & 接口（让并行 agent 不打架）

**并行 agent 靠"文件 + schema"通信，不靠共享内存。** 每个 session 只读/写自己那层，中间产物是 JSONL。

```
consensus-lies/
  common/
    llm.py          # 统一多provider客户端；按 role 取模型；带缓存/重试/成本日志
    schema.py       # 见下方 dataclasses —— 全项目的接口契约
    config.yaml     # §2 的路由
  bench/            # Direction A
    templates/      # code_spec / data_analysis / policy_qa 三域模板
    build.py        # 删除式歧义生成器：full spec → 删 1/2/3 类 requirement
    gold/           # 可执行 checker（单测 / 确定数值）—— 不是 LLM 判
    data/*.jsonl    # 生成的题目
  harness/
    run.py          # 跑 single/SC/MAD/verifier/interpretation-diverse
    label.py        # L_i ∈ I：用可执行信号（报错类型/traceback/数值）聚类
    metrics.py      # convergent-delusion, marginal ρ(phi), A_maj, ECE
  detector/         # Direction B（Hypothesis Surfacing）
    branch.py       # forced interpretation branching
    signals.py      # divergence / aleatoric（Input Clarification Ensembling 基线）
    surface.py      # latent-assumption surfacer + suspicion score
  sim_users/        # Direction C
    personas.py     # 注入 automation bias 的 simulated decision-maker
    study.py        # conditions: baseline / lightweight-warning / divergence-surfacing
  analysis/
    stats.py        # mixed-effects logistic regression + bootstrap CI
    figures.py      # ρ–ambiguity 相图、silent-failure heatmap
  paper/            # AI 起草的各节
  tests/            # 流水线自身的单测（§5 金标）—— 最重要的目录
```

```python
# common/schema.py  —— 接口契约（所有 agent 遵守；改这里要通知所有 session）
@dataclass
class Interpretation:      # I_0 = 真实隐藏意图；I_1..I_m = 先验偏见解读；I_perp = 退化/噪声
    id: str               # "I0" | "I1" | ... | "I_perp"
    is_target: bool
    gold_check: str       # 指向 gold/ 下的可执行 checker（函数名或测试文件）
@dataclass
class Task:
    id: str; domain: str  # code_spec | data_analysis | policy_qa
    prompt: str           # 欠定 prompt（已删除 k 类 requirement）
    latent_spec: str      # 完整规格（评测脚本可见、被测 agent 不可见）
    interpretations: list # List[Interpretation]，含各自 hidden gold
    ambiguity_level: int  # 1/2/3 = 删了几类 requirement
    key_questions: list   # 关键澄清问题（golden）
@dataclass
class AgentRun:
    task_id: str; config: str      # single|sc|mad|verifier|diverse
    model_role: str; model_id: str
    output: str; label: str        # L_i ∈ {I0,I1,...,I_perp}，由 label.py 用可执行信号判定
    verbalized_conf: float; logit_conf: float | None
```

---

## 4. 分阶段执行计划

> 记号：`[S#]` = 一个可独立开的 session/agent；`⟂` = 可并行；`→` = 依赖。
> 每阶段给：目标 / 输入 / 输出 / 验证 / 你的检查点。

### Phase 0 — 脚手架 `[S0]`（必须最先，阻塞其余）
- **目标**：`common/` 全套 + `tests/` 骨架 + 空的模块接口 + CI（本地 pytest）。
- **输出**：可 import 的包、mock 数据能跑通端到端"空管道"。
- **验证**：`pytest` 绿；一条 mock Task 能走完 run→label→metrics。
- **你**：读一遍 `schema.py`，锁定接口（之后改动代价大）。

### Phase 1 — Benchmark（Direction A）`[S1a code]⟂[S1b data]⟂[S1c policy]`（Phase 0 后并行）
- **目标**：每域 100–150 题，含 latent spec / 2–4 interpretation / **可执行 gold** / 关键澄清问题。
- **关键设计**：
  - **删除式歧义**：先让 `constructor` 写**完整** human-style spec，再**删掉** 1/2/3 类 requirement 得低/中/高歧义（model-agnostic 结构性缺失，不是"生成一个歧义 prompt"）。
  - **gold 必须可执行**：code 域=单测；data 域=确定数值/DataFrame 断言;policy 域**弱化**或只用人工 rubric（别让它拖垮无 GT 的严谨性）。
- **验证**：每题的每个 interpretation 都能被 `gold/` 里的 checker 确定性判定；`constructor` 家族 ≠ 后续 `tested` 家族。
- **你的检查点（硬）**：**先做 50 题 MVP，亲手抽检 10 题**——歧义是真的吗？gold 标对了吗？澄清问题问到点子上了吗？**这一步不过，后面全是沙上建塔。**

### Phase 2 — Harness + 指标（Direction A 测量）`[S2]`（Phase 0 后即可起，用 stub 数据；真数据等 Phase 1）
- **目标**：跑 single / SC(k=5,10) / homogeneous-MAD / heterogeneous-MAD / verifier / interpretation-diverse；产出 `AgentRun`。
- **`label.py`**：用**可执行信号**把每个输出映射到 `L_i ∈ I`（报错类型/traceback/数值聚类），**不用 LLM-judge**。
- **`metrics.py`**：`convergent-delusion / false-consensus rate`（主）、`marginal ρ phi`（次）、`A_maj`、`ECE`、confidence–accuracy slope。
- **验证**：见 §5 金标单测。
- **你**：确认"主指标是 convergent-delusion，不是 binary ρ"这件事在代码里**真的**是这样。

### Phase 3 — 检测器（Direction B / Hypothesis Surfacing）`[S3]`（接口定后起）
- **目标**：`branch.py` 强制枚举解读 → `signals.py` 算 interpretation-branch 输出发散 / aleatoric（**以 Input Clarification Ensembling 为基线**）→ `surface.py` 输出"latent-assumption 告警"。
- **定位（关键，别写错）**：**不判对错**，而是"挖出共识依赖的未证实假设 I_k 并打印告警"。判据 = 分支是否发散，**不是** consensus strength。
- **头条指标**：`false-surfacing rate on unambiguous controls`（无歧义控制集上的误报率）——直接回答审稿人"真共识时会不会乱报"。
- **你**：定"报警阈值"；看无歧义集上它是否闭嘴。

### Phase 4 — 表征分析（§8.5，ACL 内核，**需 GPU**）`[S4]`（独立，可推 v2）
- **目标**：在**单一开源模型多 session**（先用 Llama-3.1-8B 省 GPU）做 logit-lens / activation patching，证明"共享表征扰动 = 跨 session 错误相关的根因"。
- **边界（硬伤 #1 的教训）**：**只在同一开源模型内做**；闭源/异构一律只测行为层。别试图跨 tokenizer 做 patching。
- **资源**：租 1 张云 GPU（8B 单卡够）。**若暂时无 GPU：整块推到第二篇，第一篇不受影响。**
- **你**：ML 工程细节、判断 patching 结果是否可信。

### Phase 5 — 模拟用户（Direction C）`[S5]`（Phase 2 后）
- **目标**：`personas.py` 造注入 automation-bias 的 **simulated decision-maker**；`study.py` 三条件（baseline / 轻量警告 / divergence-surfacing）测 appropriate reliance（corrective/detrimental override）。
- **红线**：结论一律写成"降低**模拟决策者**接受错误共识的比例"，**绝不**写成人类心理结论;并主动引 Lost in Simulation 自曝局限。
- **你**：确认 framing 不越界。

### Phase 6 — 统计 & 图 `[S6]`（有数据后）
- `stats.py`：`correctness ~ ρ + ambiguity + method + model + interactions`，随机效应按 task/model，bootstrap CI。
- `figures.py`：ρ–ambiguity 相图（预注册的 crossover）、method × ambiguity 的 silent-failure heatmap。
- **你**：**预注册 H1/H2 和指标 → 再跑全量**（防止 AI 迎合你、把效应"找"出来）。

### Phase 7 — 写作 `[S7]`（持续）
- AI 按结果起草各节；**你拥有 claim / 叙事 / venue framing**。ACL 版顶起语言触发器+表征;CHI 版顶起 surfacing+reliance。

---

## 5. 验证策略：防止"造沉默失效检测器的过程本身沉默失效"（**全篇最重要**）

1. **指标金标单测（不可跳过）**：手工构造**已知答案**的极小合成样本，喂给 `metrics.py`，断言它吐出**正确的** convergent-delusion 值。
   ```python
   # tests/test_metrics_golden.py —— 若这个错了，下游一切都是 silent failure
   def test_convergent_vs_scattered():
       # 5 个 agent 都错在同一个 I1 → 高 convergent-delusion
       assert false_consensus_rate(labels=["I1"]*5, target="I0") == 1.0
       # 5 个各错各的（I1,I2,I3,I_perp,I_perp）→ 低 convergent-delusion，即使 binary ρ 高
       r = false_consensus_rate(labels=["I1","I2","I3","I_perp","I_perp"], target="I0")
       assert r < 0.5
   ```
2. **跨家族代码复核**：每个 agent 交付的代码，用**另一个模型家族**的 `code_reviewer` 过一遍（写代码的模型不许自己批自己）。
3. **确定性优先**：能用可执行 gold 就别用 LLM-judge；必须用 judge 时跨家族 + 人工抽检一致性。
4. **可复现**：全局 seed、prompt 版本化、API 结果缓存（同输入不重复烧 token、结果可回放）。
5. **预注册**：跑全量前，把 H1/H2、主指标、相图预期写死（git commit），**之后不许改指标定义**——挡住"AI 迎合式找效应"。
6. **对抗性抽检**：你定期挑 5 条系统"报对了"的样本，**主动找反例**：它是真挖出了隐性假设，还是碰巧？

---

## 6. 风险登记表（AI 驱动执行特有）

| 风险 | 触发 | 缓解 |
|---|---|---|
| **Meta 沉默失效**：多编码 agent 同一隐蔽 bug | 同家族 agent 共享先验 | 指标金标单测 + 跨家族复核（§5.1/5.2） |
| **构造循环**：ρ 是构造模型伪影 | constructor 与 tested 同家族 | provenance separation + cross-family 对照（§2） |
| **判定循环**：LLM-judge 与被测共享盲区 | 用 LLM 打 interpretation 标签 | 可执行 gold 打标签；judge 仅备用 + 抽检 |
| **迎合式发现**：AI"帮你"找到不存在的效应 | 无预注册、指标可事后改 | 预注册 H1/H2 + 锁定指标 + 对抗性抽检（§5.5/5.6） |
| **GPU 缺口**：§8.5 跑不动 | Copilot 不给 GPU | 第一篇纯 API；表征分析用 8B + 云 GPU 或推 v2 |
| **接口漂移**：并行 agent 改坏 schema | 多 session 同时改 `schema.py` | schema 冻结 + 改动需通知；文件级接口 |
| **reasoning 模型削弱效应** | SOTA 上 ρ 变小 | 设为一等条件；H1（真外部知识欠定）/H2（可推导歧义=边界）皆可发 |

---

## 7. 你（人）每周实际要做的事

- [ ] **Week 1**：跑 Phase 0；亲手锁 `schema.py`;定 §2 模型路由。
- [ ] **Week 1–2（MVP 闸门）**：50 题 benchmark + 指标金标单测 + 一次小规模跑批。**看一件事：convergent-delusion 到底测不测得出来？** 测得出→放大;测不出→先别 scale，回去改设计。
- [ ] **每周**：抽检 10 条（gold 对吗 / 标签对吗 / 报警对吗）;挑 5 条主动找反例。
- [ ] **放大前**：git commit 预注册（H1/H2 + 指标 + 相图预期）。
- [ ] **出相图后**：戴上"首席怀疑者"帽子——**这是真效应还是伪影？** 换个 domain / 换 constructor 家族，看它还在不在。
- [ ] **写作**：claim 收窄到系统级;ACL / CHI / NeurIPS 分装;你拍板叙事。

---

### 一句话
**可行度高**：纯 API 那条主线（benchmark + 测量 + 检测器 + 模拟用户 + 第一篇论文）你和 AI 施工队能在数周内跑通;唯一要真金白银的是表征分析那张 GPU（可推 v2）。**成败不在算力、不在 token，而在你能不能当好那个"不被 AI 共识带偏"的首席怀疑者**——这也正是你论文的主题。
