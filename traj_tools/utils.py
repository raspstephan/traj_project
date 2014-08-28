"""
utils module
------------

Contains helpful functions outside of core functionality.

"""

import glob
import os
import numpy as np
import netCDF4 as nc
import cosmo_utils.pywgrib as pwg
import fortran.futils as futils
import cPickle



####################
### Helper Functions
####################


def create_startfile(lonmin, lonmax, dlon, 
                     latmin, latmax, dlat, 
                     zmin, zmax, dz, outname,
                     zfilter = True, cfile = None,
                     refdate = None):
    """
    Creates a trajectory start file in output directory
    
    Parameters
    ----------

    lonmin : float
      Lower boundary of longitude
    lonmax : float
      Upper boundary of longitude
    dlon : float
      longitude increment
    latmin : float
      Lower boundary of latitude
    latmax : float
      Upper boundary of latitude
    dlat : float
      latitude increment
    zmin : float
      Lower height boundary [m]
    zmax : float
      Upper height boundary [m]
    dz : float
      Height increment [m]
    outname : str
      Path to output directory, plus prefix
    zfilter : bool
      If True, trajectories which are "under ground" are filtered out. 
      cfile has to be specified! 
    cfile : str
      Location of COSMO EU constants file
    refdate : str
      Reference date to be written as a header
      
    Examples
    --------
    
    >>> import traj_tools as trj
    >>> cfile = '/home/scratch/users/stephan.rasp/Case1_20070720/d2euout/lfff00000000c'
    >>> trj.utils.create_startfile(-5, 5, 0.25, -7, 7, 0.25, 1000, 5000, 250, 
    >>>                            './case1_coarse.sf', zfilter = True,
    >>>                            cfile, '20070720')
    
    """
    
    suff = '.sf'
    
    f = open(outname + suff, 'w+')
    if refdate == None:
        f.write('Reference Date N/A\n')
    else:
        f.write('Reference Date ' + refdate + '\n')
    f.write('lon lat z\n')
    f.write('-----------------\n')
    
    # Create lon and lat arrays
    lonlist = list(np.arange(lonmin, lonmax + dlon, dlon))
    latlist = list(np.arange(latmin, latmax + dlat, dlat))
    zlist = list(np.arange(zmin, zmax + dz, dz))
    
    if zfilter:
        if cfile == None:
            raise Exception('No cfile give for filter')
        hh = pwg.getfieldobj(cfile, 'HH')
        
    print 'Output file is:', outname + suff
    print 'Unfiltered number of trajectories:', \
          len(lonlist) * len(latlist) * len(zlist)
    
    trjcount = 0
    
    for lon in lonlist:
        for lat in latlist:
            if zfilter:
                # Interpolate to closest x and y indices
                xind = (np.abs(hh.lons - lon)).argmin()
                yind = (np.abs(hh.lats - lat)).argmin()
                
                # Get nearest z value
                hhint = hh.data[-1, yind, xind]
                
                # Filter out values in zlist which are below hhint
                zlisttmp = list(np.array(zlist)[np.array(zlist) > hhint])
                
            else:
                zlisttmp = zlist
               
            for z in zlisttmp:
                lontmp = '%3.3f' % (lon)
                lontmp = (8 - len(lontmp)) * ' ' + lontmp
                lattmp = '%2.3f' % (lat)
                lattmp = (7 - len(lattmp)) * ' ' + lattmp
                ztmp = '%4.3f' % (z)
                ztmp = (8 - len(ztmp)) * ' ' + ztmp
                line = (' ' + lontmp + ' ' + lattmp + ' ' + ztmp)
                assert (len(line) == 26), \
                        'Start file line does not have correct length'
                f.write(line + '\n')
                trjcount += 1
    
    print 'Total number of trajectories:', trjcount
    print 'Filtered out:', len(lonlist) * len(latlist) * len(zlist) - trjcount
    
    f.close() 
                    
                

