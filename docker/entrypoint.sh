#!/usr/bin/env bash
# 测试执行入口：跑 pytest -> 归档到 runs/<日期>/<序号>/<套件>/ -> 写 summary.json
# 源码由 compose 以 bind mount 挂载到 /app，构建后改代码无需重建镜像
set -uo pipefail

SUITE="${SUITE:-unknown}"
RUN_BASE="${RUN_BASE:-/runs}"
RESULTS_DIR="${RESULTS_DIR:-/app/reports/allure-results}"
KEEP_AUTH="${KEEP_AUTH:-0}"

STAMP="$(date +%F)"
RUN_ROOT="${RUN_BASE}/${STAMP}"
mkdir -p "${RUN_ROOT}"

# 序号：当日递增三位补零；可用 RUN_SEQ 显式指定，把 api / ui 归到同一次运行
SEQ="${RUN_SEQ:-}"
if [ -z "${SEQ}" ]; then
  LAST="$(find "${RUN_ROOT}" -maxdepth 1 -type d -printf '%f\n' 2>/dev/null \
          | grep -E '^[0-9]{3}$' | sort -n | tail -n1)"
  if [ -z "${LAST}" ]; then
    SEQ="001"
  else
    SEQ="$(printf '%03d' $((10#${LAST} + 1)))"
  fi
fi

RUN_DIR="${RUN_ROOT}/${SEQ}/${SUITE}"
mkdir -p "${RUN_DIR}"

START_AT="$(date -Iseconds)"
START_EPOCH="$(date +%s)"

echo "=========================================================="
echo "套件        : ${SUITE}"
echo "命令        : pytest $*"
echo "结果目录    : ${RESULTS_DIR}"
echo "归档目录    : ${RUN_DIR}"
echo "开始时间    : ${START_AT}"
echo "=========================================================="

set +e
python -m pytest "$@"
EXIT_CODE=$?
set -e

END_AT="$(date -Iseconds)"
DURATION=$(( $(date +%s) - START_EPOCH ))

# 归档 Allure 原始结果（--clean-alluredir 每次会覆盖，靠归档保留历史）
if [ -d "${RESULTS_DIR}" ]; then
  rm -rf "${RUN_DIR}/allure-results"
  cp -a "${RESULTS_DIR}" "${RUN_DIR}/allure-results" 2>/dev/null || true
fi

# 登录态不落宿主机（含真实 token），用完即删；需要留痕时 KEEP_AUTH=1
if [ "${KEEP_AUTH}" != "1" ]; then
  rm -f /app/reports/.auth_state.json "${RESULTS_DIR}/../.auth_state.json" 2>/dev/null || true
fi

CMD_STR="$(printf '%s ' "$@" | sed 's/\\/\\\\/g; s/"/\\"/g')"
cat > "${RUN_DIR}/summary.json" <<JSON
{
  "suite": "${SUITE}",
  "date": "${STAMP}",
  "seq": "${SEQ}",
  "start_at": "${START_AT}",
  "end_at": "${END_AT}",
  "duration_sec": ${DURATION},
  "exit_code": ${EXIT_CODE},
  "command": "pytest ${CMD_STR}",
  "results_dir": "${RUN_DIR}/allure-results"
}
JSON

echo "=========================================================="
echo "退出码      : ${EXIT_CODE}"
echo "耗时        : ${DURATION}s"
echo "归档        : ${RUN_DIR}"
# pytest 退出码 5 = 未收集到任何用例。空框架刚起步时这是正常状态，
# 明确提示出来，避免被误判成"容器坏了"。
if [ "${EXIT_CODE}" -eq 5 ]; then
  echo "提示        : 未收集到任何用例（testcases/ 为空时属正常，非容器故障）"
fi
echo "=========================================================="

exit "${EXIT_CODE}"
