# Docker 一键部署方案

> 7 项决策已于 2026-09-24 全部确认（见 §10），本文件即实施蓝图。

## 1. 目标与验收标准

| 目标 | 说明 |
|---|---|
| 一键运行 | 宿主机不需要装 Python / allure / playwright，`docker compose` 一条命令跑起来 |
| 环境一致 | 依赖版本固化在镜像里，换机器结果一致 |
| 结果可追溯 | 每次运行的结果可归档、可回溯，不会被下一次覆盖丢失 |
| 产物可控 | 明确每类产物落在哪、是否入库、怎么清理 |
| 敏感不外泄 | 账号 token、登录态不落到仓库，也不长期滞留宿主机 |

## 2. 已核实的现状约束

| 项 | 现状 | 对方案的影响 |
|---|---|---|
| Docker | Desktop 29.8.0 / Compose v5.5.1，x86_64 | 支持 profile、`env_file.required=false`、Compose 内 build |
| 本机已有镜像 | `python:3.12-slim`(190MB)、`nginx:alpine`(103MB)、`maven:3.9-eclipse-temurin-17`(763MB)、`node:22-slim`，以及若干 `docker.m.daocloud.io` 镜像源副本 | 优先复用本地镜像，避免在线拉取失败 |
| Playwright | 只有 `mcr.azure.cn/playwright/java` (**4.63GB**，Java 版)，没有 Python 版 | UI 侧不直接复用它，见 §4.2 |
| allure CLI | **宿主机未安装**；宿主机有 Java 21 | HTML 报告必须靠容器生成，见 §4.3 |
| 网络 | 走代理 `http://127.0.0.1:3067` | 容器内 `127.0.0.1` 是容器自己，必须换成 `host.docker.internal:3067` 或加 `extra_hosts: host-gateway` |
| API 工程 | pytest + requests + allure-pytest；`pythonpath=["."]`；选项 `--env=dev/uat/sit/prod`（无 local） | 容器内 `PYTHONPATH=/app` |
| UI 工程 | pytest + playwright + allure-pytest；选项 `--env=local/dev/sit/uat/prod`，另有 `--headed` | `local` 跑本地 fixture，不联网 → 适合验证容器是否可用 |
| 日志 | 两个工程 `logging.conf` 只有 console handler，**不落日志文件** | 日志 = 容器 stdout，`docker compose logs` 查看，随容器删除消失 |

## 3. 服务拓扑

一次性任务型容器（run-to-complete），不是常驻服务：

```text
docker compose build                              → 构建 3 个镜像（report 需加 --profile report）
docker compose run --rm api-tests                 → 跑接口用例 → 产出 allure-results
docker compose run --rm ui-tests                  → 跑 UI 用例   → 产出 allure-results
docker compose --profile report up -d report-site → 生成 HTML + 起报告站（localhost:8080）
```

> 报告命令必须显式带上服务名 `report-site`。Compose 的 profile 是"额外启用"而不是
> "只启用这些"，直接 `up -d` 会把没有 profile 的测试服务一起拉起来跑一遍测试。

- `api-tests`：pytest + requests，轻量
- `ui-tests`：pytest + playwright + chromium
- `allure-report`：allure HTML 生成 + nginx 托管，归入 `report` profile，默认不参与 `up`，避免每次都拉起

## 4. 镜像选型与取舍

### 4.1 api-tests（无争议）
`FROM python:3.12-slim`（**本机已有，零拉取**）+ `pip install -r requirements.txt`。
pip 走代理 + 可选 `--index-url` 镜像源（做成 build ARG，默认走官方源 + 代理）。

### 4.2 ui-tests ✅ 已定：B. 官方 playwright python 镜像

| 方案 | 做法 | 优点 | 风险 |
|---|---|---|---|
| A. slim + 自装浏览器 | `python:3.12-slim` + `pip install playwright` + `playwright install chromium` | 复用本地 190MB 镜像 | 浏览器下载环节可能失败 |
| **B（已选）** 官方镜像 | `mcr.microsoft.com/playwright/python:v1.52.0` | 开箱即用，浏览器与依赖版本对齐，不用自己装 | 需新拉 1GB+ |

