# Рефакторинг `Race.to_dict_partial` → именованные методы

**Дата:** 2026-07-01  
**Файлы:** `sportorg/models/memory.py`, `sportorg/gui/dialogs/report_dialog.py`

---

## Контекст

`Race.to_dict_partial` строит частичный словарь гонки для шаблонов (HTML/DOCX/CSV).  
Функция принимает 5 необязательных списков; вызывающий код всегда передаёт все 5,  
из которых ровно один непустой — в зависимости от активной вкладки в `report_dialog.py`.

### Диагностированные проблемы

| # | Проблема | Место |
|---|----------|-------|
| 1 | Нет type hints (нарушение mypy strict) | сигнатура |
| 2 | Мутация списков caller: `group_list.append(...)`, `person_list.append(...)` | строки 1748, 1757 |
| 3 | Несогласованная семантика: `course_list`/`group_list` дополняют `person_list`, а `orgs_list`/`result_list` его заменяют | строки 1759–1773 |
| 4 | `group_list` хранит строки-имена; все остальные — объекты | строки 1748, 1754 |
| 5 | O(n²) проверка `person not in person_list` в цикле | строки 1755, 1764 |
| 6 | «Implicit dispatch»: режим работы определяется тем, какой параметр непуст | всё тело |

---

## Решение: именованные публичные методы + приватный `_build_partial`

### Новые методы в `Race`

```python
def _build_partial(self, persons: List[Person]) -> Optional[Dict[str, Any]]:
    """Assembles the partial race dict from a resolved person list."""

def partial_for_persons(self, persons: List[Person]) -> Optional[Dict[str, Any]]: ...
def partial_for_groups(self, groups: List[Group]) -> Optional[Dict[str, Any]]: ...
def partial_for_courses(self, courses: List[Course]) -> Optional[Dict[str, Any]]: ...
def partial_for_orgs(self, orgs: List[Organization]) -> Optional[Dict[str, Any]]: ...
def partial_for_results(self, results: List[Result]) -> Optional[Dict[str, Any]]: ...
```

`to_dict_partial` удаляется.

### `_build_partial` — контракт

Принимает итоговый список `Person`. Возвращает `None` если список пуст.  
Все выходные списки в порядке модели (`self.groups`, `self.courses`, `self.organizations`, `self.results`).

```python
def _build_partial(self, persons: List[Person]) -> Optional[Dict[str, Any]]:
    if not persons:
        return None
    person_set = set(persons)
    person_groups = {p.group for p in persons if p.group}
    person_orgs   = {p.organization for p in persons if p.organization}

    return_groups  = [g for g in self.groups       if g in person_groups]
    group_courses  = {g.course for g in return_groups if g.course}
    return_courses = [c for c in self.courses      if c in group_courses]
    return_orgs    = [o for o in self.organizations if o in person_orgs]
    return_results = [r for r in self.results      if r.person in person_set]

    return {
        "object":        self.__class__.__name__,
        "id":            str(self.id),
        "data":          self.data.to_dict(),
        "settings":      self.settings.copy(),
        "organizations": [o.to_dict() for o in return_orgs],
        "courses":       [c.to_dict() for c in return_courses],
        "groups":        [g.to_dict() for g in return_groups],
        "results":       [r.to_dict() for r in return_results],
        "persons":       [p.to_dict() for p in persons],
    }
```

### Публичные методы — логика разрешения в `persons`

| Метод | Логика |
|-------|--------|
| `partial_for_persons(persons)` | все `self.persons`, входящие в `set(persons)` |
| `partial_for_groups(groups)` | все `self.persons`, чья `person.group in groups_set` |
| `partial_for_courses(courses)` | группы с `group.course in courses_set`, затем как groups |
| `partial_for_orgs(orgs)` | все `self.persons`, чья `person.organization in orgs_set` |
| `partial_for_results(results)` | все `self.persons`, чья `person in {r.person for r in results}` |

Во всех методах промежуточная фильтрация строится через `set` (O(1) lookup),  
финальный список `persons` собирается итерацией по `self.persons` — порядок модели гарантирован во всех случаях.

### Изменения в `report_dialog.py`

```python
# Было (tab == 2, группы):
group_list = [obj.groups[i].name for i in mw.get_selected_rows()]
races_dict = [r.to_dict_partial(person_list=[], result_list=[],
              group_list=group_list, orgs_list=[], course_list=[])
              for r in races()]

# Станет:
group_list = [obj.groups[i] for i in mw.get_selected_rows()]
races_dict = [r.partial_for_groups(group_list) for r in races()]
```

Аналогично для остальных четырёх вкладок.

---

## Инварианты (для тестов)

1. `partial_for_groups([])` → `None`
2. Порядок `groups` в выходном dict совпадает с порядком `self.groups`, независимо от порядка выборки
3. `partial_for_groups(groups)` не содержит персон/результатов из невыбранных групп
4. `partial_for_courses(courses)` — выходной `groups` содержит только группы, привязанные к переданным дистанциям
5. `partial_for_results(results)` — выходной `persons` в порядке `self.persons`, не в порядке `results`

---

## Что остаётся вне скоупа

