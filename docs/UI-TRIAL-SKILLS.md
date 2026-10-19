# UI Trial Skills 用法（工作区安装，不全局）

更新：2026-10-19。技能装在仓库内，供 Codex（及本机 Cursor）发现；**不要**用 `--global` 装到用户主目录。

## 安装位置

| 内容 | 路径 |
|------|------|
| Codex 项目技能根 | `.agents/skills/` |
| Impeccable hooks | `.codex/hooks.json`（项目级） |
| Notion DESIGN.md | `tools/ui-trial-skills/design-md/notion/DESIGN.md` |
| 共用 Brief | `tools/ui-trial-skills/SHARED-BRIEF.md` |
| Taste lock | `skills-lock.json` |

Impeccable 引擎二进制（约 20MB）在 `.agents/skills/impeccable/scripts/bin/`，**已 gitignore**；缺失时在项目根再跑：

```powershell
npx --yes impeccable install --scope=project --providers=codex -y
```

## 五套是什么

1. **frontend-design**（Anthropic）— `.agents/skills/frontend-design/`  
   纯设计 brief skill；无 CLI。提示里写 `$frontend-design` 或「按 frontend-design skill」。

2. **design-md-notion**（输入物，非 skill）— Notion `DESIGN.md`  
   提示里要求「严格吸收 `tools/ui-trial-skills/design-md/notion/DESIGN.md` 的语言与 token，场景是课程问答，不是 Notion 官网」。

3. **ui-ux-pro-max** — `.agents/skills/ui-ux-pro-max/`（另有 companion：`design` / `design-system` / `ui-styling` 等，同属 Pro Max 安装）  
   可先跑设计系统脚本再实现。示例：

```powershell
python .agents/skills/ui-ux-pro-max/scripts/search.py --design-system --query "university course knowledge QA student app"
```

4. **design-taste-frontend**（Taste）— `.agents/skills/design-taste-frontend/`  
   抽方向 + 浏览器自检。允许外链图。目标是**学生知识产品 app 屏**，不是营销落地页。提示写 `$design-taste-frontend`。

5. **impeccable** — `.agents/skills/impeccable/` + hooks  
   用 shape / craft / polish / critique；**起点不是现状截图**。Windows 启动器：`.agents/skills/impeccable/scripts/impeccable.cmd`。

## 在 Codex 提示里如何引用

- 长 prompt 放文件，经 stdin：`Get-Content .\prompt.txt -Raw -Encoding utf8 | codex exec -m gpt-6.1-sol -c model_reasoning_effort=medium -s workspace-write -C <worktree> -`
- Brief：先贴/引用 `tools/ui-trial-skills/SHARED-BRIEF.md`
- Skill：显式 `$skill-name`，并说明「已安装在本仓库 `.agents/skills/`」
- **禁止**把现有学生端 UI 当设计参考

## 分支与 worktree 约定

- 分支：`ui-trial/<slug>`，slug ∈ `frontend-design` | `design-md-notion` | `pro-max` | `taste` | `impeccable`
- Worktree 建议：`D:\workspace\univ-course-rag-wt\ui-trial-<slug>`
- 不 merge main、不 push；验收后该分支本地 commit
- 主仓脏文件 `新开题资料.md` 不要动

## 重装（仍保持项目 scope）

```powershell
# Anthropic frontend-design
python $env:USERPROFILE\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo anthropics/skills --path skills/frontend-design --dest "$PWD\.agents\skills"

# Notion DESIGN.md
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/notion/DESIGN.md" -OutFile "tools\ui-trial-skills\design-md\notion\DESIGN.md"

# Pro Max（勿加 --global）
npx --yes ui-ux-pro-max-cli init --ai codex

# Taste（项目级 copy）
npx --yes skills add https://github.com/Leonxlnx/taste-skill --skill "design-taste-frontend" -a codex -y --copy

# Impeccable（项目级，含 hooks）
npx --yes impeccable install --scope=project --providers=codex -y
```

## 注意

- **勿全局安装**（Pro Max 的 `-g`、skills 的 `-g`、impeccable `--global` 都不要用）。
- Taste 需要本机 Chrome/Edge；Impeccable hooks 会在 Edit/Write 后跑检测，可接受。
- 五版对比时每版附 `DESIGN-NOTES.md`。
