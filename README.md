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
api-automation-template/  接口自动化脚手架（带 example 参考实现，复制到新项目用）
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

docker compose run --rm api-tests                  # 跑接口（默认 dev）
docker compose run --rm api-tests --env=sit        # 指定环境
docker compose run --rm api-tests -m smoke         # 只跑冒烟

docker compose run --rm ui-tests                   # 跑 UI（默认 local fixture，不联网）
docker compose run --rm ui-tests --env=sit         # 指定环境

docker compose --profile report up -d report-site  # 生成报告并起报告站
# 浏览器打开 http://localhost:8080

docker compose down -v                             # 清理
```

> 报告命令必须显式写服务名 `report-site`：profile 只是"额外启用"，不会限制已存在的
> 服务，直接 `up -d` 会把测试服务也拉起来跑一遍。

每次运行的结果归档到 `runs/<日期>/<序号>/<套件>/`，含 `allure-results/` 与
`summary.json`（时间、耗时、退出码、命令）。序号当日递增，不会覆盖。

两个注意点：

- `docker/entrypoint.sh`（归档逻辑）是**烤进镜像**的，改完要 `docker compose build` 才生效；
  工程内的用例代码是挂载进去的，改完直接生效，不用重建
- `api-automation` 的 `testcases/` 为空时，pytest 退出码为 5，entrypoint 会额外打印
  "未收集到任何用例（非容器故障）"，属正常状态

### 资产边界

| 目录 | 容器内 | 模式 | 说明 |
|---|---|---|---|
| `api-automation/`、`ui-automation/` | `/app` | 读写 | 代码与自动化用例 md，随 git 走 |
| `projects/`、`templates/`、`schemas/`、`config/` | `/assets/**` | **只读** | 需求 / 评审 / 设计态用例，容器只消费不改写 |
| 工程内 `reports/allure-results/` | `/app/reports/allure-results` | 读写 | 最新一次结果，已 gitignore |
| `runs/`、`reports/site/` | `/runs`、`/site` | 读写 | 归档与报告站，已 gitignore |

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
