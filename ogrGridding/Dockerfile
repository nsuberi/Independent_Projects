FROM ecarrara/python-gdal
MAINTAINER Nathan Suberi <nathan.suberi@wri.org>
ARG NAME=ogrgridding
ENV NAME ${NAME}

# install application libraries
RUN apt-get update && apt-get install -y \
  libspatialindex-dev \
  && apt-get clean

# RUN pip install -e git+https://github.com/fgassert/cartosql.py.git#egg=cartosql
RUN pip install --upgrade pip && pip install geopandas rtree

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
