# Gemini: Imahunga on docker

## Versions

App | Version
--- | ---
Python | 3.6.6
Django | 1.11

## What is included

- PostgreSQL as a Django database

## Docker Compose containers

- db (Django PostgreSQL database)
- web (Django application)

# Setup & Run

## Run inside docker

    # In your computer yo need to have set:
    # API_KEY_DEUTSCHER_SPORTAUSWEIS
    # SOCIAL_AUTH_EVENTBRITE_KEY
    # SOCIAL_AUTH_EVENTBRITE_SECRET

    # collect your own Enviroments Variables
    python enviroment_keys.py

    # build docker containers
    docker-compose build

    # option 1: run 1 instance of web
    docker-compose up

You can also run manage.py commands using docker environment, for example tests.

    docker-compose run web python ./manage.py test

See docker's logs

    docker-compose logs --tail 5

## Run from local machine

    # Install requirements
    virtualenv env
    source env/bin/activate
    pip install -r requirements.txt

    # Move to 'imahunga' folder
    cd imahunga

    # Start application on another console
    python manage.py runserver