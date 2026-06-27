# Полезные команды при разработке SportOrg

## Обновление репозитория

* Сохранить несохранённые изменения
  * `git stash`
* Получить изменения из `origin/dev-ank`
  * `git checkout dev-ank`
  * `git fetch origin`
* Переключиться на локальную ветку `master`
  * `git checkout master`
* Получить последние изменения из `upstream`
  * `git fetch upstream`
    * Может написать, что не получается удалить директории `.git/logs/refs/remotes/upstream/workflows` и `.git/refs/remotes/upstream/workflows`
      * нужно вручную удалить эти папки
* Обновить свою локальную ветку `master`
  * `git rebase upstream/master`
* Обновить свой форк на github
  * `git push --force-with-lease origin master`
* Переключиться на ветку `dev-ank`-
  * `git checkout dev-ank`
* Выполнить rebase ветки `dev-ank` на свежую ветку `master`
  * `git rebase master`
    * Разрешить конфликты, если возникнут
    * Может возникнуть ошибка: `warning: could not read '.git/rebase-merge/head-name': No such file or directory`
      * Нужно вручную удалить папку `.git/rebase-merge/`, rebase завершится
* Обновить ветку dev на github
  * `git push --force-with-lease origin dev-ank`
* Вернуть несохранённые изменения
  * `git stash pop`

## Виртуальное окружение

Облачные хранилища плохо дружат с виртуальными окружениями

1. Создать виртуальное окружение. По умолчанию папка `.venv`
2. Переместить папку с виртуальным окружением в AppData
3. Создать Junction link на папку `.venv`

### Установка виртуального окружения

`uv sync --frozen --all-extras --python 3.8`

### Путь до виртуального окружения

`C:\Users\ank\AppData\Local\uv\venv\sportorg-py3.8-C-Users-ank-gDrive-Prog-pysport`

## Запуск Спорторга

Far Manager + ConEmu. Команда записывается в Main Menu Far Manager. Запуск файла по `F2, s`. Ключ `-new_console:b` обрабатывает ConEmu, запускает SportOrg в новой консоле в бэкграунде.

`pwsh -new_console:b -wd C:\Users\ank\gDrive\Prog\pysport\ -c "uv run python SportOrg.pyw \"!\!.!\""`

## Сборка exe

Предварительно: очистить директорию ./build

`uv run python builder.py build_exe`
