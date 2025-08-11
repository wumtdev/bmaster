# BellMaster

## Система управления интеркомами. Преимущественно используемая в школах.

![Скрин](./img/img1.jpg)

## Требования

- Python 3.8 или выше (рекомендуется 3.11+)
- Поддержка ОС: Windows или Linux

## Установка

### 1. Клонировать репозиторий

```bash
git clone https://github.com/wumtdev/bmaster.git
cd bmaster
```

### 2. Запустить скрипт установки

#### Для Windows:

```bash
setup.bat
```

#### Для Linux/macOS:

```bash
chmod +x setup.sh  # Дать права на выполнение
./setup.sh
```

#### Важные заметки

1. Для пользователей Windows:

   - Если возникают ошибки, попробуйте запускать скрипт от имени администратора
   - Убедитесь что Python добавлен в PATH

2. Для Linux/macOS пользователей:
   - Если используется python3, обновите скрипты: замените `python` на `python3`
   - Может потребоваться установка: `sudo apt install python3-venv`, `sudo apt install python3-pip`

Этот README покрывает основные сценарии установки. Для более экзотичных проблем смотрите раздел FAQ.

## Запуск приложения

После успешной установки запустите основное приложение:

```bash
python main.py
```

## Зависимости проекта

Основные зависимости (автоматически устанавливаются скриптом):

- FastAPI
- Uvicorn
- SoundDevice
- Wauxio
- Wsignals
- APScheduler
- PyJWT

[Полный список зависимостей](./requirements.txt)

## Особенности установки

- Скрипт установки автоматически:
  - Создает виртуальное окружение (.venv)
  - Устанавливает все зависимости из requirements.txt
  - Устанавливает дополнительные зависимости:
    - `wauxio`
    - `wsignals`
- Для аудио-зависимостей на Linux может потребоваться:
  ```bash
  sudo apt-get install portaudio19-dev python3-dev
  ```

## Проблемы при установке

1. Если возникают ошибки с sounddevice:

   - Убедитесь что установлены системные зависимости для PortAudio
   - Windows: установите [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
   - Linux: `sudo apt-get install libportaudio2`

2. Для проблем с компиляцией пакетов:
   - Обновите pip: `python -m pip install --upgrade pip`
   - Убедитесь что у вас установлены последние версии setuptools и wheel

## Тестирование работы

После установки проверьте работоспособность:

```python
python -c "import fastapi; print(fastapi.__version__)"
python -c "import wauxio; print(wauxio.__name__)"
```

## Дополнительная информация

Для работы с проектом рекомендуется использовать:

- Python 3.10+
- Виртуальное окружение (уже создается скриптом)
- При разработке: VS Code/PyCharm с поддержкой Python

---

```
С любовью и терпением разрабатывают и поддерживают проект frum1 и WuMT.
2025-20xx
```
