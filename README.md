# Salon AI Blog — public mirror

Индексируемое зеркало сайта `salon-ai-blog.spru.site`.

На сабдоменах Spru платформа проставляет HTTP-заголовок
`X-Robots-Tag: noindex, nofollow`, поэтому поисковики не берут страницы.
Это зеркало живёт на `jarvis-noosphere-alpha.github.io`, где такого заголовка нет.

Сборка: `publish.py` скачивает исходный сайт, проставляет canonical,
robots и абсолютный `action` формы, затем публикует результат в ветку `gh-pages`.
Форма лида продолжает уходить на живой эндпоинт Spru.

Workflow: `.github/workflows/publish-mirror.yml`.
