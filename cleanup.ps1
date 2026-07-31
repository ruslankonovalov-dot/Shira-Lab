# cleanup.ps1 — Очистка мусора из репозитория Shira Lab
# Запуск: .\cleanup.ps1
# ====================================================================

Write-Host "=== Shira Lab Cleanup ===" -ForegroundColor Green

# 1. Удалить "Dont touch cloude" файлы
Write-Host "`n[1/7] Removing Dont touch cloude*.json..." -ForegroundColor Yellow
Remove-Item ".\Dont touch cloude1.json" -Force -ErrorAction SilentlyContinue
Remove-Item ".\Dont touch cloude2.json" -Force -ErrorAction SilentlyContinue
Write-Host "  Done" -ForegroundColor Green

# 2. Удалить data/profile.json (только example должен быть в репо)
Write-Host "`n[2/7] Removing data/profile.json (user data)..." -ForegroundColor Yellow
Remove-Item ".\data\profile.json" -Force -ErrorAction SilentlyContinue
Write-Host "  Done" -ForegroundColor Green

# 3. Удалить записи рекордера
Write-Host "`n[3/7] Removing records/REC_*.json..." -ForegroundColor Yellow
Remove-Item ".\records\REC_*.json" -Force -ErrorAction SilentlyContinue
Write-Host "  Done" -ForegroundColor Green

# 4. Удалить .claude папку
Write-Host "`n[4/7] Removing .claude/ folder..." -ForegroundColor Yellow
Remove-Item ".\.claude" -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "  Done" -ForegroundColor Green

# 5. Удалить screenshots папку
Write-Host "`n[5/7] Removing screenshots/ folder..." -ForegroundColor Yellow
Remove-Item ".\screenshots" -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "  Done" -ForegroundColor Green

# 6. Удалить старые бэкапы и lnk
Write-Host "`n[6/7] Removing .lnk and .zip backups..." -ForegroundColor Yellow
Remove-Item ".\Shira Lab.lnk" -Force -ErrorAction SilentlyContinue
Remove-Item ".\shira_lab_qt.zip" -Force -ErrorAction SilentlyContinue
Remove-Item ".\shira_lab_v1_sss.zip" -Force -ErrorAction SilentlyContinue
Write-Host "  Done" -ForegroundColor Green

# 7. Удалить debug файлы
Write-Host "`n[7/7] Removing debug files..." -ForegroundColor Yellow
Remove-Item ".\debug_layout.py" -Force -ErrorAction SilentlyContinue
Remove-Item ".\logo_check.txt" -Force -ErrorAction SilentlyContinue
Remove-Item ".\logo_out.txt" -Force -ErrorAction SilentlyContinue
Write-Host "  Done" -ForegroundColor Green

Write-Host "`n=== Cleanup Complete! ===" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "  1. Apply fixes from shira_v0166_fixes.zip" -ForegroundColor White
Write-Host "  2. Run: python run.py" -ForegroundColor White
Write-Host "  3. Commit: git add -A && git commit -m 'cleanup + v0.16.6 fixes'" -ForegroundColor White
