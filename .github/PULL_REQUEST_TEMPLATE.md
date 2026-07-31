# .github/PULL_REQUEST_TEMPLATE.md
## 📋 Что делает этот PR?

<!-- Краткое описание изменений в 2-3 предложениях -->

## 🎯 Связанный issue

Closes #XXX

## 🧪 Тип изменения

- [ ] 🐛 Bug fix (не-breaking change, фиксит issue)
- [ ] ✨ New feature (не-breaking change, добавляет функционал)
- [ ] 💥 Breaking change (фикс/фича, ломающая существующий API)
- [ ] ♻️ Refactor (без изменения поведения)
- [ ] 📚 Documentation update
- [ ] 🧪 Test addition
- [ ] ⚡ Performance improvement
- [ ] 🎨 UI/UX improvement

## ✅ Чек-лист

- [ ] Код следует стилю проекта (ruff + black)
- [ ] Self-review выполнен
- [ ] Комментарии добавлены в сложных местах
- [ ] Документация обновлена (README, ARCHITECTURE, docstrings)
- [ ] Тесты добавлены / обновлены
- [ ] `pytest --cov=app --cov-fail-under=85` проходит локально
- [ ] `ruff check .` без ошибок
- [ ] `black --check .` без diff
- [ ] `qmllint-qt6 app/ui/**/*.qml` без критических ошибок
- [ ] Ручной smoke-test: launch → clicker → aim → macro → recorder → quit
- [ ] Нет новых warnings в консоли
- [ ] Логи работы обновлены в worklog.md (если работаете с subagents)

## 📸 Скриншоты (если применимо)

<!-- Для UI изменений — приложите before/after -->

## 📝 Заметки для ревьюера

<!-- Что важно проверить? Какие подводные камни? -->

## 🧩 Migration guide (если breaking change)

<!-- Что нужно сделать пользователям старой версии для перехода? -->