**拉取通道的坑已排除**：本机 `mcr.azure.cn` 是 `mcr.microsoft.com` 的镜像站——两个源对
`playwright/python:v1.52.0` 返回**完全相同的 manifest digest**（`sha256:3997517e…`）。
因此 Dockerfile 里 `FROM mcr.microsoft.com/playwright/python:v1.52.0`，宿主机再建一个同名 alias
tag 指向 `mcr.azure.cn` 的镜像即可零拉取；换机器时走官方源，语义不变。

版本号写死为 ARG（`PLAYWRIGHT_VERSION`），升级时改一处。

### 4.3 allure 报告 ✅ 已定：a. 自制 CLI 镜像 + nginx

宿主机没有 allure CLI，容器内必须有能产出 HTML 的地方：

| 方案 | 做法 | 优点 | 风险 |
|---|---|---|---|
| **a（已选）** 自制 allure-cli 镜像 | `FROM maven:3.9-eclipse-temurin-17`（**本机已有 763MB，自带 JDK 17**）+ 下载 allure-commandline tarball | 复用本地镜像，JDK 现成无需 apt；版本 ARG 固定 | 需从 GitHub Releases 下载 tarball，走代理一般可行 |
| b. 第三方服务镜像 | `frankescobar/allure-docker-service` | 自带 UI、历史趋势 | 需新拉约 1GB，自动触发策略有坑 |
| c. 不生成 HTML | 只看 allure-results JSON | 最轻 | 结果不可读，等于没有报告 |

落地细节（已核实）：

- Allure 版本 **2.46.1**（GitHub Releases 当前 latest），资源 `allure-2.46.1.tgz`
- 下载 URL：`https://github.com/allure-framework/allure2/releases/download/${ALLURE_VERSION}/allure-${ALLURE_VERSION}.tgz`
- 解到 `/opt/allure`，`PATH` 加 `/opt/allure/bin`；JDK 由 maven 镜像提供，无需 apt 装任何东西
- 报告容器把 `allure-results` 生成静态 HTML 到宿主机目录，再用本地 `nginx:alpine`（103MB，已在本地）托管
- `docker compose --profile report up -d` 后浏览器打开 `http://localhost:8080`

## 5. 产物（资产）处理 —— 本次重点

### 5.1 产物清单与落位

| 产物 | 容器内位置 | 是否挂到宿主机 | 入 git 吗 | 保留策略 |
|---|---|---|---|---|
| Allure 原始结果（JSON + 附件） | `/app/reports/allure-results` | 是 → `<工程>/reports/allure-results` | 否（`allure-results/` 已忽略） | 每次 `--clean-alluredir` 覆盖，只留最新；历史靠归档 |
| HTML 报告 | 由 allure 容器生成 | 是 → `<工程>/reports/allure-report` | 否（`allure-report/` 已忽略） | 同上，最新一份 |
| 失败截图 | 已内联进 allure 附件 | 不单独落盘 | 否（`reports/*.png` 已忽略，作兜底） | 跟随结果一起走 |
| **登录态 `.auth_state.json`** | `/app/reports/.auth_state.json` | **默认不挂到宿主机**（容器内 `/tmp` 或匿名卷） | 否（已忽略） | 随容器销毁；含真实 token，不该长期滞留磁盘 |
| 日志 | stdout | 否 | 否 | `docker compose logs` 查看，容器删即消失 |
| `__pycache__` / `.pytest_cache` | 容器内 | 否（运行模式不挂载源码） | 否 | 随容器销毁，不污染工作区 |

### 5.2 历史归档 ✅ 已定：顶层 `runs/YYYY-MM-DD/<seq>/`

