web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && python -m gunicorn togai.wsgi -c gunicorn.conf.py
bot: python manage.py runbot
