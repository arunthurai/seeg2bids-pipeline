#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import nibabel as nb
import numpy as np
import pandas as pd
import nrrd
import os


def bounding_box(seg):
	x = np.any(np.any(seg, axis=0), axis=1)
	y = np.any(np.any(seg, axis=1), axis=1)
	z = np.any(np.any(seg, axis=1), axis=0)
	ymin, ymax = np.where(y)[0][[0, -1]]
	xmin, xmax = np.where(x)[0][[0, -1]]
	zmin, zmax = np.where(z)[0][[0, -1]]
	bbox = np.array([ymin,ymax,xmin,xmax,zmin,zmax])
	return bbox

def get_shape_origin(img_data):
	bbox = bounding_box(img_data)
	ymin, ymax, xmin, xmax, zmin, zmax = bbox
	shape = list(np.array([ymax-ymin, xmax-xmin, zmax-zmin]) + 1)
	origin = [ymin, xmin, zmin]
	return shape, origin

def write_nrrd(data_obj, out_file,atlas_labels):
	
	data=data_obj.get_fdata()
	
	keyvaluepairs = {}
	keyvaluepairs['dimension'] = 3
	keyvaluepairs['encoding'] = 'gzip'
	keyvaluepairs['kinds'] = ['domain', 'domain', 'domain']
	keyvaluepairs['space'] = 'right-anterior-superior'
	keyvaluepairs['space directions'] = data_obj.affine[:3,:3].T
	keyvaluepairs['type'] = 'double'
	
	box = bounding_box(data)
	seg_cut = data[box[0]:box[1]+1,box[2]:box[3]+1,box[4]:box[5]+1]
	shape, origin = get_shape_origin(data)
	origin = nb.affines.apply_affine(data_obj.affine, np.array([origin]))

	keyvaluepairs['sizes'] = np.array([*shape])
	keyvaluepairs['space origin'] = origin[0]
	
	for i in range(int(np.max(data))):
		col_lut=np.array(atlas_labels[atlas_labels['index']==i+1]['lut'].values[0]+[255])/255
		name = 'Segment{}'.format(i)
		keyvaluepairs[name + '_Color'] = ' '.join([f"{a:10.3f}" for a in col_lut])
		keyvaluepairs[name + '_ColorAutoGenerated'] = '1'
		keyvaluepairs[name + '_Extent'] = f'0 {shape[0]-1} 0 {shape[1]-1} 0 {shape[2]-1}'
		keyvaluepairs[name + '_ID'] = 'Segment_{}'.format(i+1)
		keyvaluepairs[name + '_LabelValue'] = '{}'.format(i+1)
		keyvaluepairs[name + '_Layer'] = '0'
		keyvaluepairs[name + '_Name'] = '_'.join([atlas_labels[atlas_labels['index']==i+1]['hemi'].values[0], atlas_labels[atlas_labels['index']==i+1]['abbreviation'].values[0]])
		keyvaluepairs[name + '_NameAutoGenerated'] = 1
		keyvaluepairs[name + '_Tags'] = 'TerminologyEntry:Segmentation category' +\
			' and type - 3D Slicer General Anatomy list~SRT^T-D0050^Tissue~SRT^' +\
			'T-D0050^Tissue~^^~Anatomic codes - DICOM master list~^^~^^|'

	keyvaluepairs['Segmentation_ContainedRepresentationNames'] = 'Binary labelmap|'
	keyvaluepairs['Segmentation_ConversionParameters'] = 'placeholder'
	keyvaluepairs['Segmentation_MasterRepresentation'] = 'Binary labelmap'
	
	nrrd.write(out_file, seg_cut, keyvaluepairs)

