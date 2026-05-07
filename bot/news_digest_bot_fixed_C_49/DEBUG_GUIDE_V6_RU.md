# Debug Guide v6

Если бот пишет `найдено 0`, теперь нужно смотреть не только `source_fetch_empty`, но и `candidate_decision`.

Примеры интерпретации:

- `raw_count > 0`, но `accepted_count=0`: поиск нашёл ссылки, фильтры отбраковали их.
- `candidate_decision status=old`: статья слишком старая, это ожидаемый reject.
- `candidate_decision status=weak_but_usable`: статья без verified date, но OpenRouter snippet достаточно прямой.
- `candidate_decision reason=topic_news_hub_page`: это страница-раздел, не статья.
- `candidate_decision reason=wrong_entity_context`: совпала не та сущность.

Для следующего ревью кидай `search_debug_only.txt`, а не скриншоты.