| 方案 | 结构 | 优点 | 缺点 |
|---|---|---|---|
| 沿用旧约定 | `<工程>/reports/09月/0924/001/` | 与现有脚本一致 | 分散在两个工程；中文目录名在容器挂载时有编码隐患 |
| **（已选）** 顶层 `runs/` | `runs/2026-09-24/001/api/...`、`runs/2026-09-24/001/ui/...`，附 `summary.json`（时间、退出码、环境、命令） | 集中管理、日期可排序、一条命令清理、出问题易定位 | 需给 `.gitignore` 加一条 `runs/` |

序号当日递增三位补零（`001`/`002`…），避免覆盖。旧 `run_all.ps1` 的归档逻辑保持不变（见 §9）。

### 5.3 清理策略

```text
docker compose down -v          # 删容器与匿名卷（含登录态）
rm -rf runs/                    # 清全部历史归档
docker image prune              # 清理悬空镜像
```

归档默认全留、手动清理；也可以加保留最近 N 次的开关（按需）。

## 6. 项目资产（需求 / 评审 / 测试用例）放哪

> **已确认（2026-09-24）**：需求本体、需求相关资料、评审过程、测试用例，全部保存在本地（仓库目录内），Docker 只读挂载，不进 Docker 卷、不拷进镜像。

要把**两类用例**分开，它们不是一个东西：

| | 人工/设计态用例 | 自动化用例 |
|---|---|---|
| 代表文件 | `projects/<项目>/features/<功能>/04-test-design/test-cases.md` | `api-automation|ui-automation/testcases/<模块>/*.md` |
| 谁写 | 人 + AI 智能体，在 IDE 里 | 人 + AI 智能体，在 IDE 里 |
| 谁消费 | 人（阅读、评审、追溯） | pytest（脚本读取执行） |
| 与代码关系 | 独立存在，代码不读它 | **与自动化脚本同生共死**，脚本要读它 |
| 归宿 | 仓库 + 本地，容器只读挂载 | 仓库 + 容器（随代码一起进镜像/挂载） |

**判定规则：一个用例要不要进 Docker / 进 GitHub，只问一句——自动化脚本运行时需不需要读它？需要就跟着代码走，不需要就留在 `projects/` 里只做只读挂载。**

先把两类东西彻底分开，它们是不同性质的文件：

| | 创作层资产 | 执行层产物 |
|---|---|---|
| 内容 | 需求原文、补充确认、评审记录、冻结需求、测试用例 | Allure 结果、HTML 报告、截图、登录态 |
| 谁产生 | 人和 AI 智能体，在宿主机 IDE 里写 | pytest，在容器里跑出来 |
| 价值 | 长期资产，是项目的知识沉淀 | 一次性消耗品，看完就没用 |
| 归宿 | **进 git，跟随仓库** | **不进 git，可随时清** |

### 6.1 结论：Docker 不接管创作层

`projects/` 继续留在仓库里、留在宿主机上，**不放进 Docker 卷，不拷进镜像**。理由：

1. 评审和用例设计是智能体在 IDE 里读写的，这个环节本身不在容器里发生，Docker 无从接管；
2. git 是它唯一的版本管理，一旦放进 named volume 就脱离版本控制，且 `docker compose down -v` 会直接删掉——等于把资产挂在一个可被清理命令抹掉的地方；
3. 拷进镜像更是冻结在构建时刻，改一个字就要重新构建。

### 6.2 但容器需要"看见"它：只读挂载

当某个容器任务需要引用项目资产时（例如按 `04-test-design/test-cases.md` 校验用例格式、渲染静态文档站、生成某个项目的专属上下文），统一走**只读 bind mount**：

```text
projects/          → /assets/projects:ro    只读，容器不能改
templates/         → /assets/templates:ro   只读
schemas/           → /assets/schemas:ro     只读
config/            → /assets/config:ro      只读
```

