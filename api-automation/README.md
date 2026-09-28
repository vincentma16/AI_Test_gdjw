# 接口自动化测试框架

基于 **pytest + requests + Allure** 的接口自动化测试框架。独立可运行，不依赖外部工作台。

> 当前为**空框架骨架**：框架能力齐备，未接入任何被测系统。接入步骤见文末。

## 技术栈

| 组件 | 用途 |
|---|---|
| pytest | 测试框架与执行 |
| requests | HTTP 客户端 |
| allure-pytest | 测试报告 |
| pyyaml | 数据驱动（外部数据文件） |
| jsonpath-ng / jsonschema | 响应提取与断言 |
| python-dotenv | 敏感配置走环境变量 |

## 目录结构

```text
api-automation/
├── pyproject.toml          # 项目与 pytest 配置
├── requirements.txt        # 依赖
├── .env.example            # 敏感配置模板（复制为 .env）
├── conftest.py             # 全局 fixture
├── common/                 # 公共能力
│   ├── config.py           # 配置加载（YAML + 环境变量）
│   ├── request_handler.py  # 请求封装
│   ├── assert_util.py      # 断言工具
│   ├── extractor.py        # 响应提取
│   ├── throttle.py         # 请求节流（防频控）
│   └── logger.py           # 日志
├── apis/                   # 接口定义层，当前为空
├── config/
│   ├── config.yaml         # 多环境配置（含占位 TODO）
│   └── logging.conf        # 日志配置
├── data/                   # 用例数据（yaml），当前为空
├── testcases/              # 用例（pytest），当前为空
└── reports/                # 运行结果，已 gitignore
```

## 跑起来

本机裸跑：

```bash
pip install -r requirements.txt
cp .env.example .env        # 按注释填 base_url 与账号
pytest --env=sit            # 或 dev / uat / prod
pytest -m smoke             # 只跑冒烟
```

Docker（推荐，见仓库根目录 README）：

```bash
docker compose run --rm api-tests --env=sit
```

`testcases/` 为空时 pytest 会提示"未收集到用例"（退出码 5），属正常现象。

## 接入一个新系统

1. **配环境**：改 `config/config.yaml` 的 `base_url`（多域名系统在 `services` 登记），
   或只在 `.env` 里填 `<ENV>_BASE_URL` 覆盖
2. **建接口层**：新建 `apis/<模块>/<模块>_api.py`，一个接口一个函数，返回原始 `Response`
3. **写用例**：新建 `testcases/<模块>/test_<模块>.py`，只调用 apis 层函数，用 fixture `api` 发请求
4. **需要鉴权**：在 `config/config.yaml` 的 `auth` 段按注释补充配置，参考
   `common/auth.py` 写一个登录函数，并在 conftest 做成 session 级 fixture

工程内自带一套可直接复制的写法示范：`apis/example/`、`testcases/example/`
（未接入真实环境时自动 skip，不影响 CI）。

## 约定

- **敏感值不进 git**：账号、token、密钥一律写 `${VAR}` 占位，真实值放 `.env`（已 gitignore）
- **断言用 common.assert_util**：`assert_status_code` / `assert_jsonpath`，不要在用例里裸 `assert`
- **取响应字段用 common.extractor**：`extract_by_jsonpath`
- **用例之间不互相依赖**：数据自行准备，顺序无关
- 更细的工程纪律见 [`../docs/接口自动化框架规则.md`](../docs/接口自动化框架规则.md)
