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
