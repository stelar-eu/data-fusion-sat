"""
    Implementation of STARFM via github rep starfm4py by Nikolina Mileva.
    Preprocessing (co-registration is performed first)

    @author: C. Jörges, VISTA GmbH
    Date: 11/23

    To DO: Add reading RAS Files instead of TIF Files (use existing code)
"""

# import packages
import time
from osgeo import gdal
import rasterio
import numpy as np
import starfm4py as stp
import matplotlib.pyplot as plt
from parameters import (path, sizeSlices)
from lai_data_fusion import reproj2base

# Measure execution time
start = time.time()

# TO DO: Input images croppen und auf maximal ENMAP extent bringen

# Set the path where the images are stored
path_multi_t0 = 'Q:\\_STELAR\\Sammlung\\Test_Data\\DATA-FUSION\\LAI-Compare\\S2B_33UXP2BP_230505_ICE_DECODED.TIF'
path_multi_t1 = 'NOT DEFINED'
path_hyper_t0 = 'Q:\\_STELAR\\Sammlung\\Test_Data\\DATA-FUSION\\LAI-Compare\\ENMAP_33UXP_230504T101024_PRE_IVPARA.TIF'
path_hyper_t1 = 'Q:\\_STELAR\\Sammlung\\Test_Data\\DATA-FUSION\\LAI-Compare\\ENMAP_33UXP_230905T102533_PRE_IVPARA.TIF'
path_out = 'Q:\\_STELAR\\Sammlung\\Test_Data\\DATA-FUSION\\LAI-Compare\\'

# PreProcessing
reproj2base(inpath=path_hyper_t0, basepath=path_multi_t0, outpath=path_out+'ENMAP_t0.TIF', bands=[4], resampling_method='nearest')
reproj2base(inpath=path_hyper_t1, basepath=path_multi_t0, outpath=path_out+'ENMAP_t1.TIF', bands=[4], resampling_method='nearest')

# update filepaths for starfm inputs
path_hyper_t0 = path_out+'ENMAP_t0.TIF'
path_hyper_t1 = path_out+'ENMAP_t1.TIF'

# To DO: PreProcessing - Funktion: Angabe delete bands
def read_fusion_data:
    """
    Einlesen der Daten, Auswhl Kanäle, etc.
    :return:
    """

# Read the data
product = rasterio.open(path_multi_t0) # High Spatial T0 = Reference Sentinel-2
profile = product.profile
profile.update({'count': 1})
SentinelT0 = rasterio.open(path_multi_t0).read(2) # High Spatial T0 = S2 LAI band 2
ENMAPt0 = rasterio.open(path_hyper_t0).read(1) # Low Spatial T0 = ENMAP LAI band 4 (Preprocessed band 1)
ENMAPt1 = rasterio.open(path_hyper_t1).read(1) # Low Spatial T1 = ENMAP LAI band 4 (Preprocessed band 1)

# Set the path where to store the temporary results
path_fineRes_t0 = 'Temporary\\Tiles_fineRes_t0\\'
path_coarseRes_t0 = 'Temporary\\Tiles_coarseRes_t0\\'
path_coarseRes_t1 = 'Temporary\\Tiles_fcoarseRes_t1\\'

# Flatten and store the moving window patches
fine_image_t0_par = stp.partition(SentinelT0, path_fineRes_t0)
coarse_image_t0_par = stp.partition(ENMAPt0, path_coarseRes_t0)
coarse_image_t1_par = stp.partition(ENMAPt1, path_coarseRes_t1)

print("Done partitioning!")

# Stack the the moving window patches as dask arrays
S2_t0 = stp.da_stack(path_fineRes_t0, SentinelT0.shape)
S3_t0 = stp.da_stack(path_coarseRes_t0, ENMAPt0.shape)
S3_t1 = stp.da_stack(path_coarseRes_t1, ENMAPt1.shape)

shape = (sizeSlices, SentinelT0.shape[1])

print("Done stacking!")

# Perform the prediction with STARFM
for i in range(0, SentinelT0.size - sizeSlices * shape[1] + 1, sizeSlices * shape[1]):

    fine_image_t0 = S2_t0[i:i + sizeSlices * shape[1], ]
    coarse_image_t0 = S3_t0[i:i + sizeSlices * shape[1], ]
    coarse_image_t1 = S3_t1[i:i + sizeSlices * shape[1], ]
    prediction = stp.starfm(fine_image_t0, coarse_image_t0, coarse_image_t1, profile, shape)

    if i == 0:
        predictions = prediction

    else:
        predictions = np.append(predictions, prediction, axis=0)

# Write the results to a .tif file
print('Writing product...')
profile = product.profile
profile.update(dtype='float64', count=1)  # number of bands
file_name = path + 'prediction.tif'

result = rasterio.open(file_name, 'w', **profile)
result.write(predictions, 1)
result.close()

end = time.time()
print("Done in", (end - start) / 60.0, "minutes!")

# Display input and output
plt.imshow(SentinelT0)
plt.gray()
plt.show()
plt.imshow(ENMAPt0)
plt.gray()
plt.show()
plt.imshow(ENMAPt1)
plt.gray()
plt.show()
plt.imshow(predictions)
plt.gray()
plt.show()


