#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 24 16:02:30 2021

@author: greydon
"""

import nrrd
import re
import pandas as pd
import nibabel as nb
import numpy as np
import matplotlib.pyplot as plt
import itertools


def bbox2(img):
	rows = np.any(img, axis=(1, 2))
	cols = np.any(img, axis=(0, 2))
	z = np.any(img, axis=(0, 1))
	
	ymin, ymax = np.where(rows)[0][[0, -1]]
	xmin, xmax = np.where(cols)[0][[0, -1]]
	zmin, zmax = np.where(z)[0][[0, -1]]
	return img[ymin:ymax+1, xmin:xmax+1, zmin:zmax+1]

def sorted_nicely(data, reverse = False):
	convert = lambda text: int(text) if text.isdigit() else text
	alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
	
	return sorted(data, key = alphanum_key, reverse=reverse)



#%%


isub="P066"
scene_path="seega_scenes"

repo_path = r'/home/greydon/Documents/GitHub'
#repo_path = r'/home/stereotaxy/Documents/GitHub'

data_path = r'/home/greydon/Documents/data/SEEG'
#data_path = r'/media/stereotaxy/3E7CE0407CDFF11F/data/SEEG/imaging/clinical'
#data_path = r'/media/veracrypt6/projects/iEEG/imaging/clinical'


atlas_labels = pd.read_table(repo_path + r'/seeg2bids-pipeline/resources/tpl-MNI152NLin2009cSym/tpl-MNI152NLin2009cSym_atlas-CerebrA_dseg.tsv')
nrrd.reader.ALLOW_DUPLICATE_FIELD = False
filedata, fileheader = nrrd.read(data_path + f'/derivatives/{scene_path}/' + f"sub-{isub}/sub-{isub}_desc-segmentations.seg.nrrd")


for iseg in sorted_nicely(list(fileheader)):
	if iseg.startswith('Segment') and iseg.endswith('Name'):
		new_label = atlas_labels.loc[atlas_labels['label']==int(''.join([x for x in (fileheader[iseg.replace("Name","ID")]) if x.isdigit()])), 'hemi'].to_list()[0]
		new_label = ' '.join([new_label, atlas_labels.loc[atlas_labels['label']==int(''.join([x for x in (fileheader[iseg.replace("Name","ID")]) if x.isdigit()])), 'name'].to_list()[0]])
		fileheader[iseg] = new_label.replace(" ","_")
		fileheader[iseg.replace("Name","NameAutoGenerated")] = '0'


data_obj=nb.load(data_path + f'/derivatives/{scene_path}/' + f'sub-{isub}/sub-{isub}_desc-segmentations.nii.gz')
data = bbox2(data_obj.get_fdata())
nrrd.write(data_path + f'/derivatives/{scene_path}/' + f'sub-{isub}/sub-{isub}_desc-segmentations.seg.nrrd', data, fileheader)



#%%




filedata, fileheader = nrrd.read('/media/veracrypt6/projects/iEEG/imaging/clinical/deriv/seega_scenes/sub-P067/sub-P067_desc-segmentations_3.seg.nrrd')

a = np.where(data != 0)
bbox = np.min(a[0]), np.max(a[0]), np.min(a[1]), np.max(a[1])
nrrd.write('/media/veracrypt6/projects/iEEG/imaging/clinical/deriv/seega_scenes/sub-P067/sub-P067_desc-segmentations_2.seg.nrrd', filedata, fileheader)


fig, ax = plt.subplots(1, 1)
tracker2 = IndexTracker(ax, data1, points=None,rotate_img=False, rotate_points=False)
fig.canvas.mpl_connect('scroll_event', tracker2.on_scroll)
plt.show()

nrrd.write('/media/veracrypt6/projects/iEEG/imaging/clinical/deriv/seega_scenes/sub-P067/sub-P067_desc-segmentations_3.seg.nrrd', data, fileheader)


