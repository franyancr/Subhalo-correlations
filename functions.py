from __future__ import division
import numpy as np
import matplotlib.pyplot as plt
import pylab as py
import h5py
import sys
import itertools
import scipy
from scipy.interpolate import griddata
from mpl_toolkits.mplot3d import Axes3D

def simul_data(data,Rnge=600,mhigh_cut=False,mhigh=0):
    """
    takes in subhalo catalogs and returns subhalo masses, positions, halfmass and vmax radii
    inputs:
        data: halo catalog
        Rnge: size (in kpc/h) of the box/cube out to which we want to include subhalos
    outputs:
        subh_mass: subhalo masses
        subh_pos: subhalo positions
        rh : halfmass radii
        rvmax: radius at which v_max (max. circular velocity) is achieved
    """

    print "m_high cut: %s " % mhigh_cut
    masses = []
    positions1 = []
    rh = []
    rvmax = []
    
    for i in data:
    
        file = h5py.File(i,'r')
        h = file['Header'].attrs['HubbleParam']
    
        if len(file['Subhalo'].keys()) != 0:
            masses.append(file['Subhalo']['SubhaloMass'].value) #in 10^10 M_sun/h
            positions1.append(file['Subhalo']['SubhaloPos'].value) # in kpc/h, absolute box coordinates
            rh.append(file['Subhalo']['SubhaloHalfmassRad'].value) # in kpc/h
            rvmax.append(file['Subhalo']['SubhaloVmaxRad'].value) # in kpc/h
    
    masses = [i for j in masses for i in j]
    positions1 = [np.asarray(i)*h for j in positions1 for i in j]
    rh = [i*h for j in rh for i in j]
    rvmax = [i*h for j in rvmax for i in j]
    parent_mass = masses[0]
    parent_pos = positions1[0]
    parent_rvmax = rvmax[0]
    parent_rh = rh[0]
    positions = [i - parent_pos for i in positions1] #setting origin at halo center

    subh = zip(masses[1:],positions[1:],rh[1:],rvmax[1:])
    
    #keeping subhalos above mass resolution limit (below mhigh if mhigh_cut = True) and out to 300 kpc
    
    if mhigh_cut == True:

        subh_cut = [i for i in subh if 1.5e-4 < i[0] <= mhigh and -Rnge/2. < i[1][0] < Rnge/2. and -Rnge/2. < i[1][1] < Rnge/2. and -Rnge/2. < i[1][2] < Rnge/2.]
        mass,pos,rh,rvmax = zip(*subh_cut)

        return mass,pos,rh,rvmax

    else:

        subh_cut = [i for i in subh if 1.5e-4 < i[0] and -Rnge/2. < i[1][0] < Rnge/2. and -Rnge/2. < i[1][1] < Rnge/2. and -Rnge/2. < i[1][2] < Rnge/2.]
        mass,pos,rh,rvmax = zip(*subh_cut)

        return mass,pos,rh,rvmax

def rotation(nx,ny,nz,theta):
    """
    input:
        unit vector (nx,ny,nz)
        theta: rotation angle
    output:
        3x3 rotation matrix that rotates a 3d vector about a unit vector (nx,ny,nz) by an angle theta
    """
    R = [[np.cos(theta) + (nx**2)*(1-np.cos(theta)) , nx*ny*(1-np.cos(theta)) - nz*np.sin(theta) , nx*nz*(1-np.cos(theta)) + ny*np.sin(theta)], [nx*ny*(1-np.cos(theta)) + nz*np.sin(theta) , np.cos(theta) + (ny**2)*(1-np.cos(theta)) , ny*nz*(1-np.cos(theta)) - nx*np.sin(theta)], [nz*nx*(1-np.cos(theta)) - ny*np.sin(theta) , nz*ny*(1-np.cos(theta)) + nx*np.sin(theta) , np.cos(theta) + (nz**2)*(1-np.cos(theta))]]

    return R

def orig_projection(positions,masses,rvmax,rh,rnge=100,shift=0,num_proj=10):
    
    coords_orig = []
    coordsm_orig = []
    
    orig_proj = [[[i[0],i[1]],j,k,l,np.linalg.norm(i)] for i,j,k,l in zip(positions,masses,rvmax,rh) if -rnge/2.+shift < i[0] < rnge/2.+shift and -rnge/2.+shift < i[1] < rnge/2.+shift]
    coordsm_orig.append(orig_proj)
    
    return coordsm_orig

