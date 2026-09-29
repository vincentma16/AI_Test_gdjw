#!/usr/bin/env bash
# 为某一次运行生成 Allure 报告，并重建 runs/index.html 导航页
#
#   bash docker/run-report.sh                        # 最新一次运行
#   bash docker/run-report.sh --date 2026-09-29      # 该日最新一次
#   bash docker/run-report.sh --seq 003              # 指定序号（默认今天）
#
# 报告输出位置始终是：runs/<日期>/<序号>/report/
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

RUNS_DIR="${REPO_ROOT}/runs"
DATE_ARG="$(date +%F)"
SEQ_ARG=""

usage() {
  cat <<'USAGE'
用法: bash docker/run-report.sh [选项]

  --date YYYY-MM-DD   指定日期，默认今天
  --seq NNN           指定当日序号；不传则取该日最大的序号
  --help

说明：报告是否生成与测试是否通过无关，失败的运行同样会出报告（这正是要看的东西）。
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --date) [ $# -ge 2 ] || { echo "错误: --date 缺少取值" >&2; exit 2; }
            [[ "$2" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { echo "错误: --date 必须是 YYYY-MM-DD" >&2; exit 2; }
            DATE_ARG="$2"; shift 2 ;;
    --seq)  [ $# -ge 2 ] || { echo "错误: --seq 缺少取值" >&2; exit 2; }
            [[ "$2" =~ ^[0-9]{1,3}$ ]] || { echo "错误: --seq 必须是 1-3 位数字" >&2; exit 2; }
            SEQ_ARG="$(printf '%03d' $((10#$2)))"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "错误: 未知参数 $1（只接受 --date / --seq）" >&2; usage; exit 2 ;;
  esac
done

if [ ! -d "${RUNS_DIR}/${DATE_ARG}" ]; then
  echo "错误: ${RUNS_DIR}/${DATE_ARG} 不存在，先跑一次测试或换个 --date" >&2
  exit 1
fi

if [ -z "${SEQ_ARG}" ]; then
  SEQ_ARG="$(ls -1 "${RUNS_DIR}/${DATE_ARG}" | grep -E '^[0-9]{3}$' | sort | tail -n1 || true)"
  if [ -z "${SEQ_ARG}" ]; then
    echo "错误: ${RUNS_DIR}/${DATE_ARG} 下还没有可用的序号目录" >&2
    exit 1
  fi
fi

RUN_REL="${DATE_ARG}/${SEQ_ARG}"
RUN_HOST="${RUNS_DIR}/${RUN_REL}"
if [ ! -d "${RUN_HOST}" ]; then
  echo "错误: 运行目录不存在 ${RUN_HOST}" >&2
  exit 1
fi

echo "=========================================================="
echo "目标运行    : runs/${RUN_REL}"
echo "报告输出    : runs/${RUN_REL}/report"
echo "=========================================================="

# 报告进程独立成一个 compose 项目，避免与正在跑的测试抢容器名
COMPOSE_PROJECT_NAME="ai-test-report-${SEQ_ARG}-$$" \
docker compose --profile report run --rm \
  -e "RUN_DIR=/runs/${RUN_REL}" \
  allure-generate

# ---------------------------------------------------------------------------
# 重建导航页：列出所有有报告的运行，按日期+序号倒序
# ---------------------------------------------------------------------------
INDEX="${RUNS_DIR}/index.html"

# 用 sed 从 summary.json 取值，不依赖宿主机是否装 python
field() {  # $1=summary.json $2=字段名
  [ -f "$1" ] || return 0
  sed -n "s/.*\"$2\"[[:space:]]*:[[:space:]]*\"\{0,1\}\([^,\"}]*\)\"\{0,1\}.*/\1/p" "$1" | head -n1
}

{
  echo '<!DOCTYPE html>'
  echo '<html lang="zh-CN"><head><meta charset="utf-8"><title>测试运行归档</title>'
  echo '<style>body{font-family:system-ui,sans-serif;padding:32px;background:#16181d;color:#e6e6e6}'
  echo 'h1{font-size:20px;font-weight:600}table{border-collapse:collapse;margin-top:16px;width:100%}'
  echo 'th,td{text-align:left;padding:8px 12px;border-bottom:1px solid #333;font-size:13px}'
  echo 'a{color:#6fb1ff;text-decoration:none}a:hover{text-decoration:underline}'
  echo '.ok{color:#5ad19a}.fail{color:#ff8080}.na{color:#9a9a9a}</style></head><body>'
  echo '<h1>测试运行归档</h1>'
  echo '<p style="color:#9a9a9a;font-size:13px">报告需在浏览器查看；本机请用 <a href="http://127.0.0.1:8080/">http://127.0.0.1:8080/</a></p>'
  echo '<table><tr><th>运行</th><th>套件</th><th>结果</th><th>耗时</th><th>开始时间</th><th>报告</th></tr>'

  found=0
  for d in $(ls -1 "${RUNS_DIR}" 2>/dev/null | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' | sort -r); do
    for s in $(ls -1 "${RUNS_DIR}/${d}" 2>/dev/null | grep -E '^[0-9]{3}$' | sort -r); do
      for suite in api ui; do
        summary="${RUNS_DIR}/${d}/${s}/${suite}/summary.json"
        [ -f "${summary}" ] || continue
        found=1
        code="$(field "${summary}" exit_code)"
        dur="$(field "${summary}" duration_sec)"
        start="$(field "${summary}" start_at)"
        if [ "${code}" = "0" ]; then
          cls="ok"; text="通过"
        elif [ "${code}" = "5" ]; then
          cls="na"; text="无用例"
        else
          cls="fail"; text="失败 ${code}"
        fi
        echo "<tr><td>${d} / ${s}</td><td>${suite}</td><td class=\"${cls}\">${text}</td><td>${dur}s</td><td>${start}</td><td><a href=\"./${d}/${s}/report/index.html\">查看</a></td></tr>"
      done
    done
  done

  if [ "${found}" -eq 0 ]; then
    echo '<tr><td colspan="6">还没有任何运行记录</td></tr>'
  fi
  echo '</table></body></html>'
} > "${INDEX}"

echo "导航页      : runs/index.html"
echo "查看报告    : http://127.0.0.1:8080/${RUN_REL}/report/index.html"
echo "=========================================================="
