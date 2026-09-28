# projects/ —— 项目资产区

每个被测项目在 `projects/` 下占一个目录，存放该项目的需求、分析与测试资产。

> 本目录当前为空：原有业务项目资产已移出仓库，避免在代码库中保留业务数据。

## 目录约定

```
projects/
└── <project-id>/                       # 项目 ID，见同目录 project.yaml
    ├── project.yaml                    # 项目配置（校验见 schemas/project-config.schema.json）
    ├── requirement-catalog.md          # 需求总目录（可选）
    ├── knowledge/                      # 项目知识库（术语、业务规则、交接文档等）
    │   ├── terminology.md
    │   └── business-rules.md
    └── features/
        └── <feature-name>/             # 单个功能/需求
            ├── 01-source/              # 需求原文与补充确认
            │   ├── requirement.md
            │   ├── attachments/
            │   └── confirmations/
            ├── 02-analysis/            # 需求评审产出
            │   └── requirement-review.md
            ├── 03-frozen-requirement.md # 冻结需求（评审通过后）
            └── 04-test-design/         # 测试设计产出
                └── test-cases.md
```

## 新建项目

1. 复制 `project.yaml` 结构（字段以 `schemas/project-config.schema.json` 为准）；
2. 需求原文放 `features/<feature>/01-source/requirement.md`，模板见 `templates/requirement-input.md`；
3. 由需求评审智能体产出 `02-analysis/requirement-review.md`，通过后冻结为 `03-frozen-requirement.md`；
4. 由测试设计智能体产出 `04-test-design/test-cases.md`，格式见 `schemas/test-case.schema.json`。

## 约束

- 项目资产只落在 `projects/<project-id>/` 内，不得写入 `.github/`、`config/`、`schemas/`、`templates/`、`tools/` 等共享目录。
- 需求、用例中如涉及账号、token、内网地址等敏感信息，一律用占位符（如 `${TEST_MOBILE}`），真实值放 `.env`。
- 若项目目录下需要克隆被测系统的源码仓库，放到 `projects/<project-id>/repositories/`，该路径已被 `.gitignore` 排除。
