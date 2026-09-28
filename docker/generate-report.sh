#!/usr/bin/env bash
# 把 Allure 原始结果生成静态 HTML 报告
# 默认合并"最新一次 api + ui"的结果；可用 ALLURE_RESULTS_DIRS 指向某次归档
set -euo pipefail

# 冒号分隔的多个结果目录
SRC_DIRS="${ALLURE_RESULTS_DIRS:-/api/reports/allure-results:/ui/reports/allure-results}"
OUT_DIR="${ALLURE_REPORT_DIR:-/site}"
WORK_DIR="/tmp/allure-combined"

rm -rf "${WORK_DIR}"
mkdir -p "${WORK_DIR}" "${OUT_DIR}"

FOUND=0
IFS=':' read -ra DIRS <<< "${SRC_DIRS}"
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

if [ "${FOUND}" -eq 0 ]; then
  echo "[allure] 没有找到任何 Allure 结果，生成占位页"
  cat > "${OUT_DIR}/index.html" <<'HTML'
<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>Allure 报告</title></head>
<body style="font-family:system-ui,sans-serif;padding:48px">
  <h1>暂无测试报告</h1>
  <p>还没有生成 Allure 结果。先跑一次测试：</p>
  <pre>docker compose run --rm api-tests
docker compose run --rm ui-tests</pre>
</body>
</html>
HTML
  exit 0
fi

rm -rf "${OUT_DIR:?}"/*
allure generate "${WORK_DIR}" --clean -o "${OUT_DIR}"
echo "[allure] 报告已生成: ${OUT_DIR}"
