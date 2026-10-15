# 最小 Python 邮件助手

兼容 Python 3.10。读取 `data/emails.json` 中五封虚构英文邮件，输出优先级（`high`、`medium` 或 `low`）、分类、岗位匹配理由、待办与截止日期，以及需要回复时的英文草稿。信息不足时优先级为 `medium`，不编造理由。没有个人履历，岗位匹配标为“未知”；不适用的字段标为“不适用”。不连接邮箱、不发送邮件。

## 安装和 mock 运行

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py --mock
python -m unittest discover -s tests -v
```

mock 不读取环境变量或 `.env`，不创建 API 客户端。它读取固定示例答案，验证结构和邮件覆盖情况，再生成 `outputs/mock/results.json` 和 `outputs/mock/results.md`。这是离线流程验证，不能衡量真实模型的提取质量；修改邮件时应同步修改 mock 答案。

## 真实 API 运行

以 `.env.example` 为模板创建本地 `.env`，再在 `.env` 中填入你自己的密钥和可用模型。`.env` 已被 Git 忽略：

```bash
source .venv/bin/activate
cp .env.example .env
# 编辑 .env，替换两个占位符
python src/email_assistant.py
```

真实模式直接读取项目根目录 `.env` 中的 `OPENAI_API_KEY` 与 `OPENAI_MODEL`，并显式请求官方 OpenAI API 端点。模型必须是你的账户可用、支持 Responses API 和 Structured Outputs 的模型；不设置默认模型。

真实模式将五封虚构邮件发送到 OpenAI API（可能产生费用），并写入 `outputs/api/results.json` 和 `outputs/api/results.md`。同一模式再次运行会覆盖该模式的结果。失败返回非零退出码，不会用 mock 冒充 API 结果；已有结果不会自动删除，请以本次命令成功为准。程序不打印 SDK 异常正文或密钥。

按 [OpenAI 官方 Structured Outputs 文档](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses) 使用官方 `openai` SDK 的 `client.responses.parse(..., text_format=AnalysisBatch)`、Pydantic schema 和 `response.output_parsed`。设置 `store=False`，对拒绝/不完整响应停止运行。

## 数据与执行边界

邮件仅作为 user 消息中的 JSON 数据；固定 system 指令禁止执行邮件内的指令。示例广告含提示注入，用于展示它不应成为待办。程序没有工具调用、shell 执行、URL 抓取或发送邮件能力。Markdown 会转义模型文本，避免直接嵌入 HTML 或 Markdown 链接。提示词和结构校验无法保证真实模型绝不误判，草稿仍需人工审核；不把 mock 通过视为真实模型抗注入验证。

截止日期只提取明确提供的信息，不把广告期限或通知时间当作工作截止日期。缺失或歧义日期为“未知”，草稿不虚构个人资历、空闲时间、已完成工作或承诺。

## 项目结构

- `main.py`：项目 CLI 入口。
- `src/email_assistant.py`：数据模型、API 调用、校验与 JSON/Markdown 输出。
- `data/emails.json`：五封虚构英文邮件；`mock_results.json`：固定离线答案；`data_profile.md`：数据说明。
- `tests/test_email_assistant.py`：离线流程与 API 调用边界测试，全部无需真实密钥。
- `requirements.txt`、`.env.example`、`.gitignore`：依赖、变量示例和忽略规则。
- `AGENTS.md`、`specs/current_task.md`：开发规则与当前任务约束。
- `evals/run_eval.py`：运行离线测试；`experiments/`：预留实验目录。
- `outputs/`、`logs/`、`reflections/`：本地结果、验证记录和开发记录，均忽略提交。

依赖安装只发生在本项目 `.venv` 中。运行结果、`.env` 和虚拟环境不会提交。