挂在 `/assets/` 而不是 `/app/projects`，是为了不让资产目录混进工程目录里——工程目录是
pytest 的工作目录，往里塞只读挂载既没必要，也容易在 `cp -a` 归档时把资产一起拷走。

只读是关键：避免容器内进程（或root 属主）意外改写你的需求原文和评审结论。

### 6.3 生命周期目录与读写角色

沿用现有约定，容器视角下每一层的处理：

| 目录 | 内容 | 谁写 | 容器能否看到 | 备注 |
|---|---|---|---|---|
| `01-source/requirement.md` | 需求原文 | 人/产品 | 只读 | markdown，入库 |
| `01-source/confirmations/` | 答复原文 | 人 | 只读 | 必须保留原始答复，作为判定依据 |
| `01-source/attachments/` | 原型图、Excel、PDF | 人 | 只读 | **见 6.4，不建议直接入库** |
| `02-analysis/requirement-review.md` | 评审记录 | AI 智能体 | 只读 | 顶部当前结论 + 底部追加轮次 |
| `03-frozen-requirement.md` | 冻结需求 | AI 智能体 | 只读 | 评审通过才算数 |
| `04-test-design/test-cases.md` | 测试用例 | AI 智能体 | 只读 | 用例执行在容器里，用例本身在仓库里 |
| `project.yaml` / `knowledge/` | 项目配置与业务知识 | 人 | 只读 | 含私有仓库地址等，注意脱敏 |

一句话概括：**资产在仓库里被人和 AI 维护，在执行时被容器只读消费，容器只负责往 `reports/`、`runs/` 里吐结果。**

### 6.4 原始材料（大文件 / 敏感件）单独放

需求材料常见的原型图、Excel 用例导出、需求 PDF、页面截图，特点是**体积大且往往包含真实业务信息**——而这个仓库是要推 GitHub 的。建议分层：

| 层 | 放什么 | 位置 | 入库吗 |
|---|---|---|---|
| 正文层 | 脱敏整理后的需求描述、评审结论、用例（markdown） | `projects/<id>/features/<feature>/` | 是 |
| 原始材料层 | 原件、大附件、含真实数据的截图 | 宿主机私有区或网盘/对象存储 | **否** |
| 索引层 | 记录原件位置 | `01-source/assets.md`（只写路径或链接） | 是 |

给 `.gitignore` 补一条 `01-source/attachments/` 之类的规则即可兜底，避免手滑把原件提交了。（这条其实是之前清洗工作的延续：那次留下的教训就是"写了 gitignore 规则但目录名不匹配规则"，所以现在把路径定死在约定里。）

### 6.5 备份问答

- markdown 资产：git + GitHub 远端就是备份，无需额外措施；
- 外部原始材料：按公司/个人习惯单独保管，仓库只留索引；
- 测试结果：`runs/` 里的东西丢了不心疼，重跑一次就有。

### 6.6 自动化用例 md 的落位（第二层）

你说的"单独用 md 存放到对应位置"——对应位置就是**自动化工程内的用例目录，与测试代码同级**：

```text
api-automation/
  apis/<模块>/              接口封装
  testcases/<模块>/
      test_xxx.py           执行代码
      cases.md    ← 用例 md（可选，按模块拆分）   新增
  data/<模块>/*.yaml        测试数据（占位符化）

ui-automation/
  pages/<模块>/
  testcases/<模块>/
      test_xxx.py
      cases.md    ← 用例 md                      新增
  data/*.yaml
```

这样做的原因：

1. **跟随代码进 git**：自动化脚本要推 GitHub，用例 md 与脚本同一 commit，改脚本和改用例一次提交，不会出现"代码更新了但用例还停在旧版本"的错位；
2. **容器天然可见**：工程目录以只读或读写方式挂载进容器（源码挂载是开发态默认做法），脚本和用例 md 一起被看见，不需要额外的挂载声明；
3. **可追溯**：可以从 `projects/.../04-test-design/test-cases.md`（设计态全量）→ `testcases/<模块>/cases.md`（已自动化子集）逐层收敛，前者是全集，后者是落地集。

