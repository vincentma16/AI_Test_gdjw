<#
.SYNOPSIS
  接口自动化一键运行：跑全部场景 -> 生成 Allure 报告 -> 按日期归档
.DESCRIPTION
  - --clean-alluredir 清空上次结果，保证本次报告干净
  - 归档到 reports/<月>月/<日>/<序号>/，序号当日递增（3位补零）
  - 历史归档永久留存，手动删除才消失
  - 最新报告始终在 reports/allure-report/
#>
$ErrorActionPreference = "Continue"
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $base
$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " 1/3 运行全部接口测试场景" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
& $py -m pytest testcases/ -v --clean-alluredir --alluredir=reports/allure-results
$testExit = $LASTEXITCODE

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " 2/3 生成 Allure 报告" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
allure generate reports/allure-results -o reports/allure-report --clean
if ($LASTEXITCODE -ne 0) { Write-Host "报告生成失败" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " 3/3 归档报告 -> reports/<月>月/<日>/<序号>" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
$now = Get-Date
$month = "{0:D2}月" -f $now.Month                # 08月
$day = "{0:D2}{1:D2}" -f $now.Month, $now.Day    # 0807
$archiveBase = "reports\$month\$day"
# 序号递增：扫描同日已有数字目录，取最大+1
$seq = 1
if (Test-Path $archiveBase) {
    $existing = Get-ChildItem $archiveBase -Directory | Where-Object { $_.Name -match '^\d{3}$' } | ForEach-Object { [int]$_.Name }
    if ($existing) { $seq = ($existing | Measure-Object -Maximum).Maximum + 1 }
}
$seqStr = "{0:D3}" -f $seq
$archive = "$archiveBase\$seqStr"
New-Item -ItemType Directory -Path $archive -Force | Out-Null
robocopy "reports\allure-report" $archive /E /NFL /NDL /NJH /NJS /NP 2>&1 | Out-Null
# 写归档清单
$summary = "运行时间: $($now.ToString('yyyy-MM-dd HH:mm:ss'))`r`n测试结果: exit=$testExit`r`n报告生成: allure"
Set-Content -Path "$archive\run_info.txt" -Value $summary -Encoding UTF8

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host " 完成！" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host " 最新报告: reports\allure-report\index.html"
Write-Host " 归档报告: $archive\index.html"
Write-Host " 历史归档目录: reports\"
Write-Host ""
Write-Host " 启动查看服务: 在项目目录执行"
Write-Host "   python -m http.server 8089 --directory reports\allure-report"
Write-Host " 然后打开 reports\open_report.html"