def write_ply(filename, vertices, faces, comment=None):
	import pandas as pd
	# infer number of vertices and faces
	number_vertices = vertices.shape[0]
	number_faces = faces.shape[0]
	# make header dataframe
	header = ['ply',
			'format ascii 1.0',
			'comment %s' % comment,
			'element vertex %i' % number_vertices,
			'property float x',
			'property float y',
			'property float z',
			'element face %i' % number_faces,
			'property list uchar int vertex_indices',
			'end_header'
			 ]
	header_df = pd.DataFrame(header)
	# make dataframe from vertices
	vertex_df = pd.DataFrame(vertices)
	# make dataframe from faces, adding first row of 3s (indicating triangles)
	triangles = np.reshape(3 * (np.ones(number_faces)), (number_faces, 1))
	triangles = triangles.astype(int)
	faces = faces.astype(int)
	faces_df = pd.DataFrame(np.concatenate((triangles, faces), axis=1))
	# write dfs to csv
	header_df.to_csv(filename, header=None, index=False)
	with open(filename, 'a') as f:
		vertex_df.to_csv(f, header=False, index=False,
						 float_format='%.3f', sep=' ')
	with open(filename, 'a') as f:
		faces_df.to_csv(f, header=False, index=False,
						float_format='%.0f', sep=' ')


#%%

debug = False

if debug:
	class dotdict(dict):
		"""dot.notation access to dictionary attributes"""
		__getattr__ = dict.get
		__setattr__ = dict.__setitem__
		__delattr__ = dict.__delitem__
	
	class Namespace:
		def __init__(self, **kwargs):
			self.__dict__.update(kwargs)
	
	subject_id="sub-P111"
	deriv_dir='/home/arun/Documents/data/seeg/derivatives'
	
	input=dotdict({
				't1_fname':'{deriv_dir}/hippunfold/hippunfold/{subject_id}/anat/{subject_id}_desc-preproc_T1w.nii.gz',
				})
	params=dotdict({
				'deriv_dir':deriv_dir,
				'subject_id':subject_id,
				'dseg_labels_file':'/home/arun/Documents/GitHub/ieegProc/resources/desc-subfields_atlas-bigbrain_dseg.tsv'
				})
	
	snakemake = Namespace(input=input,params=params)


# atlas_labels = pd.read_table(snakemake.params.dseg_labels_file)
# atlas_labels['lut']=atlas_labels[['r','g','b']].to_numpy().tolist()
# data_dir = snakemake.params.deriv_dir


atlas_labels = pd.read_table('/home/arun/Documents/ieegProc/resources/desc-subfields_atlas-bigbrain_dseg.tsv')
atlas_labels['lut']=atlas_labels[['r','g','b']].to_numpy().tolist()
data_dir = '/home/arun/Documents/data/seeg/derivatives'


for isub in os.listdir(os.path.join(data_dir,'hippunfold','hippunfold')):
	
	for isurf in ('inner','midthickness','outer'):
		for ihemi in ('L','R'):
			base_filename=f'{isub}_hemi-{ihemi}_space-T1w_den-0p5mm_label-hipp_{isurf}'
			gii_file_fname = f'{data_dir}/hippunfold/hippunfold/{isub}/surf/{base_filename}.surf.gii'
			gii_out_fname = f'{data_dir}/hippunfold/hippunfold/{isub}/surf/{base_filename}.ply'
			if not os.path.exists(gii_out_fname):
				gii_data = nb.load(gii_file_fname)
				vertices = gii_data.get_arrays_from_intent('NIFTI_INTENT_POINTSET')[0].data
				faces = gii_data.get_arrays_from_intent('NIFTI_INTENT_TRIANGLE')[0].data
				write_ply(gii_out_fname,vertices,faces,'SPACE=RAS')
	
	
	for ihemi in ('L','R'):
		base_filename=f'{isub}_hemi-{ihemi}_space-cropT1w_desc-subfields_atlas-multihist7_dseg'
		seg_file_fname = f'{data_dir}/hippunfold/hippunfold/{isub}/anat/{base_filename}.nii.gz'
		seg_out_fname = f'{data_dir}/hippunfold/hippunfold/{isub}/anat/{base_filename}.seg.nrrd'
		if not os.path.exists(seg_out_fname):
			data_obj=nb.load(seg_file_fname)
			
			atlas_labels['hemi']=np.repeat(ihemi, atlas_labels.shape[0])
			
			write_nrrd(data_obj, seg_out_fname, atlas_labels)



