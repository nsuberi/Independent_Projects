import logging
import sys
import os
from math import ceil

from osgeo import ogr
import geopandas as gpd

### Constants
NUM_INTERSECT = 50
LOG_LEVEL = logging.INFO
SHAPEFILE_LOC = 'data/big_leaf_maple_range_map_&_shapefiles/acermacr.shp'

###
## Accessing remote data
###

def createAndTestGrid(limits, resolution, shapefile):

    outfile = 'data/attempt_at_grid_{}.shp'.format(str(resolution))

    ### ogr code to make a grid
    xmin,xmax,ymin,ymax = limits
    gridHeight = gridWidth = resolution

    # convert sys.argv to float
    xmin = float(xmin)
    xmax = float(xmax)
    ymin = float(ymin)
    ymax = float(ymax)
    gridWidth = float(gridWidth)
    gridHeight = float(gridHeight)

    # get rows
    rows = ceil((ymax-ymin)/gridHeight)
    # get columns
    cols = ceil((xmax-xmin)/gridWidth)

    # start grid cell envelope
    ringXleftOrigin = xmin
    ringXrightOrigin = xmin + gridWidth
    ringYtopOrigin = ymax
    ringYbottomOrigin = ymax-gridHeight

    # create output file
    outDriver = ogr.GetDriverByName('ESRI Shapefile')
    if os.path.exists(outfile):
        os.remove(outfile)
    outDataSource = outDriver.CreateDataSource(outfile)
    outLayer = outDataSource.CreateLayer(outfile,geom_type=ogr.wkbPolygon )
    featureDefn = outLayer.GetLayerDefn()

    # create grid cells
    countcols = 0
    while countcols < cols:
        countcols += 1

        # reset envelope for rows
        ringYtop = ringYtopOrigin
        ringYbottom = ringYbottomOrigin
        countrows = 0

        while countrows < rows:
            countrows += 1
            ring = ogr.Geometry(ogr.wkbLinearRing)
            ring.AddPoint(ringXleftOrigin, ringYtop)
            ring.AddPoint(ringXrightOrigin, ringYtop)
            ring.AddPoint(ringXrightOrigin, ringYbottom)
            ring.AddPoint(ringXleftOrigin, ringYbottom)
            ring.AddPoint(ringXleftOrigin, ringYtop)
            poly = ogr.Geometry(ogr.wkbPolygon)
            poly.AddGeometry(ring)

            # add new geom to layer
            outFeature = ogr.Feature(featureDefn)
            outFeature.SetGeometry(poly)
            outLayer.CreateFeature(outFeature)
            outFeature.Destroy

            # new envelope for next poly
            ringYtop = ringYtop - gridHeight
            ringYbottom = ringYbottom - gridHeight

        # new envelope for next poly
        ringXleftOrigin = ringXleftOrigin + gridWidth
        ringXrightOrigin = ringXrightOrigin + gridWidth

    # Close DataSources
    outDataSource.Destroy()

    ### intersect with shapefiles
    # Read in newly created grid
    new_grid = gpd.GeoDataFrame.from_file(outfile)
    new_grid.crs = {'init' :'epsg:4326'}
    logging.info('New grid shape: {}'.format(new_grid.shape))
    logging.info('New grid head: {}'.format(new_grid.head()))

    # Intersect
    intersection = gpd.sjoin(new_grid, shapefile, how='inner',op='intersects')
    logging.info('Intersection head: {}'.format(intersection.shape))
    logging.info('Intersection head: {}'.format(intersection.tail()))

    unique_intersection = intersection['FID'].unique()
    unique_intersection = new_grid.loc[unique_intersection]

    logging.info('Unique Intersection shape: {}'.format(unique_intersection.shape))
    logging.info('Unique Intersection head: {}'.format(unique_intersection.head()))

    removeExcess(outfile)
    unique_intersection.to_file(driver = 'ESRI Shapefile', filename=outfile)

    return outfile, unique_intersection.shape[0]

def removeExcess(outfile):
    base = os.path.splitext(outfile)[0]
    os.remove(base+'.dbf')
    os.remove(base+'.shx')
    os.remove(base+'.shp')
    try:
        os.remove(base+'.cpg')
        os.remove(base+'.prj')
    except:
        logging.debug('No .cpg or .prj files to delete')

###
## Application code
###

def main():
    logging.basicConfig(stream=sys.stderr, level=LOG_LEVEL)

    ### 1. Load shapefile
    big_maple_rangemap = gpd.GeoDataFrame.from_file(SHAPEFILE_LOC)
    big_maple_rangemap.crs = {'init' :'epsg:4326'}
    logging.info('Shape of data: {}'.format(big_maple_rangemap.shape))
    logging.info('Head of data: {}'.format(big_maple_rangemap.head()))
    logging.info('CRS: {}'.format(big_maple_rangemap.crs))

    ### 2. Find bounding box, use to loop over
    # https://gis.stackexchange.com/questions/266730/filter-by-bounding-box-in-geopandas
    limits = big_maple_rangemap.total_bounds
    logging.info('Bounding box of shapefile: {}'.format(limits))

    resolution = 1.5 # lat/lon degree
    num_intersections = 0
    while num_intersections < NUM_INTERSECT:
        grid, num_intersections = createAndTestGrid(limits, resolution, big_maple_rangemap)
        logging.info('Resolution {} had {} intersections'.format(resolution, num_intersections))
        if num_intersections < 50:
            removeExcess(grid)
            resolution -= .1
