# 接口自动化框架模板

> 即开即用的接口自动化测试脚手架。复制本目录即可启动新项目，**不含任何业务数据**。
> 所有约定见 [框架规则.md](框架规则.md)。

## 技术栈

pytest + requests + Allure（Python 3.9+）

## 目录结构

```
├── common/        通用层（原样复用，勿改）
├── config/        多环境配置 + 日志（接入时填 config.yaml）
├── apis/          接口定义层（按业务模块分子目录）
├── testcases/     用例层（按业务模块分子目录）
├── data/          数据层（按业务模块分子目录）
├── reports/       报告（运行产物，按 月/日/序号 归档）
├── conftest.py    三句柄 fixture（api / auth_api / biz_api）
├── pyproject.toml pytest 配置
├── run_all.ps1    一键运行 + 报告 + 归档
└── 框架规则.md     所有约定
```

## 新项目接入（8 步）

1. 复制本目录 -> 改名为新项目（如 `xxx-api-test`）
2. 填 `config/config.yaml`：base_url、services、auth（登录端点/账号/鉴权链路）
3. 建 `.env`：复制 `.env.example` -> `.env`，填敏感值（如有）
4. 建 `apis/{模块}/{模块}_api.py`：从后端/前端代码提取接口，写路径常量 + 函数
5. 建 `data/{模块}/{接口}.yaml`（数据驱动用例）或场景链直接在用例生成
6. 写 `testcases/{模块}/test_*.py`：只调用 apis 函数 + 断言
7. 运行 `.\run_all.ps1`，报告按 `reports/<月>月/<日>/<序号>/` 归档
8. 删除 `example/` 示例（或改造为首业务模块）

## 核心原则

- **用例只调用 apis 函数，不拼 URL、不存放参数**
- 接口路径/默认参数集中在 `apis/`，变更只改一处
- 鉴权全由 `config.yaml` 驱动，改鉴权方式只改配置不改代码

## 运行

```powershell
# 全量运行 + 报告 + 归档
.\run_all.ps1

# 单模块
.\.venv\Scripts\python.exe -m pytest testcases/{模块}/ -v

# 查看报告（file:// 会 500，用本地 HTTP 服务）
python -m http.server 8089 --directory reports\allure-report
# 然后打开 reports\open_report.html
```