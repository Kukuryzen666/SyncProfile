# SyncProfile: Критические правила безопасности кода

## КРИТИЧЕСКИЙ БАГ: MessagesController НЕ thread-safe

### Проблема
`MessagesController.getUser()`, `putUser()`, `putUserFull()`, `putUsersAndChats()` и другие методы
**НЕЛЬЗЯ вызывать из фонового потока** (`threading.Thread`, `asyncio`, `executor`).

Если вызвать эти методы не с UI-потока — **чаты перестают грузиться**. Telegram
падает в состояние гонки данных внутри своих коллекций.

### Что сломалось (08.2026)
Функция `_apply_all_to_all_accounts` была перенесена в `threading.Thread` с целью
снизить нагрузку на UI-поток. Внутри фонового потока вызывались:

    mc.getUser(uid)      # НЕЛЬЗЯ вне UI-потока
    mc.putUser(u, True)  # НЕЛЬЗЯ вне UI-потока
    ms.getUser(uid)      # НЕЛЬЗЯ вне UI-потока

Результат: чаты перестали загружаться сразу после старта плагина.

### Правило
MessagesController.* и MessagesStorage.* — ТОЛЬКО через run_on_ui_thread()

### Что МОЖНО делать в фоновом потоке
- Сетевые запросы (urllib, requests)
- Работу с кэшем (self._profiles_cache, self._sync_lock)
- Чтение/запись файлов (json.dump, open)

### Что НЕЛЬЗЯ делать в фоновом потоке
- MessagesController.getUser() / putUser() / putUserFull()
- MessagesStorage.getUser() / putUsersAndChats()
- NotificationCenter.postNotificationName() — использовать run_on_ui_thread
- Любые Android View операции

### Правильный паттерн для этого плагина

    def _apply_all_to_all_accounts(self):
        def ui_update_task():
            # Вся работа с MessagesController — здесь, на UI-потоке
            from org.telegram.messenger import UserConfig, MessagesController
            mc = MessagesController.getInstance(acc)
            u = mc.getUser(uid)      # безопасно — мы на UI-потоке
            mc.putUser(u, True)      # безопасно
            ...
        run_on_ui_thread(ui_update_task)  # обязательно

### Рабочая эталонная версия
Файл `sync(1).plugin` (v10.2.26) — эталон. В ней чаты грузятся стабильно.
Перед любыми изменениями `_apply_all_to_all_accounts` — сравнивать с этим файлом.

---

## Архитектурная заметка: GetUserHook как альтернатива итерации

В sync.plugin (компактная версия) нет явной итерации всего кэша профилей.
Вместо этого стоит Xposed хук на MessagesController.getUser():

    class GetUserHook(MethodHook):
        def after_hooked_method(self, param):
            user_obj = param.getResult()
            if user_obj:
                plugin_self._patch_user_tl_object(user_obj)

Telegram сам вызывает getUser() когда рендерит диалог/сообщение — хук
перехватывает и патчит прямо на UI-потоке, без лишней нагрузки.
Это правильный и безопасный подход для этой архитектуры.