def projections(positions,masses,rvmax,rh,rnge=100,shift=0,num_proj=10):
    """
    inputs:
        positions: array of 3d positions
        masses: array of masses
        rnge: (2*radial distance) out to which we want to include subhalos
        shift: optional shift away from the host center; default is zero
        num_proj: (total number of 2d maps we want)/3 - the division by three is because for each 3d map we project in three different directions, namely xy,xz,yz
    outputs:
        coordsm: array of 2d positions and masses (len(coordsm)=3*num_proj)
        avg_num_subh: average number of subhalos within r < rnge/2 kpc/h after rotating and projecting
    """

    coordsm = []
    count = 0
    while count < num_proj:
        count += 1
        nnx = np.random.uniform(0,10)
        nny = np.random.uniform(0,10)
        nnz = np.random.uniform(0,10)
        theta = np.random.uniform(0,2*np.pi)

        nx = 1/np.sqrt(nnx**2 + nny**2 + nnz**2) * nnx
        ny = 1/np.sqrt(nnx**2 + nny**2 + nnz**2) * nny
        nz = 1/np.sqrt(nnx**2 + nny**2 + nnz**2) * nnz

        R = rotation(nx,ny,nz,theta)
        rot_pos = [np.dot(R,i) for i in positions]

        proj_xy2 = [[[i[0],i[1]],j,k,l,np.linalg.norm(i)] for i,j,k,l in zip(rot_pos,masses,rvmax,rh) if -rnge/2.+shift < i[0] < rnge/2.+shift and -rnge/2.+shift < i[1] < rnge/2.+shift]
        proj_xz2 = [[[i[0],i[2]],j,k,l,np.linalg.norm(i)] for i,j,k,l in zip(rot_pos,masses,rvmax,rh) if -rnge/2.+shift < i[0] < rnge/2.+shift and -rnge/2.+shift < i[2] < rnge/2.+shift]
        proj_yz2 = [[[i[1],i[2]],j,k,l,np.linalg.norm(i)] for i,j,k,l in zip(rot_pos,masses,rvmax,rh) if -rnge/2.+shift < i[1] < rnge/2.+shift and -rnge/2.+shift < i[2] < rnge/2.+shift]

        coordsm.append(proj_xy2)
        coordsm.append(proj_xz2)
        coordsm.append(proj_yz2)

        tot_num_subh = []
        for i in coordsm:
            tot_num_subh.append(len(i))
        avg_num_subh = np.mean(tot_num_subh)

    return coordsm,avg_num_subh

def twoD_nr(coords,pix_num=20,rnge=100,shift=0,show_nr=False):
    """
    takes in projected subhalo positions and returns the 2D n(r)
    inputs:
        coords: list of lists, where each list is an array of 2d subhalo positions
        pix_num: number of bins in the horizontal and vertical axes of the 2D power spectrum
        rnge: box size
        shift: offset from the halo center
        show_nr: whether you want to display it; default is False
    outputs:
        ind_corr: list of lists, where each list is a 2d n(r) map
        tot_corr: coadded 2d n(r) map (i.e. coadding maps in ind_corr)
        bin_size: pixel size
        np.mean(nbar): average nbar across all maps
    """
    bin_size = rnge/pix_num
    bin_avg = []
    ind_corr = []
    for i in coords:
        x,y = zip(*i)
        n,xedges,yedges = np.histogram2d(x,y,bins=pix_num)
        N = n.T
        Nbar = N.mean()
        bin_avg.append(Nbar)
        corr = (N - Nbar) / Nbar
        ind_corr.append(corr)

    nbar = Nbar/(bin_size**2)

    tot_corr = sum(ind_corr)/len(ind_corr)

    if show_nr == True:
        py.figure('(n - nbar)/nbar %s x %s' % (pix_num,pix_num))
        plt.imshow(tot_corr,extent=[-rnge/2+shift, rnge/2+shift, -rnge/2+shift, rnge/2+shift],interpolation='nearest')
        plt.colorbar()
        py.show()

    return ind_corr,tot_corr,np.mean(nbar)

