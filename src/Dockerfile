# FROM python:3.7.5-alpine
FROM gijzelaerr/snap7:latest

# RUN apt-get install libpq
RUN apt-get update
RUN apt-get install build-essential
# RUN apt-get install jpeg-dev
RUN apt-get install -y libjpeg-dev
RUN apt-get install -y zlib1g
# jpeg-dev zlib-dev

RUN apt-get install gcc
# RUN apt-get install unixodbc-dev
RUN apt-get install python3-dev

RUN apt-get -y install postgresql-12
RUN apt-get -y install musl-dev
RUN apt-get -y install postgresql-client-12
# RUN apt-get install unixodbc-dev
    # python3-dev \
    # musl-dev \
    # postgresql-dev \
    # && pip install --no-cache-dir psycopg2 \
# RUN apt-get del --no-cache .build-deps

# Installing and build python module
# RUN apt-get install python-pip
RUN apt-get install python3

RUN apt-get install libpq-dev


RUN pip3 install psycopg2


# RUN apt-get install freetype-dev musl-dev libpng-dev

	#libjpeg-dev libjpeg8-dev libpng3 libfreetype6-dev

ENV LIBRARY_PATH=/lib:/usr/lib

# RUN apt-get install --no-cache --virtual .build-deps build-base linux-headers \
#     && pip3 install Pillow==5.4.1
RUN pip3 install Pillow==5.4.1

RUN apt-get install -y curl
RUN apt-get install -y sudo
# build-base unixodbc-dev unixodbc freetds-dev && pip3 install pyodbc

RUN pip install ipython

RUN apt-get install iputils-ping


ENV LIBRARY_PATH=/lib:/usr/lib

WORKDIR /usr/src/web

# set environment variables
# Added by Chutchai on July 24,2020
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1


COPY ./requirements.txt /usr/src/web

RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir -r requirements.txt

#ENTRYPOINT ["python"]
COPY . /usr/src/web

COPY ./requirements.txt /usr/src/web

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt


COPY . /usr/src/web

RUN chmod a+x docker-entrypoint.sh
ENTRYPOINT ["/usr/src/web/docker-entrypoint.sh"]