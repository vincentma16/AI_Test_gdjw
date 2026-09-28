# UI 自动化测试框架

基于 **Playwright + pytest + Allure** 的 UI 自动化测试框架。独立可运行，不依赖外部工作台。
与 `api-automation/` 同级、同分层风格，共用 pytest + Allure 体系。

> 当前为**空框架骨架**：只留一层 `sample` 自检样例，未接入任何被测系统。

## 技术栈

| 组件 | 用途 |
|---|---|
| Playwright | 浏览器自动化（Chromium / Firefox / WebKit，支持 Electron 桌面端） |
| pytest | 测试框架与执行 |
| allure-pytest | 测试报告 |
| pyyaml | 数据驱动（外部数据文件） |
| python-dotenv | 敏感配置走环境变量 |
| pytest-rerunfailures | 失败重跑 |

## 目录结构

```text
ui-automation/
├── pyproject.toml              # 项目与 pytest 配置
├── requirements.txt            # 依赖
├── .env.example                # 敏感配置模板（复制为 .env）
├── conftest.py                 # 全局 fixture：config / browser / context / page + 失败自动截图
├── common/                     # 公共能力
│   ├── config.py               #   配置加载（YAML + 环境变量）
│   ├── browser.py              #   Playwright 浏览器封装
│   ├── assert_util.py          #   断言工具（自动等待）
│   ├── data_helper.py          #   数据文件读取
│   └── logger.py               #   日志
├── pages/                      # Page Object Model
│   ├── base_page.py            #   页面基类
│   └── sample_page.py          #   示例页（自检用，可删）
├── config/
│   ├── config.yaml             #   多环境配置
│   └── logging.conf            #   日志格式
├── data/                       # 测试数据
│   └── sample.yaml             #   自检用例数据（可删）
├── fixtures/                   # 本地 HTML fixture（框架自检用）
│   └── sample.html
├── testcases/                  # 测试用例（按模块分目录）
│   └── sample/                 #   自检样例（可删）
│       └── test_sample.py
└── reports/                    # Allure 结果输出（已 gitignore）
```

> **用例按模块分目录**：`testcases/<模块>/test_*.py`，用例多了也能快速定位。

## 跑起来

本机裸跑：

```bash
pip install -r requirements.txt
playwright install chromium       # 首次下载内置浏览器（用系统浏览器则不必）
cp .env.example .env              # 按注释填被测地址
pytest --env=sit
pytest --env=local                # 跑本地 fixture 自检，不联网
pytest --headed                   # 有头模式调试
pytest -m smoke                   # 只跑冒烟
```

Docker（推荐，见仓库根目录 README）：

```bash
docker compose run --rm ui-tests                  # 默认 local，跑自检样例
docker compose run --rm ui-tests --env=sit        # 指定环境
```

## 自检样例怎么用

`testcases/sample/` + `fixtures/sample.html` 是一套**最小可用样例**，跑本地 HTML 不联网。
它的用途是确认「浏览器 + Page Object + 数据驱动 + Allure」这条链路是否正常，
尤其在容器里——想知道 Docker 环境有没有问题，就跑 `docker compose run --rm ui-tests`。

接入真实系统后可整体删除这三个：`testcases/sample/`、`data/sample.yaml`、
`fixtures/sample.html`，以及 `pages/sample_page.py`。

## 接入一个新系统

1. **配环境**：改 `config/config.yaml` 各环境的 `home_url`，或只在 `.env` 填 `<ENV>_HOME_URL`
2. **建页面对象**：新建 `pages/<模块>/<模块>_page.py`，继承 `BasePage`，
   一个页面元素一个 property，一个业务流程一个方法
3. **写用例**：新建 `testcases/<模块>/test_<模块>.py`，用 `page` fixture，
   调用 Page Object 方法 + `common.assert_util` 断言
4. **需要登录态**：在 conftest 的 `stored_state` fixture 里补一次登录并保存
   `storage_state`（注释里有写法），业务用例复用它

## 约定

- **敏感值不进 git**：账号、token 一律放 `.env`（已 gitignore）
- **登录态不落盘**：`AUTH_STATE_FILE` 默认指向容器 `/tmp`，随容器销毁；
  宿主机默认写到 `reports/.auth_state.json`（已 gitignore）
- **不在用例里裸写选择器**：选择器集中在 Page Object
- **失败自动截图**：conftest 已挂载钩子，失败时截图进 Allure 报告，无需手动处理