def twoD_ps(data=None,pix_size=0,rnge=100,shift=0,show_ps=False):
    """
    takes in a 2D array and returns the 2D FFT:
    inputs:
        ind_coords: n 2d arrays, whose average = coadd_coords
        coadd_coords: a singe 2d array
        pix_size: pixel size
        rnge: box size
        shift: offset from the halo center
        show_ps: whether you want to display the 2d power spectrum
    outputs:
        ind_ps_x: list of lists, where each list is a 2d power spectrum
        tot_ps: total 2D power spectrum after coadding all PS in ind_ps_x
        ky,ky: fft frequencies
    """
    if data == None:
        raise RuntimeError('No data was given!')

    ind_ps = []
    for i in data:
        ft = np.fft.fft2(i)
        ps2D = np.abs(ft)**2
        ind_ps.append(ps2D)

    A_pix = pix_size**2
    A_box = rnge**2
    norm = A_pix**2/A_box

    ind_ps_x = [norm*np.fft.fftshift(i) for i in ind_ps]
    tot_ps = np.mean(ind_ps_x,axis=0)
    tot_ps2 = np.log10(tot_ps)

    kx = 2*np.pi*np.fft.fftfreq(tot_ps.shape[0],d=pix_size)
    kx = np.fft.fftshift(kx)
    ky = 2*np.pi*np.fft.fftfreq(tot_ps.shape[1],d=pix_size)
    ky = np.fft.fftshift(ky)

    if show_ps == True:
        fig,(ax1,ax2) = plt.subplots(2,sharey=True)
        ax1.imshow(tot_ps,extent=[min(kx),max(kx),min(ky),max(ky)],interpolation='nearest')
        ax2.imshow(tot_ps2,extent=[min(kx),max(kx),min(ky),max(ky)],interpolation='nearest')
        plt.show()

    return ind_ps_x,tot_ps,kx,ky

def multipoles(data,x,y,mask=None,pix_num=0,dr=1,ns=[]):
    """
        inputs:
        data: 2d map
        x,y: arrays that make up the map edges
        rnge: 2d map physical size
        dr: pixel size
	ns: a list of integers n where n represents the nth multipole (i.e. 0 = monopole, 1 = dipole, etc.)
    """
    
    data = np.asarray(data)
    shift = int(np.floor(pix_num/2))
    
    X,Y = np.meshgrid(x,y)
    r = np.sqrt(X**2+Y**2)

    if max(x) <= max(y):
        rmax = max(x)
    else:
        rmax = max(y)

    R = np.arange(rmax/dr)*dr

    power_spectra = {}

    for n in ns:
    	    
	power_spectra['%s' % n] = []
	
	if n == 0:

	    for i,j in zip(range(len(R)),mask):
        	ring = data*j
        	pk = ring[ring != 0]
        	dphi = 2*np.pi/len(pk)
		power_spectra['%s' % n].append((1/(2*np.pi))* np.sum(pk*dphi))
	
	if n != 0:    

            for i,j in zip(range(len(R)),mask):
                ring = data * j
        
                pk = ring[ring != 0]

                indices = np.asarray(np.nonzero(ring)) - shift
                dphi = 2 * np.pi / len(pk)

                phi = np.zeros(len(pk))
                count = 0
                for i,j in zip(indices[0],indices[1]):
                    phi[count] = np.arctan2(j,i)
                    count += 1
        
                integrand = pk * np.cos(n*phi)
	
		power_spectra['%s' % n].append((1/(2*np.pi)) * np.sum(dphi*integrand))

    return power_spectra,R

def variance(individual_ps,ps1d,N,kx,ky,mask=None,rnge=100,pix_num=21,pix_size=1,n=None):
    """
    takes in a list of lists where each nested list is a single 2d map and returns the variance of each map with respect to the average of all the maps
        individual_ps: list of lists where each nested list is a single 2d map
        ps1d: average 1D power spectrum
        kx,ky: fft frequencies
        rnge: spatial extent out to which we want to consider subhalos
        pix_num: number of pixels
        pix_size: pixel size
    """

    ns = [int(n)]

    var = []

    for i in individual_ps:

        power_spectra,K = multipoles(i,kx,ky,mask=mask,pix_num=pix_num,dr=pix_size,ns=ns)
        diff = [(1/N)*(j-k)**2 for j,k in zip(power_spectra[n],ps1d)]
	var.append(diff)
    
    var = np.sum(var,axis=0)
    return var

def poisson_realization(rnge=100,subh_num=1,num_proj=3000):
    """
    Creates 2d maps with a given number of randomly distributed subhalos
        rnge: box size
        subh_num: desired number of subhalos in the map
        num_proj: desired number of projections, default is 3000
    """
    coords = []
    count = 0
    while count < num_proj:
        count += 1
        rand = np.random.uniform(-rnge/2.,rnge/2.,(int(subh_num),2))
        coords.append(rand)
    return coords

def interpolation(data,x,y,num=100j,display=False):
    """
    Takes in discrete 2d array and returns an interpolated array
    """
    X, Y = np.meshgrid(x,y)
    l1 = [i for j in X for i in j]
    l2 = [i for j in Y for i in j]
    points = [list(i) for i in zip(l1,l2)]
    values = np.array([i for j in data for i in j])
    grid_x,grid_y = np.mgrid[x[0]:x[-1]:num, y[0]:y[-1]:num]
    grid = griddata(points,values,(grid_x,grid_y),method='cubic')

    if display == True:
        py.figure('Interpolated map')
        plt.imshow(grid.T)
        plt.colorbar()
        plt.show()

    return grid
