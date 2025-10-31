import rasterio
from rasterio.warp import reproject, Resampling, calculate_default_transform
from rasterio.coords import disjoint_bounds
import numpy as np


def reproj2base(inpath, basepath, outpath, resampling_method, bands=None, plot=False):
    """
    Transform raster file to match the shape and projection of existing raster (co-registration).

    Inputs
    ----------
    inpath : (string) filepath of input raster file
    basepath : (string) path to raster with reference shape and projection
    outpath : (string) path to output raster file (tif)
    bands : (list) specified # band to reproject with default None=All bands
    resampling_method : (string) 'nearest', 'bilinear', 'cubic', 'average'
    plot : (bool) plot the data?
    """
    # ToDo: Add reading RAS Files instead of TIF Files (use existing code)



    # open input file
    with rasterio.open(inpath, 'r') as src:
        #src = rasterio.open(inpath, 'r')
        src_transform = src.transform
        src_nodata = src.nodata
        src_height = src.height
        src_width = src.width
        bb_src=src.bounds
        with rasterio.open(basepath, 'r') as base:
            dst_crs = base.crs
            dst_count = len(bands)
            # check if bounding boxes do intersect
            bb_dst=base.bounds
            if not src.crs == base.crs:
                print(f'CRS of {inpath} and {basepath} do not match, no bbox check ')
            else:
                if disjoint_bounds(bb_src, bb_dst):
                    print(f'Bounding boxes of {inpath} and {basepath} do not intersect')
                    raise ValueError('Bounding boxes of {inpath} and {basepath} do not intersect')
                
            # calculate the output transform matrix
            dst_transform, dst_width, dst_height = calculate_default_transform(
                src.crs,  # input CRS
                dst_crs,  # output CRS
                base.width,  # base width
                base.height,  # base height
                *base.bounds)  # base outer boundaries (left, bottom, right, top)
        # set properties for output
        dst_kwargs = src.meta.copy()
        dst_kwargs.update({"crs": dst_crs,
                           "transform": dst_transform,
                           "width": dst_width,
                           "height": dst_height,
                           "count": dst_count,
                           "nodata": src_nodata})
        #print("Original shape:", src_height, src_width, '\n Affine', src_transform)
        #print("Coregistered to shape:", dst_height, dst_width, '\n Affine', dst_transform)
        # open output
        with rasterio.open(outpath, 'w', **dst_kwargs) as dst:
            #dst=rasterio.open(outpath, 'w', **dst_kwargs)
            # define resampling method
            if resampling_method == 'nearest':
                resampling = Resampling.nearest
            elif resampling_method == 'bilinear':
                resampling = Resampling.bilinear
            elif resampling_method == 'average':
                resampling = Resampling.average
            elif resampling_method == 'cubic':
                resampling = Resampling.cubic
            else: print("No Resampling method specified!")


            # specify amount of bands
            if bands:
                destination = np.zeros((dst_height,dst_width))
                for i, iband in enumerate(bands):
                    band_data = src.read(iband) # read band data as numpy array
                    #min_val=np.min(band_data)
                    #max_val=np.max(band_data)
                    #print(f'Minimum value of band {iband}: {min_val}')
                    #print(f'Maximum value of band {iband}: {max_val}')
                    #bin_edges = [-1000,-990,-950, -900, 0, 1, 2, 3, 4, 5, 6, 7, 8]
                    #hist, bins = np.histogram(band_data, bins=bin_edges)
                    #hist, bins = np.histogram(band_data, bins=10, range=(-1000,-900))
                    #print(hist)
                    #print(bins)
                    # set all values below 0 to -999
                    band_data[band_data <= 0]=-999.0
                    #hist, bins = np.histogram(band_data, bins=bin_edges)
                    #print(hist)

                    try:
                        #max_val=np.max(band_data)
                        reproject(
                            #source=rasterio.band(src, iband),
                            source=band_data,
                            destination=destination, #rasterio.band(dst, i+1), # destination
                            src_transform=src.transform,
                            src_crs=src.crs,
                            src_nodata=-999.0,
                            dst_transform=dst_transform,
                            dst_crs=dst_crs,
                            #dst_nodata=-999.0,
                            resampling=resampling)
                        #hist, bins = np.histogram(destination, bins=bin_edges)
                        #print(hist)
                        dst.write(destination, 1)
                        #max_val=np.max(destination)
                    except Exception as e:
                        print(f'Error in reprojecting band {iband}: {e}')
                        raise e
            else:
                # iterate through all bands and write using reproject function
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=dst_transform,
                        dst_crs=dst_crs,
                        resampling=resampling)