**唯一的前提：这些 md 里不能出现真实业务数据。** 仓库要推 GitHub，凡是进了 `testcases/` 目录的东西都会跟着公开出去——沿用已经定下的约定：账号/手机号/企业名/token 一律走 `${VAR}` 这类占位符，真实值只存在于本地 `.env`（已 gitignore）。这一条要在写入时检查，不要等到推送后再清理。

### 6.7 挂载矩阵（最终形态）

| 路径 | 容器内 | 模式 | 说明 |
|---|---|---|---|
| `api-automation/`、`ui-automation/` | `/app` | rw | 代码 + 自动化用例 md，随 git 走；改代码不用重建镜像 |
| `projects/` | `/assets/projects` | **ro** | 需求 / 评审 / 设计态用例，容器只读消费 |
| `templates/`、`schemas/`、`config/` | `/assets/**` | **ro** | 共享定义 |
| 工程内 `reports/allure-results/` | `/app/reports/allure-results` | rw | 结果吐到宿主机（已 gitignore） |
| `runs/`（顶层） | `/runs` | rw | 历史归档 |
| `reports/site/`（顶层） | `/site`、nginx html | rw | 报告站静态页（已 gitignore） |

一句话：**进镜像/挂载的是"跑得起来的东西"，只读挂载的是"要被参考的东西"，两者不混。**

## 7. 配置与密钥注入

沿用现有"占位符 + `.env`"机制，**不在镜像里封任何真实值**：

- 容器变量：被测系统的账号口令（键名自定义，如 `TEST_USERNAME` / `TEST_PASSWORD`），以及 `<ENV>_BASE_URL` / `<ENV>_HOME_URL` 覆盖
- 通过 `env_file` 注入（用 long syntax 的 `required: false`，文件缺失也不报错），建议 `docker/compose.env`，从 `docker/compose.env.example` 复制
- 构建期代理：`http_proxy/https_proxy` 用 `host.docker.internal:3067`；运行期若被测系统是内网地址，需要配 `no_proxy` 放行

## 8. 命令矩阵（落地后的预期）

```text
docker compose build                                  # 构建测试镜像
docker compose --profile report build                 # 构建报告镜像（按需）
docker compose run --rm api-tests                     # 跑接口（默认 dev 环境）
docker compose run --rm ui-tests                      # 跑 UI（默认 local fixture，不联网，用于自检）
docker compose run --rm ui-tests --env=sit            # 指定环境
docker compose run --rm api-tests -m smoke            # 只跑冒烟
docker compose --profile report up -d report-site     # 生成 + 托管报告 localhost:8080
docker compose down -v                                # 清理
```

已实跑验证（2026-09-24）：

- `docker compose run --rm ui-tests` → 2 passed / 1 skipped，归档到 `runs/2026-09-24/002/ui`
- `docker compose --profile report up -d report-site` → allure-generate 退出 0，
  `reports/site/index.html` 生成了完整报告（含 data/、widgets/、history/），`localhost:8080` 返回 200

## 9. 与现有 `run_all.ps1` 的关系 ✅ 已定：并行保留

- PowerShell 脚本继续走**本机裸跑**路径（无 Docker 时的兜底），归档沿用旧的 `reports/<月>月/<日>/<序号>/`
- Docker 路径独立实现 `runs/YYYY-MM-DD/<seq>/` 归档（§5.2），README 中标注 **Docker 为主路径**
- 两条路径不共用归档目录，避免互相覆盖

## 10. 决策状态

