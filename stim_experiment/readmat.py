

import os
import collections
import json

import scipy as sy
import h5py
import scipy.io

import numpy as np

import statsmodels as sm

import pandas as pd

import series_utils as su

from time import time

#
#	NOTE: Waveforms currently not recorded.
#
#
#
#

# def times_corr(times1, times2, max_diff=30000):
# 	corr_off = np.empty([max_diff+1])
# 	print(times2)
# 	t2set = sets.Set(times2)
# 	for offset in xrange(0,max_diff):
# 		offtimes = times1 + offset
# 		corr_off[offset] = len(t2set.intersection(sets.Set(offtimes)))
# 	return corr_off

def parse_nev_mat(f):
    """Parses a .mat version of an NEV file and returns a time-series
    of spike, where the indices are times (in units since start of rec)
    and the data are (electrode,unit) tuples.

    Note that we will likely need to return the sampling frequency.
    Currently I assume 30kHz."""

    (root, ext) = os.path.splitext(f)
    if ext == '.mat':
        mat_spikes = h5py.File(f, 'r')['NEV']
        time_res = mat_spikes['MetaTags']['TimeRes'][0][0]
        mat_spikes = mat_spikes['Data']['Spikes']

        unwrap = lambda x: np.array([y for z in x for y in z])

        # eu stands for 'Electrode/Unit'
        eu_mat = map(unwrap, [mat_spikes['Electrode'][:],
            mat_spikes['Unit'][:]])
        duped_eu_tuples = zip(*eu_mat)

        time_indexed = pd.Series(duped_eu_tuples,
                index=mat_spikes['TimeStamp'][:])

        return time_indexed
    return pd.Series() # Gets hissy if you return None

def nevdir_to_xcorrs(matdir):
    """Assumes all .mat files in the provided directory are parsed NEV files.
    Ignores non-.mat files."""
    # Experiment with one file
    retdct = {}
    for root, dirs, files in os.walk(matdir):
        for f in files:
            (bname, ext) = os.path.splitext(f)
            if ext == '.mat':
                fullpath = os.path.join(root,f)
                parsedmat = parse_nev_mat(fullpath)
                retdct[fullpath] = parsedmat
    return retdct

def corr_memview_to_list(memview):
    maplambda = lambda x: map(lambda y: np.asarray(y).tolist(), x) # assumes [] not None
    return map(maplambda, memview)

def get_correlated_eus(arr, eus):
    ret_list = []
    left_max = len(arr)
    right_max = len(arr[0])
    for ii in range(left_max):
        for jj in range(right_max):
            if len(arr[ii][jj]) > 0:
                ret_list.append([eus[ii], eus[jj]])
    return ret_list

def _times_xcorr(time1, time2, max_diff=3000):
    xcorr = np.zeros([max_diff+1])
    for ii in range(len(time1)):
        for jj in range(len(time2)):
            diff = time1[ii] - time2[jj]
            if diff >= 0 and diff <= max_diff:
                xcorr[diff] += 1
    return xcorr


def xcorr_from_times(times):
    xcorr_mat = [[_times_xcorr(time1, time2) for time2 in times] 
            for time1 in times]
    return xcorr_memview_to_list(xcorr_mat)

def write_corrs_to_json(nevdir):
    parsed_dct = nevdir_to_xcorrs(nevdir)
    written_jsons = []

    for key,value in parsed_dct.iteritems():
        unique_eu_tuples = list(set(value))
        eu_indexed_dict = {k: [] for k in unique_eu_tuples}
        for n,v in value.iteritems():
            eu_indexed_dict[v].append(*n)

        ordered_eu_indexed_dict = collections.OrderedDict(sorted(eu_indexed_dict.items(), 
            key=lambda t: t[0]))

        times = map(lambda x: np.array(x, np.int64), ordered_eu_indexed_dict.values())

        corr_memview = su.corr_mat_from_times(times)
        corr_mat = corr_memview_to_list(corr_memview)

        (noext, ext) = os.path.splitext(key)
        newpath = noext + '_xcorr.json'
        with open(newpath, 'w') as jsonfile:
            json.dump(corr_mat, jsonfile)
        written_jsons.append(newpath)

    return written_jsons

def stupid_times(nevdir):
    # nevdir_to_xcorrs is 60% of function time
    parsed_dct = nevdir_to_xcorrs(os.path.join(nevdir, "A"))

    times_list = []

    # this loop is 40% of function time
    for key,value in parsed_dct.iteritems():
        print value
        print key
        unique_eu_tuples = list(set(value))
        eu_indexed_dict = {k: [] for k in unique_eu_tuples}

        # This loop is ~80% of loop time, or 35% of function time
        for n,v in value.iteritems():
            eu_indexed_dict[v].append(*n)

        ordered_eu_indexed_dict = collections.OrderedDict(sorted(eu_indexed_dict.items(), 
            key=lambda t: t[0]))

        times_list.append(map(lambda x: np.array(x, np.int64), ordered_eu_indexed_dict.values()))
    return times_list


if __name__ == "__main__":

    rootdir = '/home/grahams/Dropbox/Hatsopoulos/stim_experiment'
    nevdir = os.path.join(rootdir, 'nev_sorted')

    written = write_corrs_to_json(nevdir)


# with open('xcorr_m5th25.json','w') as jsonfile:
# 	json.dump(xcorr_memview_to_list(xcorr_mat), jsonfile)