def calc_theta(files):
    """
    Adds Potential Temperature as a Variable to given netCDF files. 
    The new variable is called 'THETA'.
    
    Parameters
    ----------
    
    files : List or string
      Either a list of all netCDF files to be considered, 
      or the path to the directory containing .nc files. 
    
    """
    
    # Define constants
    P0 = 1.e5   # reference pressure [Pa]
    R = 287.    # specific gas constant dry air [J K-1 kg-1]
    CP = 1004.  # specific heat at constant pressure [J K-1 kg-1]
    
    
    # Checking if filelist needs to be created
    if type(files) == list:
        filelist = files
    elif type(files) == str:
        files = os.path.normpath(files) + '/'
        filelist = sorted(glob.glob(files + '*.nc'))
    else:
        raise Exception('Wrong type for files.')
    
    assert (len(filelist) > 0), 'No files selected.'
    
    # Create new files
    thetalist = []
    for f in filelist:
        thetaf = f.rstrip('.nc') + '_theta.nc'
        thetalist.append(thetaf)
        os.system('cp ' + f + ' ' + thetaf)
    
    # Iterate over files in filelist
    for f in thetalist:
        print 'Open file:', f 
        rootgrp = nc.Dataset(f, 'a')
        
        # Read file arrays needed for calculation
        pmat = rootgrp.variables['P'][:, :] * 100.   # Convert to SI Units
        tmat = rootgrp.variables['T'][:, :]

        # Add new array to netCDF file
        theta = rootgrp.createVariable('THETA', 'f4', ('time', 'id'))
        theta[:, :] = tmat * ((P0 / pmat) ** (R / CP))
        rootgrp.close()
        
        
    return thetalist
    

def convert_pickle2netcdf(indir, outdir):
    """
    Converts pickled trajectory files to NetCDF files, so they can be used with
    this version of traj_tools
    
    Parameters
    ----------
    indir : string
      Path to directory containing GRIB files
    outdir : string
      Path to directory where netcdf files are created
    """
    
    # Specifics for Case0
    pnum = 7   # ptracer
    trjstart = 360 * 60   # Trj start after model start in secs
    dt = 300   # Save time interval in secs
    tsteps = 1369   # Max time steps in pickled files
    
    # Create filelist
    inprefix = '/test_case_'
    filelist = sorted(glob.glob(indir + inprefix + '*'))
    
    # Output prefix
    savebase = outdir + '/traj_t' 
    
    # Set counter
    fcount = 1
    
    # loop over all files
    for fn in filelist:
        print 'Converting file:', fn
        
        # Load pickled files and extract data
        f = open(fn, 'r')
        spec = cPickle.load(f)
        mat = cPickle.load(f)
        f.close()
        
        # Check for starting time
        tstart = np.nonzero(mat[0, pnum, :])[0][0]   # Start index of first traj
        
        # Check if mat needs to be split
        if np.where(mat[:, pnum, tstart] == 0)[0].shape[0] != 0:
            splitind = np.where(mat[:, pnum, tstart] == 0)[0][0]
            if np.nonzero(mat[splitind, pnum, :])[0].shape[0] != 0:
                tstart2 = np.nonzero(mat[splitind, pnum, :])[0][0]
            else:
                print 'Arrays contain only zeros! END!'
                break
            
            # Swap axes
            conmat = np.swapaxes(mat[:splitind, :, tstart:], 0, 2)
            conmat2 = np.swapaxes(mat[splitind:, :, tstart2:], 0, 2)
            
            # First file
            print '2'
            _write2netcdf(conmat, tstart, savebase, fcount)
            fcount = 1
            # Second file
            print '3'
            _write2netcdf(conmat2, tstart2, savebase, fcount)
            fcount += 1
        
        else:
            # Swap axes
            conmat = np.swapaxes(mat[:, :, tstart:], 0, 2)  
            
            # Just one file
            print '1'
            _write2netcdf(conmat, tstart, savebase, fcount)
            fcount += 1
        
        
def _write2netcdf(conmat, tstart, savebase, fcount):
    """
    To be used inside this function
    
    Parameters
    ----------
    conmat : np.array
        Converted and trimmed matrix
    savename : string
        Path of new netCDF file
    
    """
    # Specifics for Case0, see above (repeated here for convenience)
    trjstart = 360 * 60   # Trj start after model start in secs
    dt = 300   # Save time interval in secs
    tsteps = 1369   # Max time steps in pickled files
    
    # Create savename
    savename = (savebase + str(360 + tstart * 5).zfill(6) + 
                '_p' + str(fcount).zfill(3) + '.nc')
    
    # Create time array
    tarray = np.arange(tstart * dt + trjstart, 
                       tsteps* dt + trjstart, dt)
    
    # Create NetCDF file
    print 'Creating netCDF file:', savename
    rootgrp = nc.Dataset(savename, 'w')
    # Create dimensions
    time = rootgrp.createDimension('time', tarray.shape[0])
    id = rootgrp.createDimension('id', conmat.shape[2])
    print tarray.shape[0], conmat.shape[2]
    # Create variables
    times = rootgrp.createVariable('time', 'f4', ('time', ))
    lon = rootgrp.createVariable('longitude', 'f4', ('time', 'id', ))
    lat = rootgrp.createVariable('latitude', 'f4', ('time', 'id', ))
    z = rootgrp.createVariable('z', 'f4', ('time', 'id', ))
    p = rootgrp.createVariable('P', 'f4', ('time', 'id', ))
    # Fill variables
    times[:] = tarray
    lon[:, :] = conmat[:, 0, :]
    lat[:, :] = conmat[:, 1, :]
    z[:, :] = conmat[:, 2, :]
    p[:, :] = conmat[:, 7, :]
    
    rootgrp.close()
        
    