| # | 议题 | 结论 |
|---|---|---|
| 1 | UI 镜像 | ✅ **B —— 官方 `mcr.microsoft.com/playwright/python:v1.52.0`**（走 `mcr.azure.cn` 镜像站拉取，manifest 与官方一致） |
| 2 | Allure 报告 | ✅ **a —— 自制 allure CLI 镜像（v2.46.1，基于本地 `maven:3.9-eclipse-temurin-17`）+ 本地 `nginx:alpine` 托管** |
| 3 | 历史归档 | ✅ **顶层 `runs/YYYY-MM-DD/<seq>/`**，附 `summary.json`；`.gitignore` 加 `runs/` |
| 4 | 登录态 `.auth_state.json` | ✅ **不落宿主机**，容器内 `/tmp` 匿名卷，随容器销毁（默认行为，如需留痕加 `--keep-auth` 显式开启） |
| 5 | 项目资产落位 | ✅ **留宿主机仓库 + 容器只读挂载，不进 Docker 卷**（§6） |
| 6 | 需求原件 | ✅ **不入库**，仓库只留 markdown + 索引，`01-source/attachments/` 加 gitignore（§6.4） |
| 7 | `run_all.ps1` | ✅ **并行保留**，Docker 为主路径（§9） |
| ＋ | 自动化用例 md | ✅ **放在工程 `testcases/<模块>/cases.md`**，随脚本进 git、进容器，占位符化（§6.6） |

全部决策已确认，进入实施阶段。落地文件见 §11。

## 11. 落地文件清单

```text
docker-compose.yml                  # 3 个服务 + report profile
.dockerignore
docker/
  Dockerfile.api                    # python:3.12-slim
  Dockerfile.ui                     # playwright/python:v1.52.0
  Dockerfile.allure                 # maven 镜像 + allure CLI
  entrypoint.sh                     # 归档逻辑 + summary.json + auth 处理
  compose.env.example               # 变量示例
  nginx.conf                        # 报告站
runs/                               # 归档产物（gitignore）
```

README 补充「Docker 部署」章节。

## 12. 落地时踩到的坑（已修，换机器时照着检查）

> 补充一条运维常识：`docker/entrypoint.sh` 是 COPY 进镜像的（`/usr/local/bin`），
> 不在 `/app` 挂载范围内 —— 改了归档逻辑必须 `docker compose build` 才生效；
> 而工程内的用例代码是 bind mount，改完立刻生效。两者别搞混。

| 现象 | 原因 | 修法 |
|---|---|---|
| `BrowserType.launch: Executable doesn't exist` | Playwright 官方镜像**只装浏览器不装 python 包**（`pip show playwright` 为空，只有 `/ms-playwright/chromium-1169`）。requirements 写 `>=1.40`，pip 会装到最新 1.63，与 chromium-1169 对不上 | Dockerfile.ui 里把 playwright 从 requirements 中剔除，改按镜像版本精确安装 `playwright==1.52.0`（ARG `PLAYWRIGHT_PY_VERSION`，升镜像 tag 时同步改） |
| `Chromium distribution 'chrome' is not found at /opt/google/chrome/chrome` | `config.yaml` 的 `defaults.channel: chrome` 指定用系统 Chrome，容器里没有 | 新增 `BROWSER_CHANNEL` 环境变量覆盖，compose 里置空 → 走 Playwright 内置 chromium；宿主机不受影响 |
| `docker compose --profile report up -d` 把测试也跑了一遍 | profile 是"额外启用"，不是"只启用这些"，没有 profile 的服务照常启动 | 报告命令必须显式带服务名：`up -d report-site` |
| 容器内 `127.0.0.1:3067` 代理不生效 | 容器内 127.0.0.1 是自身 | 构建期用 `host.docker.internal:3067`，并加 `extra_hosts: host-gateway` |
| 官方镜像拉取慢 | `mcr.microsoft.com` 国内不稳 | 用 `mcr.azure.cn` 拉，再 `docker tag` 成官方名；两者 manifest digest 完全一致 |

镜像体积：`ai-test/api-tests` 约 240MB、`ai-test/ui-tests` 3.9GB（官方 Playwright 镜像本体就 3.56GB）、
`ai-test/allure` 约 810MB（maven 镜像 763MB + allure CLI）。
