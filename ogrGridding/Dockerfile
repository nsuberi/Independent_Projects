FROM python:3.6
MAINTAINER Nathan Suberi <nathan.suberi@wri.org>
ARG NAME=ogrgridding
ENV NAME ${NAME}

# install application libraries
RUN apt-get install -y \
  gdal-bin \
  libgdal-dev \
  libnetcdf-dev \
  netcdf-bin \
  cron \
  && apt-get clean

# install application libraries
RUN pip install --upgrade pip && pip install pandas
RUN pip install -e git+https://github.com/fgassert/cartosql.py.git#egg=cartosql

# Copy the application folder inside the container
RUN mkdir -p /opt/$NAME/data
WORKDIR /opt/$NAME/
COPY contents/ .
VOLUME ./data

# Set user for container security
RUN useradd $NAME
RUN chown -R $NAME:$NAME .
USER $NAME

# Launch script
CMD ["python", "main.py"]
