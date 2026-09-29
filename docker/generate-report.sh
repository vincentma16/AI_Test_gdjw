#!/usr/bin/env bash
# 把 Allure 原始结果生成静态 HTML 报告。
#
# 报告按「一次运行」独立输出，不再互相覆盖：
#   报告目录 = runs/<日期>/<序号>/report/
#
# 三种用法：
#   1) 不传任何变量：自动定位 runs/ 下最新一次运行，报告写到该运行的 report/
#   2) RUN_DIR=/runs/<日期>/<序号>：为指定的这次运行生成
#   3) ALLURE_RESULTS_DIRS=/a:/b + ALLURE_REPORT_DIR=/out：显式指定输入与输出（旧式）
set -euo pipefail

RUNS_ROOT="${RUNS_ROOT:-/runs}"
WORK_DIR="/tmp/allure-combined"
SRC_DIRS="${ALLURE_RESULTS_DIRS:-}"
OUT_DIR="${ALLURE_REPORT_DIR:-}"
RUN_DIR="${RUN_DIR:-}"

write_placeholder() {
  # $1 = 输出目录。没有结果时生成占位页，保证 nginx 侧不会 404
  local out="$1"
  mkdir -p "${out}"
  cat > "${out}/index.html" <<'HTML'
<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>Allure 报告</title></head>
<body style="font-family:system-ui,sans-serif;padding:48px">
  <h1>暂无测试报告</h1>
  <p>还没有产生 Allure 结果。先跑一次测试：</p>
  <pre>bash docker/run-tests.sh --suite api
bash docker/run-tests.sh --suite ui
bash docker/run-report.sh</pre>
</body>
</html>
HTML
}

# ---------------------------------------------------------------------------
# 1. 定位这次要出报告的运行目录
# ---------------------------------------------------------------------------
if [ -z "${SRC_DIRS}" ]; then
  if [ -z "${RUN_DIR}" ]; then
    LATEST_DATE="$(ls -1 "${RUNS_ROOT}" 2>/dev/null \
                   | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' | sort | tail -n1 || true)"
    if [ -z "${LATEST_DATE}" ]; then
      echo "[allure] ${RUNS_ROOT} 下还没有任何运行记录，写出占位页"
      write_placeholder "${OUT_DIR:-${RUNS_ROOT}/latest/report}"
      exit 0
    fi
    LATEST_SEQ="$(ls -1 "${RUNS_ROOT}/${LATEST_DATE}" 2>/dev/null \
                  | grep -E '^[0-9]{3}$' | sort | tail -n1 || true)"
    if [ -z "${LATEST_SEQ}" ]; then
      echo "[allure] ${RUNS_ROOT}/${LATEST_DATE} 下没有可用的序号目录，写出占位页"
      write_placeholder "${OUT_DIR:-${RUNS_ROOT}/latest/report}"
      exit 0
    fi
    RUN_DIR="${RUNS_ROOT}/${LATEST_DATE}/${LATEST_SEQ}"
  fi

  if [ ! -d "${RUN_DIR}" ]; then
    echo "[allure] 运行目录不存在: ${RUN_DIR}" >&2
    exit 1
  fi
  [ -n "${OUT_DIR}" ] || OUT_DIR="${RUN_DIR}/report"
  echo "[allure] 目标运行: ${RUN_DIR}"
fi
[ -n "${OUT_DIR}" ] || OUT_DIR="/site"

# ---------------------------------------------------------------------------
# 2. 收集结果：显式列表优先，否则汇总该运行下所有套件的 allure-results
# ---------------------------------------------------------------------------
rm -rf "${WORK_DIR}"
mkdir -p "${WORK_DIR}" "${OUT_DIR}"

FOUND=0
if [ -n "${SRC_DIRS}" ]; then
  IFS=':' read -ra DIRS <<< "${SRC_DIRS}"
else
  # RUN_DIR 下每个子目录是一个套件（api / ui），各带一份 allure-results
  shopt -s nullglob
  DIRS=("${RUN_DIR}"/*/allure-results)
  shopt -u nullglob
fi

for d in "${DIRS[@]}"; do
  [ -d "${d}" ] || continue
  # 只认真正的 Allure 结果文件，避免把空目录当有效输入
  if compgen -G "${d}/*-result.json" > /dev/null || compgen -G "${d}/*result.json" > /dev/null; then
    echo "[allure] 收集结果: ${d}"
    cp -a "${d}/." "${WORK_DIR}/" 2>/dev/null || true
    FOUND=1
  else
    echo "[allure] 跳过（无结果文件）: ${d}"
  fi
done

# ---------------------------------------------------------------------------
# 3. 生成
# ---------------------------------------------------------------------------
if [ "${FOUND}" -eq 0 ]; then
  echo "[allure] 没有找到任何 Allure 结果，生成占位页"
  write_placeholder "${OUT_DIR}"
  exit 0
fi

rm -rf "${OUT_DIR:?}"/*
allure generate "${WORK_DIR}" --clean -o "${OUT_DIR}"
echo "[allure] 报告已生成: ${OUT_DIR}"