- Изменение формата выходного dict (обратная совместимость с шаблонами сохраняется)
- Рефакторинг `to_dict` (полный экспорт — отдельная функция, не затронута)
- Добавление новых режимов фильтрации

---

## Аддендум (2026-07-11): точный выбор результатов в `partial_for_results`

**Проблема.** Строка `return_results = [r for r in self.results if r.person in person_set]`
возвращала ВСЕ результаты персон выбранных строк, а не сами выбранные `Result`. Если у
участника несколько результатов в одной гонке (перезабег, повторное считывание чипа), выбор
одной строки на вкладке «Результаты» тянул за собой все его результаты.

**Решение.** `_build_partial` принимает необязательный `results`; когда он задан,
`return_results` фильтруется по `.id` переданных объектов (`Result`, как и `Course`, не
хешируется — кастомный `__eq__` без `__hash__`, поэтому containment по неизменяемому `.id`).
`partial_for_results` пробрасывает `results` в `_build_partial`. Остальные `partial_for_*`
не меняются — для выбора группы/персоны/дистанции/коллектива правильно показывать все
результаты.

6. `partial_for_results(results)` — выходной `results` содержит **только** переданные объекты
   (по `.id`), даже если у их персон есть другие результаты в `self.results`; порядок — как в
   `self.results`, не в порядке `results`.

---

## Аддендум (2026-07-12): кросс-дневной выбор для многодневных соревнований

**Проблема.** Многодневное соревнование = несколько отдельных `Race` (по одному на день).
`Person`/`Group`/`Organization` используют identity по объекту и не пересекают границу дня.
`report_dialog` строит выбор по текущему дню (`obj = race()`) и передаёт этот же список во
**все** дни. Для не-активных дней `partial_for_*` не находит совпадений по identity →
`_build_partial([])` → `None`. Многодневные шаблоны («сумма») итерируют весь `races` и на
каждом дне вызывают `racePreparation(r)`, обращаясь к `r.persons`/`r.groups`/… — `null`-день
роняет шаблон (`TypeError: can't access property "persons", race is null`). Вдобавок выбор был
чисто поточным: сумма по всем дням для выбранных атлетов не собиралась (показывался только
текущий день).

**Решение.** Порог — `len(races()) > 1`.

- **Однодневные (`len == 1`)** — путь не меняется; поведение `partial_for_*` и инвариант 6
  сохраняются (точный выбор результатов).
- **Многодневные (`len > 1`)** — выбор на текущем дне сводится к множеству `multi_day_id`
  (`ФИО + группа`), одинаково для всех пяти вкладок; каждый день отдаёт свой партиал через
  новый метод. Разрешение «по атлету»: выбор группы/дистанции/коллектива сводится к персонам
  текущего дня в этих сущностях, далее — к их `multi_day_id`.

**Новый метод.**
```python
def partial_for_multi_day_ids(self, ids: Set[str]) -> Dict[str, Any]:
    persons = [p for p in self.persons if p.multi_day_id in ids]
    return self._build_partial(persons) or self._empty_partial()
```
`_empty_partial()` — валидный dict с `id`/`data`/`settings` и пустыми массивами
(`organizations`/`courses`/`groups`/`persons`/`results`). **Никогда не `None`**, поэтому
`racePreparation` на дне без участников делает 0 итераций и не падает. `_build_partial(persons)`
уже собирает самодостаточный dict дня (персоны + их группы/дистанции/коллективы/результаты
именно этого дня) — ровно то, что нужно `racePreparation`, который линкует объекты по id
внутри одного дня.

**`report_dialog.apply_changes_impl`.**
```python
if _settings["selected"]:
    if len(races()) > 1:                        # многодневные
        ids = selected_multi_day_ids(obj, mw)   # per-tab, текущий день → set[str]
        races_dict = [r.partial_for_multi_day_ids(ids) for r in races()]
    else:                                        # однодневные — как сейчас
        if mw.current_tab == 0:
            races_dict = [obj.partial_for_persons(person_list)]
        elif mw.current_tab == 1:
            races_dict = [obj.partial_for_results(result_list)]
        # … группы/дистанции/коллективы
```
`selected_multi_day_ids` по вкладке (на текущем дне `obj`):

| Вкладка | `ids` |
|---------|-------|
| Участники | `{obj.persons[i].multi_day_id}` |
| Результаты | `{obj.results[i].person.multi_day_id}` (если есть person) |
| Группы | `multi_day_id` персон, чья `group` в выбранных группах |
| Дистанции | `multi_day_id` персон, чья `group.course` в выбранных дистанциях |
| Коллективы | `multi_day_id` персон, чья `organization` в выбранных коллективах |

**Инварианты (дополнение).**
7. `partial_for_multi_day_ids(ids)` **никогда** не возвращает `None`; для дня без совпадений —
   валидный пустой dict (`racePreparation` не падает).
8. День отдаёт своих персон с `multi_day_id in ids` в порядке `self.persons`; их результаты —
   все результаты этих персон **в этом дне**, в порядке `self.results`.
9. Для `len(races()) == 1` активен прежний per-tab путь; инвариант 6 сохраняется.

**Вне скоупа.** Кросс-дневное сопоставление по чему-либо, кроме `multi_day_id` (ФИО + группа);
изменение самих многодневных HTML-шаблонов.
