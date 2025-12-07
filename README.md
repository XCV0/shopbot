# shopbot

Телеграм-бот и WebApp для выбора обедов сотрудниками: пользователи выбирают кафе, смотрят меню и оформляют заказ (доставка в офис или на подносе в ресторане).

Стек:
- **Python** (Flask, aiogram)
- **SQLite**
- **Telegram Bot API + Telegram Mini Apps**
- **systemd** для запуска сервисов

---

## 1. Подготовка сервера

### Требования

- ОС семейства Linux (например, Ubuntu 20.04+)
- Установлено:
  - `git`
  - `python3`, `python3-venv`, `python3-pip`
- Доменное имя, указывающее на ваш сервер (A-запись в DNS)
- SSL-сертификат:
  - цепочка сертификатов — `cert.pem`
  - приватный ключ — `key.pem`

---

## 2. Клонирование репозитория и установка зависимостей

Склонируйте репозиторий и перейдите в директорию проекта:

```bash
git clone https://github.com/XCV0/shopbot
cd shopbot
```

Создайте виртуальное окружение:

```bash
python3 -m venv venv
source venv/bin/activate
```

Установите зависимости:

```bash
pip install -r requirements.txt
```

---

## 3. Настройка SSL и DNS

1. **SSL-сертификаты**

   Поместите в **корень проекта** (`shopbot/`) файлы:
   - `cert.pem` — файл цепочки сертификатов;
   - `key.pem` — приватный ключ.

2. **DNS**

   В панели управления доменом создайте A-запись на IP вашего сервера, например:

   - `example.com  ->  YOUR_SERVER_IP`

   Этот домен далее будет использоваться как `WEBAPP_URL` в боте.

---

## 4. Запуск WebApp (Flask-приложения)

WebApp можно поднимать по-разному (в т.ч. через Docker), но базовый вариант - запуск через `systemd`.

### 4.1. Создание unit-файла для Flask

Откройте файл сервиса:

```bash
sudo nano /etc/systemd/system/flaskapp.service
```

Пример содержимого:

```ini
[Unit]
Description=Flask App
After=network.target

[Service]
User=root
WorkingDirectory=<ПУТЬ_К_ПАПКЕ_shopbot>
ExecStart=<ПУТЬ_К_ПАПКЕ_shopbot>/venv/bin/python webapp.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Замените:

- `<ПУТЬ_К_ПАПКЕ_shopbot>` на реальный путь к проекту, например `/root/shopbot`.

### 4.2. Перезапуск systemd и запуск сервиса

```bash
sudo systemctl daemon-reload
sudo systemctl enable flaskapp
sudo systemctl start flaskapp
```

Проверка статуса:

```bash
sudo systemctl status flaskapp
```

---

## 5. Развёртывание Telegram-бота

### 5.1. Настройка токена бота

Откройте файл `bot.py` и вставьте токен, полученный от **BotFather**  
(ориентировочно около 130-й строки, в месте, где создаётся объект `Bot`), например:

```python
BOT_TOKEN = "ВАШ_ТОКЕН_ОТ_BOTFATHER"
```

### 5.2. Настройка URL WebApp и режима презентации

Откройте файл `handlers/users.py` и измените:

1. **Домен WebApp**:

```python
WEBAPP_URL = "https://your-domain.com/"
```

Замените `https://your-domain.com/` на ваш реальный домен (тот, на который указывает A-запись).

2. **Режим презентации**:

```python
PRESENTATION_MODE = False
```

- `False` — бот работает только с зарегистрированными сотрудниками.
- `True` — бот отвечает всем пользователям (режим демо/презентации).

### 5.3. Создание unit-файла для бота

```bash
sudo nano /etc/systemd/system/shopbot.service
```

Пример содержимого:

```ini
[Unit]
Description=Shop Bot
After=network.target

[Service]
User=root
WorkingDirectory=<ПУТЬ_К_ПАПКЕ_shopbot>
ExecStart=<ПУТЬ_К_ПАПКЕ_shopbot>/venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Замените:

- `<ПУТЬ_К_ПАПКЕ_shopbot>` на реальный путь к каталогу проекта.

### 5.4. Перезапуск systemd и запуск бота

```bash
sudo systemctl daemon-reload
sudo systemctl enable shopbot
sudo systemctl start shopbot
```

Проверка статуса:

```bash
sudo systemctl status shopbot
```

---

## 6. Управление сервисами

### Flask (WebApp)

```bash
sudo systemctl start flaskapp
sudo systemctl stop flaskapp
sudo systemctl restart flaskapp
sudo systemctl status flaskapp
```

### Telegram-бот

```bash
sudo systemctl start shopbot
sudo systemctl stop shopbot
sudo systemctl restart shopbot
sudo systemctl status shopbot
```

---

## 7. Обновление проекта

При обновлении кода выполните:

```bash
cd /ПУТЬ/К/shopbot
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart flaskapp
sudo systemctl restart shopbot
```

---

## 8. Альтернатива: запуск через Docker

Проект можно развернуть и в Docker-окружении (отдельные контейнеры для WebApp и бота).  
В текущей версии описан базовый способ запуска через `systemd`.  
Docker-конфигурация (например, `Dockerfile` и `docker-compose.yml`) может быть добавлена позднее.
