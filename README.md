# cmip6-publication-site
new CMDIP6 Publication reporting site

    virtualenv2 env
    soruce env/bin/activate
    pip install -r requirments.txt
    python manage.py makemigrations
    python manage.py makemigrations publisher
    python manage.py migrate
    python mangae.py migrate publisher
    python manage.py createsuperuser
     > username:
     > email:
     > password:
     > password:
    python manage.py shell
     > from scripts.data_load import data_load
     > data_load()
    python manage.py runserver