####################################################
# Functions used in core
####################################################

def _delta(filelist, tracer):
    """
    Calculate difference of given tracer between min und max 'P' values
    
    Parameters
    ----------
    filelist : list
      List of saved NetDCF file locations
    yspan : float
      Ascent criterion in y-direction
    tracer : str 
      COSMO name of y-axis variable
      
    Returns
    -------
    deltaarray : np.array
    
    """
    # Initialize lists, convert to np.array later
    deltaarray = []
    
    for f in filelist:
        print 'Opening file:', f
        pmat = nc.Dataset(f, 'r').variables['P'][:, :]
        trcmat = nc.Dataset(f, 'r').variables[tracer][:, :]
        for j in range(pmat.shape[1]):
            parray = pmat[:, j][np.isfinite(pmat[:, j])]
            trcarray = trcmat[:, j][np.isfinite(trcmat[:, j])]
            minind = parray.argmin()
            maxind = parray.argmax()
            if minind < maxind:
                delta = trcarray[maxind] - trcarray[minind]
            else:
                delta = trcarray[minind] - trcarray[maxind]
            if tracer == 'POT_VORTIC' and delta > 0.00005:
                delta = np.nan
                print 'Detected irregulat PV value, set to NaN!'
            deltaarray.append(delta)

    return np.array(deltaarray)
            
    
    


def _minasct(filelist, yspan, tracer, dtrj):
    """
    Calculate minimum ascent time for all trajectories from NetCDF files.
    
    Parameters
    ----------
    filelist : list
      List of saved NetDCF file locations
    yspan : float
      Ascent criterion in y-direction
    tracer : str 
      COSMO name of y-axis variable
     
    Returns
    -------
    ascdata : tuple
      Tuple containing three np.arrays:
      * Minimum ascent time
      * Index of ascent start
      * Index of ascent stop
    
    """
    
    # Initialize lists, convert to np.array later
    asct = []
    ascstart = []
    ascstop = []
    
    if tracer == 'P':
        flip = True
    else:
        flip = False
    
    for f in filelist:
        print 'Opening file:', f
        rootgrp = nc.Dataset(f, 'r')
        mat = rootgrp.variables[tracer][:, :]
        trjstart = int(rootgrp.variables['time'][0] / 60) / 5
        for j in range(mat.shape[1]):
            asctup = _minxspan(mat[:, j], yspan, flip)
            asct.append(asctup[0])
            ascstart.append(asctup[1] + trjstart)
            ascstop.append(asctup[2] + trjstart)
    assert (len(asct) == len(ascstart) == len(ascstop)), \
            'Array lengths do not match'
    ascdata = (np.array(asct) * dtrj, np.array(ascstart) * dtrj, 
               np.array(ascstop) * dtrj)
    return ascdata
            

def _minxspan(array, yspan, flip = False):
    """
    Returns the minimum time steps needed to conver given criterion.
    Automatically filters out zero and nan values. If yspan is not fulfilled, 
    returns np.nan. 
    
    Parameters
    ----------
    array : np.array
      Input array
    yspan : float
      Ascent criterion in y-direction
    flip : bool
      If True array will be flipped (e.g. use for 'P')
    
    Returns
    -------
    xspan : int
      Time steps for criterion
    istart : int
      Start index of ascent
    istop : int
      End index of ascent
    
    """
    
    # Filter out nans and zeros
    array = array[np.isfinite(array)]
    array = array[array != 0]

    # Flip array if needed
    if flip:
        array = -array 

    # Check if criterion is met
    #print array
    if array.shape[0] == 0:
        xspan = np.nan
        istart = np.nan
        istop = np.nan
    elif np.amax(array) - np.amin(array) < yspan:
        xspan = np.nan
        istart = np.nan
        istop = np.nan
    else:
        # Use Fortran implementation, use 0 as error values
        xspan, istart, istop  = futils.futils.minxspan(array, yspan, 
                                                        len(array) + 1, 0, 0)
        
        # Check if output is correct. NOTE: THIS IS A POTENTIAL BUG!!!
        if (istart < 0) and (istop < 0):
            xspan = np.nan
            istart = np.nan
            istop = np.nan
            
        #assert ((xspan > 0) and (xspan <= len(array)) and (istart >= 0) 
                #and (istop >= 0)), \
                #'One of the minxspan outputs is zero or negative.'
            
    return [xspan, istart, istop]
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

