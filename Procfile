web: python manage.py makemigrations --noinput && python manage.py migrate --noinput && python manage.py collectstatic --noinput && python -m gunicorn togai.wsgi --log-file -
bot: python manage.py makemigrations --noinput && python manage.py migrate --noinput && python manage.py runbot
