# AI 测试工作台

面向个人测试提效的多项目 AI 测试工作台。当前阶段聚焦需求评审和功能测试设计，仅生成测试资产，不自动发布、执行测试或提交缺陷。

## 目录

```text
.github/agents/   可复用的任务编排智能体
.github/skills/   可迁移的测试方法与工作流
config/           全局默认配置
schemas/          机器可读的资产结构
templates/        不含业务内容的空白模板
tools/            外部系统适配器（按需建设）
projects/         按项目隔离的知识与测试资产
evaluations/      可复用能力的验收场景与质量清单
docs/             工作台架构和使用说明
api-automation/   接口自动化工程（pytest + requests）— 空框架，未接入被测系统
ui-automation/    UI 自动化工程（pytest + playwright）— 仅留 sample 自检样例
docker/           Docker 构建与运行脚本
runs/             测试运行归档（gitignored）
```

> **当前状态**：工作台本体与两个自动化工程都已清空上一套系统的业务内容，
> 只保留框架能力。接入新系统的步骤见 [api-automation/README.md](api-automation/README.md)
> 与 [ui-automation/README.md](ui-automation/README.md)。

## Docker 一键运行

宿主机不需要装 Python / allure / playwright，只需要 Docker。

```bash
cp docker/compose.env.example docker/compose.env   # 可选，按需填代理与账号
docker compose build                               # 构建镜像（首次）

# 推荐入口：自动分配运行序号 + 每次运行独立的 compose 项目名（可并发）
bash docker/run-tests.sh --suite api               # 接口（默认 dev）
bash docker/run-tests.sh --suite ui                # UI（默认 local fixture，不联网）
bash docker/run-tests.sh --suite all               # 两个套件一次跑完，共用一个序号
bash docker/run-tests.sh --suite api --env sit     # 指定环境
bash docker/run-tests.sh --suite api --marker smoke

bash docker/run-report.sh --seq 001                # 为该次运行生成报告
docker compose --profile report up -d report-site  # 起报告站
# 浏览器打开 http://127.0.0.1:8080

docker compose down -v                             # 清理
```

> 也可以直接 `docker compose run --rm api-tests`，但那样不会做并发隔离和运行序号协调，
> 多人/多窗口同时跑会撞容器名。除非明确要自己控制，否则用 `run-tests.sh`。

报告命令必须显式写服务名 `report-site`：profile 只是"额外启用"，不会限制已存在的
服务，直接 `up -d` 会把测试服务也拉起来跑一遍。

### 运行与归档

每次运行落到 `runs/<日期>/<序号>/` 下，一个套件一个子目录：

```text
runs/2026-09-29/004/
├── api/allure-results/       # 原始结果
├── api/summary.json          # 时间、耗时、退出码、命令
├── ui/allure-results/
├── ui/summary.json
└── report/                   # 该次运行的 Allure 报告（run-report.sh 生成）
```

**每次运行的报告是独立的，不会互相覆盖**。报告站直接托管 `runs/`，
访问路径为 `http://127.0.0.1:8080/<日期>/<序号>/report/index.html`；
根目录 `http://127.0.0.1:8080/` 是所有运行的导航页。

### 三条硬约束

1. **`docker/entrypoint.sh` 与 `docker/generate-report.sh` 是烤进镜像的**，
   改完必须 `docker compose build`；工程内的用例代码是挂载进去的，改完即时生效
2. **参数必须走白名单**。`run-tests.sh` 只接受 `--suite` / `--env` / `--marker`，
   取值经枚举或正则校验，命令按数组构造不经 `eval`，外部输入无法拼出额外 shell 语法。
   后续接可视化平台时，平台层要做同样的校验，不能把用户输入直接丢给 `docker compose`
3. **报告站只绑 127.0.0.1**（见 compose 的 `ports`）。能触发 `docker run` 的入口
   等同于具备本机容器控制权，平台化时必须先加鉴权，不要把 8080 直接暴露到局域网

### 资产边界

| 目录 | 容器内 | 模式 | 说明 |
|---|---|---|---|
| `api-automation/`、`ui-automation/` | `/app` | 读写 | 代码与自动化用例 md，随 git 走 |
| `projects/`、`templates/`、`schemas/`、`config/` | `/assets/**` | **只读** | 需求 / 评审 / 设计态用例，容器只消费不改写 |
| 工程内 `reports/allure-results/` | `/app/reports/allure-results` | 读写 | 最新一次结果，已 gitignore |
| `runs/` | `/runs` | 读写 | 归档 + 每次运行的报告 + 导航页，已 gitignore |

登录态 `.auth_state.json` 默认写到容器 `/tmp`，随容器销毁，不落宿主机（需要留痕时
设置 `KEEP_AUTH=1`）。详细设计见 [docs/docker-deployment-plan.md](docs/docker-deployment-plan.md)。

## 当前流程

1. 将 GitHub Issue、Markdown 或粘贴文本保存到功能的 `01-source/`。
2. 使用“需求评审”智能体创建一个评审文件，写入当前结论和 `REV-001` 摘要。
3. 将待确认问题交给产品经理或责任人，并把答复原文保存到 `01-source/confirmations/`。
4. 收到答复或补充需求后，在同一文件中更新当前结论并追加下一轮增量记录。
5. 重复确认和复评，直到阻塞问题关闭且评审结论为通过或有条件通过。
6. 评审通过且无未关闭 P0 后生成 `03-frozen-requirement.md` 冻结需求。
7. 使用“测试设计”智能体生成 `04-test-design/test-cases.md`。
8. 按需推送到 GitHub。

项目资产不得进入智能体、共享能力、模板或工具目录。配置继承顺序为：功能配置 > 项目配置 > 全局默认配置。
