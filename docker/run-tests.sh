#!/usr/bin/env bash
# 统一的测试运行入口：参数白名单 + 并发隔离 + 自动运行序号
#
#   bash docker/run-tests.sh --suite api
#   bash docker/run-tests.sh --suite ui  --env sit
#   bash docker/run-tests.sh --suite all --env dev --marker smoke
#
# 安全约束（重要）：
#   这里**不接受任意 pytest 参数**。所有取值都走枚举或正则白名单，且命令按数组构造、
#   不经 eval，外部输入无法拼出额外的 shell 语法。后续接可视化平台时，平台层必须做
#   同样的校验，不能把用户输入直接丢给 docker compose。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

RUNS_DIR="${REPO_ROOT}/runs"
SUITE=""
ENV_NAME=""
MARKER=""

ALLOWED_SUITES="api|ui|all"
ALLOWED_ENVS="dev|uat|sit|prod|local"

usage() {
  cat <<'USAGE'
用法: bash docker/run-tests.sh --suite <api|ui|all> [选项]

  --suite <api|ui|all>             必填。all = 先跑 api 再跑 ui，共用同一运行序号
  --env <dev|uat|sit|prod|local>   运行环境，默认取 compose 里的默认值（api=dev / ui=local）
  --marker <name>                  只跑指定 pytest marker（只允许字母、数字、下划线）
  --help

产出：runs/<日期>/<序号>/<套件>/ 下会有 allure-results 与 summary.json
出报告：bash docker/run-report.sh --seq <上面的序号>

并发：每次调用都会申请独立的运行序号与独立的 compose 项目名，多个运行可以同时跑。
USAGE
}

die() { echo "错误: $*" >&2; exit 2; }

# 枚举校验：$1=字段 $2=取值 $3=竖线分隔的允许列表
validate_enum() {
  local field="$1" value="$2" allowed="$3" token ok=0
  local IFS='|'
  for token in ${allowed}; do
    [ "${value}" = "${token}" ] && ok=1
  done
  [ "${ok}" -eq 1 ] || die "--${field} 只允许 ${allowed//|/, }（收到：${value}）"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --suite)
      [ $# -ge 2 ] || die "--suite 缺少取值"
      validate_enum suite "$2" "${ALLOWED_SUITES}"
      SUITE="$2"; shift 2 ;;
    --env)
      [ $# -ge 2 ] || die "--env 缺少取值"
      validate_enum env "$2" "${ALLOWED_ENVS}"
      ENV_NAME="$2"; shift 2 ;;
    --marker)
      [ $# -ge 2 ] || die "--marker 缺少取值"
      [[ "$2" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] \
        || die "--marker 只允许字母/数字/下划线开头为字母或下划线（收到：$2）"
      MARKER="$2"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) die "未知参数 $1（只接受 --suite / --env / --marker，不接受任意 pytest 参数）" ;;
  esac
done

[ -n "${SUITE}" ] || { usage; die "必须指定 --suite"; }

# ui 的 local 环境跑的是本地 fixture（不联网），作为 ui 的默认值比 dev 更合适。
# 注意 api 的 conftest 只接受 dev/uat/sit/prod，两者默认值不同，因此留到 run_one 里按套件定。
if [ -z "${ENV_NAME}" ]; then
  ENV_HINT="(api=dev / ui=local)"
else
  ENV_HINT="${ENV_NAME}"
fi

# ---------------------------------------------------------------------------
# 申请运行序号：mkdir 是原子操作，并发时能保证同一天不会撞号
# ---------------------------------------------------------------------------
TODAY="$(date +%F)"
mkdir -p "${RUNS_DIR}/${TODAY}"
SEQ=""
for i in $(seq 1 999); do
  candidate="$(printf '%03d' "$i")"
  if mkdir "${RUNS_DIR}/${TODAY}/${candidate}" 2>/dev/null; then
    SEQ="${candidate}"
    break
  fi
done
[ -n "${SEQ}" ] || die "无法分配运行序号（当日 999 次已达上限）"

PID="$$"
echo "=========================================================="
echo "运行          : ${TODAY} / ${SEQ}"
echo "套件          : ${SUITE}"
echo "环境          : ${ENV_HINT}"
[ -n "${MARKER}" ] && echo "标记          : ${MARKER}"
echo "归档          : runs/${TODAY}/${SEQ}"
echo "=========================================================="

# ---------------------------------------------------------------------------
# 执行：compose 项目名带上日期+序号+PID，使并发运行各自独立
# ---------------------------------------------------------------------------
run_one() {
  local suite="$1"
  local project="ai-test-run-${TODAY//-/}-${SEQ}-${suite}-${PID}"

  # 每个套件的默认环境不同（ui 默认 local 跑本地 fixture，api 默认 dev）
  local suite_env="${ENV_NAME}"
  if [ -z "${suite_env}" ]; then
    if [ "${suite}" = "ui" ]; then suite_env="local"; else suite_env="dev"; fi
  fi

  # 命令按数组构造，不做字符串拼接，外部取值无法注入额外参数
  local -a cmd=(docker compose -p "${project}" run --rm -e "RUN_SEQ=${SEQ}")
  cmd+=("${suite}-tests" "--env=${suite_env}")
  [ -n "${MARKER}" ] && cmd+=(-m "${MARKER}")

  echo ">>>> ${suite}: docker compose -p ${project} run --rm ${suite}-tests --env=${suite_env}"
  set +e
  "${cmd[@]}"
  local code=$?
  set -e
  echo "<<<< ${suite} 退出码: ${code}"
  return "${code}"
}

FINAL_CODE=0
if [ "${SUITE}" = "all" ]; then
  run_one api || FINAL_CODE=$?
  run_one ui  || FINAL_CODE=$?
else
  run_one "${SUITE}" || FINAL_CODE=$?
fi

echo "=========================================================="
echo "退出码        : ${FINAL_CODE}"
echo "归档          : runs/${TODAY}/${SEQ}"
echo "生成报告      : bash docker/run-report.sh --seq ${SEQ}"
echo "=========================================================="
exit "${FINAL_CODE}"
