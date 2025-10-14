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


RUN pip3 install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org psycopg2


# # Add for ODBC on June 13,2023
# # PYODBC DEPENDENCES
# RUN apt-get install -y tdsodbc unixodbc-dev
# RUN apt install unixodbc -y
# RUN apt-get clean -y
# ADD odbcinst.ini /etc/odbcinst.ini

# # DEPENDECES FOR DOWNLOAD ODBC DRIVER
# RUN apt-get install -y curl
# RUN apt-get install apt-transport-https 
# RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
# RUN curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list
# RUN apt-get update

# # INSTALL ODBC DRIVER
# RUN ACCEPT_EULA=Y apt-get install msodbcsql17 --assume-yes

# # CONFIGURE ENV FOR /bin/bash TO USE MSODBCSQL17
# RUN echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bash_profile 
# RUN echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bashrc 
# # ----End-----


# RUN apt-get install freetype-dev musl-dev libpng-dev

	#libjpeg-dev libjpeg8-dev libpng3 libfreetype6-dev

ENV LIBRARY_PATH=/lib:/usr/lib

# RUN apt-get install --no-cache --virtual .build-deps build-base linux-headers \
#     && pip3 install Pillow==5.4.1
RUN pip3 install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org Pillow==5.4.1

RUN apt-get install -y curl
RUN apt-get install -y sudo
# build-base unixodbc-dev unixodbc freetds-dev && pip3 install pyodbc

RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org ipython

RUN apt-get install iputils-ping


ENV LIBRARY_PATH=/lib:/usr/lib

WORKDIR /usr/src/web

# set environment variables
# Added by Chutchai on July 24,2020
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


COPY ./requirements.txt /usr/src/web

RUN pip3 install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --upgrade pip
RUN pip3 install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --no-cache-dir -r requirements.txt

#ENTRYPOINT ["python"]
COPY . /usr/src/web

COPY ./requirements.txt /usr/src/web

RUN pip3 install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --upgrade pip
RUN pip3 install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt


COPY . /usr/src/web

RUN chmod a+x docker-entrypoint.sh
ENTRYPOINT ["/usr/src/web/docker-entrypoint.sh"]