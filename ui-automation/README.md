# UI 自动化测试框架

基于 **Playwright + pytest + Allure** 的 UI 自动化测试框架。独立可运行，不依赖外部工作台。
与 pi-automation/ 同级、同分层风格，共用 pytest + Allure 体系。

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

`	ext
ui-automation/
├── pyproject.toml              # 项目与 pytest 配置
├── requirements.txt            # 依赖
├── .env.example                # 敏感配置模板（复制为 .env）
├── conftest.py                 # 全局 fixture：config / browser / page / auth_state / app_page + 失败自动截图
├── common/                     # 公共能力
│   ├── config.py               #   配置加载（YAML + 环境变量）
│   ├── browser.py              #   Playwright 浏览器封装
│   ├── assert_util.py          #   断言工具（自动等待）
│   └── logger.py               #   日志
├── pages/                      # Page Object Model
│   ├── base_page.py            #   页面基类
│   └── login_page.py           #   登录页（验证码授权登录）
├── config/
│   ├── config.yaml             #   多环境配置
│   └── logging.conf            #   日志格式
├── data/                       # 测试数据
│   └── login.yaml
├── fixtures/                   # 本地 HTML fixture（框架验证用）
├── testcases/                  # 测试用例（按业务模块分目录）
│   └── login/                  #   登录模块
│       └── test_login.py
└── reports/                    # Allure 报告输出 + .auth_state.json 登录态缓存
`

> **用例按模块分目录**：	estcases/<模块>/test_*.py，用例多了也能快速定位。
> 新增模块只需建子目录放用例，pytest 自动递归发现，无需改配置。

## 快速开始

`ash
# 1. 创建虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # Windows PowerShell

# 2. 安装依赖
pip install -r requirements.txt

# 3. 准备账号配置（真实登录用）
copy .env.example .env            # 填入 TEST_PHONE / TEST_CODE

# 4. 运行用例

#    a) local 环境：本地 fixture 框架验证（开箱即跑，不依赖外部系统）
pytest --env=local

#    b) sit 环境：真实登录目标系统
pytest --env=sit

#    c) 只跑某个模块
pytest --env=sit testcases/login/ -s

#    d) 调试时用有头模式（看浏览器操作）
pytest --env=sit --headed -s

# 5. 生成并查看 Allure 报告
allure serve ./reports/allure-results
`

## 环境说明

| 环境 | 说明 | login_url | 需要账号 |
|---|---|---|---|
| local | 本地 HTML fixture，框架验证（默认） | fixture://login.html | 否 |
| dev | 开发环境 | dev.example.com/web/ | 是（.env） |
| sit | 测试环境 | sit.example.com/web/ | 是（.env） |
| uat | 预发环境 | uat.example.com/web/ | 是（.env） |
| prod | 生产环境 | prod.example.com/web/ | 是（.env） |

## 全局 fixture

| fixture | scope | 说明 |
|---|---|---|
| config | session | 加载 config.yaml + .env；--headed 可覆盖 headless |
| rowser_factory | session | Playwright 浏览器工厂（复用系统 Chrome，channel=chrome） |
| page | function | 全新上下文页面（用于登录等） |
| uth_state | session | 登录一次并保存 storage_state 到 
eports/.auth_state.json，会话级复用 |
| pp_page | function | **业务用例专用**：复用登录态的页面，每个用例独立上下文；local 环境自动 skip |

### 失败自动截图

conftest.py 中的 pytest_runtest_makereport 钩子：用例 call 阶段失败时自动截图、
保存失败时 URL 和页面消息（.ant-message-notice-content），全部附加到 Allure 报告，
无需在用例里手动写截图逻辑。

### 有头模式调试

`ash
pytest --env=sit --headed -s           # 全部用例有头模式
pytest --env=sit --headed testcases/login/ -s   # 只跑登录模块
`

真实登录流程：访问 web 入口 -> 重定向 sso 登录页 -> 选择「验证码授权」->
输入手机号 + 验证码 -> 点击登录 -> 跳回 web 工作台。

## 用例说明

| 用例 | 模块 | 环境 | 说明 |
|---|---|---|---|
| 	est_real_login | login | sit+ | 真实验证码授权登录，进入工作台，断言 URL/菜单/token |
| 	est_login[LOGIN-UI-002] | login | local | 本地 fixture 正向登录 |
| 	est_login[LOGIN-UI-003] | login | local | 本地 fixture 空手机号校验 |

## 约定

- 用例 ID：<FEATURE>-UI-NNN，如 LOGIN-UI-001（接口用例为 -API-NNN，前缀区分）。
- 用例目录：	estcases/<模块>/test_*.py，按业务模块分目录管理。
- 数据与代码分离：测试数据放 data/*.yaml，用例放 	estcases/<模块>/test_*.py。
- 敏感值走 .env（账号/token），禁止硬编码；.auth_state.json 已 gitignore。
- Page Object 放 pages/，选择器优先语义定位（get_by_placeholder/get_by_role/get_by_text）。
- 环境通过 pytest --env=<env> 切换，默认 local；--headed 切有头模式。

## 与接口自动化（api-automation）的镜像关系

| api-automation | ui-automation | 说明 |
|---|---|---|
| common/request_handler.py | common/browser.py + pages/ | 请求封装 -> 浏览器 + Page Object |
| conftest.py -> pi fixture | conftest.py -> page/pp_page fixture | 全局句柄注入 |
| config/config.yaml 多环境 | 同结构 | --env 切换 |
| .env 敏感值 | 同款 | 环境变量覆盖 |
| Allure 报告 | 同款 | 报告统一 |
