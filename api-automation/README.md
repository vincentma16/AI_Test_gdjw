# 接口自动化测试框架

基于 **pytest + requests + Allure** 的接口自动化测试框架。独立可运行，不依赖外部工作台。

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
│   └── logger.py           # 日志
├── config/
│   ├── config.yaml         # 多环境配置
│   └── logging.conf        # 日志格式
├── data/                   # 测试数据
├── testcases/              # 测试用例
└── reports/                # Allure 报告输出
```

## 快速开始

```bash
# 1. 创建虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # Windows PowerShell

# 2. 安装依赖
pip install -r requirements.txt

# 3. 准备环境变量
copy .env.example .env            # 按需修改

# 4. 运行用例（默认 dev 环境）
pytest

# 5. 指定环境
pytest --env=sit

# 6. 生成并查看 Allure 报告
allure serve ./reports/allure-results
```

## 约定

- 用例 ID：`<FEATURE>-API-NNN`，如 `LOGIN-API-001`。
- 数据与代码分离：测试数据放 `data/*.yaml`，用例放 `testcases/test_*.py`。
- 敏感值走 `.env`，禁止硬编码。
- 用例通过 `@allure.feature/story` 标注业务模块与场景，便于追溯。
- 环境通过 `pytest --env=<env>` 切换，默认 `dev`。

## 鉴权

`auth_api` fixture 自动完成「登录拿 token + 注入后续请求」，session 级只登录一次：

```python
def test_example(auth_api):
    # auth_api 已自动注入 accessToken 查询参数与 Authorization 头
    resp = auth_api.get("/auth/account/userInfo")
```

鉴权方式在 `config/config.yaml` 的 `auth` 段配置：`header`（请求头）与 `query_param`（查询参数）可同时启用，按目标接口实际鉴权方式配置。`api` fixture 不带鉴权，用于测试登录等公开接口；`auth_api` 使用独立 session，二者互不污染。
