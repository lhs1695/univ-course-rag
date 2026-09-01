# 004 虚拟环境、语料、图片/视觉

状态：已拍板（2026-09-01）

## 1. 依赖要不要虚拟环境

**要。** Python 后端只用项目内虚拟环境，不把包装到系统 Python。

- 后端：`backend/.venv`（`python -m venv` 或 `uv venv`）。`pip`/`uv pip` 只在激活后装。`.venv` 进 `.gitignore`。
- 前端：`frontend/node_modules`（npm/pnpm），与 Python 无关，不要混进 venv。
- 数据库：Docker 里的 Postgres，不是 pip 依赖。
- 不把硅基流动/DeepSeek 的客户端模型权重装进 venv——它们是 HTTP API。

阶段 0 写清：`AGENTS.md` 里如何创建 venv、如何 `pytest`。不要用 Conda 当默认（除非你本机已经只用 Conda，实施时再说）。

## 2. 现在没有课程资料怎么办

**不挡第一期。** 开发和黄金题用仓库内夹具，真课件答辩前再上传。

阶段 3–4 会放：

- `backend/tests/fixtures/sample.md`：含几句独一无二的「课内原句」
- 一份可解析的短 PDF（可用脚本生成或提交一个无版权问题的自写讲义）
- `backend/tests/fixtures/golden.json`：3 条问句 ↔ 期望命中子串

你自己的课以后作为教师上传即可。不要等齐一门课的完整资料才开阶段 0。

夹具不要用受版权保护的教材扫描件进 git。

## 3. 带图片的资料能不能视觉处理

**能，但第一期不做。** 当前问答模型锁定文本版 `deepseek-v4-flash`，入库只抽 **可选中的文字**（PDF 文本层、Markdown）。

图片里的内容会表现为失败分类里的「库里没有」：扫描件、纯截图 PPT、公式图、板书照片——PyMuPDF 往往抽不到字。教师侧应看到解析成功但正文很短，而不是假装已索引图画。

以后若要做，有两条，都单开下一份 plan，不塞进阶段 0–10：

| 路径 | 做法 | 代价 |
| --- | --- | --- |
| OCR / 版面 | MinerU、PaddleOCR、本地 DeepSeek-OCR 等，把页变成 Markdown 再走现有切分 | 重、常要 GPU；适合扫描讲义 |
| 视觉模型 | 页转 PNG，调用 `deepseek-v4-flash-vision-exp`（实验，只吃图不吃 PDF）生成文字描述再入库，或问答时临时带图 | 页数 × 费用；注入面更大；和文本 embedding 不是同一条路 |

第一期禁止：问答时把整页图塞给 vision、用 vision 代替检索、默认改用 vision 模型做纯文本问答。

演示建议优先选 **可选中文字的 PDF/MD**（Word 导出的文本 PDF），不要第一份演示资料就是全图课件。
