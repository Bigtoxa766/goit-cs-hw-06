# Вибір базового образу
FROM python:3.10-slim

# Встановлення залежностей
RUN pip install pymongo

# Копіюємо файли проекту
COPY . /app
WORKDIR /app

# Відкриваємо порти
EXPOSE 3005 5000

# Запуск сервера
CMD ["python", "main.py"]
