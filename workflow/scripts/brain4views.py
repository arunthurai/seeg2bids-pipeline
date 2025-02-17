import numpy as np
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize, to_rgba_array
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.collections import PolyCollection
from nilearn import surface

EPSILON = 1e-12  # small value to add to avoid division with zero


def normalize_v3(arr):
	"""Normalize a numpy array of 3 component vectors shape=(n,3)"""
	lens = np.sqrt(arr[:, 0] ** 2 + arr[:, 1] ** 2 + arr[:, 2] ** 2)
	arr[:, 0] /= lens + EPSILON
	arr[:, 1] /= lens + EPSILON
	arr[:, 2] /= lens + EPSILON
	return arr


def normal_vectors(vertices, faces):
	tris = vertices[faces]
	n = np.cross(tris[::, 1] - tris[::, 0], tris[::, 2] - tris[::, 0])
	n = normalize_v3(n)
	return n


def frustum(left, right, bottom, top, znear, zfar):
	M = np.zeros((4, 4), dtype=np.float32)
	M[0, 0] = +2.0 * znear / (right - left)
	M[1, 1] = +2.0 * znear / (top - bottom)
	M[2, 2] = -(zfar + znear) / (zfar - znear)
	M[0, 2] = (right + left) / (right - left)
	M[2, 1] = (top + bottom) / (top - bottom)
	M[2, 3] = -2.0 * znear * zfar / (zfar - znear)
	M[3, 2] = -1.0
	return M


def perspective(fovy, aspect, znear, zfar):
	h = np.tan(0.5 * np.radians(fovy)) * znear
	w = h * aspect
	return frustum(-w, w, -h, h, znear, zfar)


def translate(x, y, z):
	return np.array(
		[[1, 0, 0, x], [0, 1, 0, y], [0, 0, 1, z], [0, 0, 0, 1]], dtype=float
	)


def xrotate(theta):
	t = np.pi * theta / 180
	c, s = np.cos(t), np.sin(t)
	return np.array(
		[[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]], dtype=float
	)


def yrotate(theta):
	t = np.pi * theta / 180
	c, s = np.cos(t), np.sin(t)
	return np.array(
		[[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]], dtype=float
	)


def plot_surf4(
	meshes,
	overlays=None,
	sulc_maps=None,
	ctx_masks=None,
	labels=None,
	label_colors=None,
	label_alpha=0.5,
	cmap=None,
	shuffle_cmap=False,
	threshold=None,
	vmin=None,
	vmax=None,
	avg_method="mean",
	colorbar=False,
	output_file="plot.png",
	dpi=128,
	title="",
):
	"""Plottig of surface mesh with optional overlay data
	and sulcal maps.

	Parameters
	----------
	meshes: list of two files [left hemi (lh), right hemi (rh)]
		Surface mesh geometry, Valid file formats are
		.gii or Freesurfer specific files such as .orig, .pial,
		.sphere, .white, .inflated
	overlays: optional, list of two files [lh, rh]
		Data to be displayed on the surface mesh. Valid formats
		are .gii, or Freesurfer specific files such as
		.thickness, .curv, .sulc, .annot, .label
	sulc_maps: optional, list of two files [lh, rh]
		Sulcal depth (or curvature) map to be plotted on the mesh
		in greyscale, underneath the overlay. Valid formats
		are .gii, or Freesurfer specific files .sulc and .curv
	ctx_masks: optional, list of two files [lh, rh]
		Cortical labels (masks) to restrict overlay data.
		Valid formats are Freesurfer specific file .label,
		or .gii
	labels: list of lists of the form
		[ [lh_label1, rh_label1], [lh_label2, rh_label2], ... ]
		Labels to be displayed on the surface mesh. Valid formats
		Freesurfer specific files (.label) or equivalent files
		in .gii format
	label_colors: list of matplotlib colors to be assigned to labels,
		of the form [ color_label1, color_label2, ... ]
		Must have the same langth as the list of labels.
	label_alpha: float, transparency level for label colors
		fro 0 (translucent) to 1 (fully opaque)
	cmap: matplotlib colormap, str or colormap object, default is None
		To use for plotting of the overlay. Either a string
		which is a name of a matplotlib colormap, or a matplotlib
		colormap object. If None, matplotlib default will be chosen.
	shuffle_cmap: boolean
		If True, randomly shuffle the cmap (useful for parcellations)
	avg_method: {'mean', 'median'}, default is 'mean'
		How to average vertex values to derive the face value, mean results
		in smooth, median in sharp boundaries (e.g. for parcellations).
	colorbar : bool, optional, default is False
		If True, a colorbar of surf_map is displayed.
	threshold : a number or None, default is None.
		If None is given, the image is not thresholded.
		If a number is given, it is used to threshold the image, values
		below the threshold (in absolute value) are plotted as transparent.
	vmin, vmax: lower / upper bound to plot surf_data values
		If None , the values will be set to min/max of the data
	title : str, optional
		Figure title.
	output_file: str, or None, optional
		The name of an image file to export plot to. Valid extensions
		are .png, .pdf, .svg. If output_file is not None, the plot
		is saved to a file, and the display is closed.
	"""

	print("plotting...")

	# if no cmap is given, set to matplotlib default
	if cmap is None:
		cmap = plt.cm.get_cmap(plt.rcParamsDefault["image.cmap"])
	else:
		# if cmap is given as string, translate to matplotlib cmap
		if isinstance(cmap, str):
			cmap = plt.cm.get_cmap(cmap)

	# randomly shuffle colormap if prompted
	if shuffle_cmap:
		vals = np.linspace(0, 1, 256)
		np.random.shuffle(vals)
		cmap = ListedColormap(plt.cm.get_cmap(cmap)(vals))

	# initiate figure
	fig = plt.figure(figsize=(8, 6))

	# select which views to show
	# [lh_lateral, lh medial], [rh_lateral, rh_medial]
	rotations_both = [[90, 270], [270, 90]]

	for m, mesh in enumerate(meshes):
		# load mesh
		vertices, faces = surface.load_surf_mesh(mesh)
		vertices = vertices.astype(np.float)
		faces = faces.astype(int)

		# Set up lighting, intensity and shading
		rotations = rotations_both[m]
		vert_range = max(vertices.max(0) - vertices.min(0))
		vertices = (vertices - (vertices.max(0) + vertices.min(0)) / 2) / vert_range
		face_normals = normal_vectors(vertices, faces)
		light = np.array([0, 0, 1])
		intensity = np.dot(face_normals, light)
		shading = 0.7  # shading 0-1. 0=none. 1=full
		# top 20% all become fully colored
		denom = np.percentile(intensity, 80) - np.min(intensity)
		intensity = (1 - shading) + shading * (intensity - np.min(intensity)) / denom
		intensity[intensity > 1] = 1

		# initiate array for face colors
		face_colors = np.ones((faces.shape[0], 4))

		##################################
		# read cortex label if provided
		if ctx_masks is None:
			mask = np.zeros(vertices.shape[0]).astype(bool)
		else:
			mask = np.zeros(vertices.shape[0]).astype(bool)
			cortex = surface.load_surf_data(ctx_masks[m])
			mask[cortex] = 1  # cortical vertices = 1

		##################################
		# read sulcal map if provided
		if sulc_maps is None:
			sulc = np.ones(vertices.shape[0]) * 0.5
		else:
			sulc = surface.load_surf_data(sulc_maps[m])
			if sulc.shape[0] != vertices.shape[0]:
				raise ValueError(
					"The sulcal map does not have the same "
					"number of vertices as the mesh."
				)

		sulc_faces = np.mean(sulc[faces], axis=1)
		# binarize sulcal map
		if sulc_faces.min() != sulc_faces.max():
			neg_sulc = np.where(sulc_faces <= 0)
			pos_sulc = np.where(sulc_faces > 0)
			sulc_faces[neg_sulc] = 0
			sulc_faces[pos_sulc] = 1

		##################################
		# read labels if provided
		label_masks = []
		if labels is not None:
			if len(label_colors) != len(labels):
				raise ValueError(
					"labels and label_colors must be" " lists of the same length."
				)
			label_colors = [to_rgba_array(c) for c in label_colors]
			for c in label_colors:
				c[0, 3] = label_alpha
			for label in labels:
				L_mask = np.zeros(vertices.shape[0]).astype(bool)
				L_indices = surface.load_surf_data(label[m])
				L_mask[L_indices] = 1  # label vertices = 1
				label_masks.append(L_mask)

		label_mask_faces = [np.median(L[faces], axis=1) for L in label_masks]

		##################################
		# read overlay map if provided
		if overlays is not None:
			overlay = surface.load_surf_data(overlays[m])
			if len(overlay.shape) != 1:
				raise ValueError(
					"overlay can only have one dimension"
					" but has %i dimensions" % len(overlay.shape)
				)
			if overlay.shape[0] != vertices.shape[0]:
				raise ValueError(
					"The overlay does not have the same number"
					" of vertices as the mesh."
				)

		##################################
		# assign greyscale colormap to sulcal map faces
		greys = plt.get_cmap("Greys", 512)
		greys_narrow = ListedColormap(greys(np.linspace(0.42, 0.58, 256)))
		face_colors = greys_narrow(sulc_faces)

		# Get indices of faces within the cortex
		if ctx_masks is None:
			kept_indices = np.arange(sulc_faces.shape[0])
		else:
			mask_faces = np.median(mask[faces], axis=1)
			kept_indices = np.where(mask_faces >= 0.5)[0]
			masked_indices = np.where(mask_faces < 0.5)[0]

		if overlays is not None:
			# create face values from vertex values by selected avg methods
			if avg_method == "mean":
				overlay_faces = np.mean(overlay[faces], axis=1)
			elif avg_method == "median":
				overlay_faces = np.median(overlay[faces], axis=1)

			# if no vmin/vmax are passed figure them out from the data
			if vmin is None:
				vmin = np.nanmin(overlay_faces)
			if vmax is None:
				vmax = np.nanmax(overlay_faces)

			# threshold if indicated
			if threshold is not None:
				valid_indices = np.where(np.abs(overlay_faces) >= threshold)[0]
				kept_indices = [i for i in kept_indices if i in valid_indices]

			# assign colormap to overlay
			overlay_faces = overlay_faces - vmin
			overlay_faces = overlay_faces / (vmax - vmin)
			face_colors[kept_indices] = cmap(overlay_faces[kept_indices])

		# make non-cortical faces light grey
		if ctx_masks is not None:
			face_colors[masked_indices] = [0.85, 0.85, 0.85, 1]

		# assign label faces to appropriate color
		for i, L in enumerate(label_mask_faces):
			L_idx = np.where(L >= 0.5)
			# blend (multiply) label color with underlying color
			face_colors[L_idx] = face_colors[L_idx] * label_colors[i]

		face_colors[:, 0] *= intensity
		face_colors[:, 1] *= intensity
		face_colors[:, 2] *= intensity

		##################################
		# Draw the plot
		for i, view in enumerate(rotations):
			MVP = (
				perspective(25, 1, 1, 100)
				@ translate(0, 0, -3)
				@ yrotate(view)
				@ xrotate(270)
			)
			# translate coordinates based on viewing position
			V = np.c_[vertices, np.ones(len(vertices))] @ MVP.T
			V /= V[:, 3].reshape(-1, 1)
			V = V[faces]
			# triangle coordinates
			T = V[:, :, :2]
			# get Z values for ordering triangle plotting
			Z = -V[:, :, 2].mean(axis=1)
			# sort the triangles based on their z coordinate
			Zorder = np.argsort(Z)
			T, C = T[Zorder, :], face_colors[Zorder, :]
			# add subplot and plot PolyCollection
			ax = fig.add_subplot(
				2,
				2,
				m + 2 * i + 1,
				xlim=[-1, +1],
				ylim=[-0.6, +0.6],
				frameon=False,
				aspect=1,
				xticks=[],
				yticks=[],
			)
			collection = PolyCollection(
				T, closed=True, antialiased=False, facecolor=C, edgecolor=C, linewidth=0
			)
			collection.set_alpha(1)
			ax.add_collection(collection)

	##################################
	# Draw colorbar if prompted
	if colorbar:
		our_cmap = plt.get_cmap(cmap)
		norm = Normalize(vmin=vmin, vmax=vmax)
		bounds = np.linspace(vmin, vmax, our_cmap.N)

		if threshold is None:
			ticks = [vmin, vmax]
		elif threshold == vmin:
			ticks = [vmin, vmax]
		else:
			if vmin >= 0:
				ticks = [vmin, threshold, vmax]
			else:
				ticks = [vmin, -threshold, threshold, vmax]

			cmaplist = [our_cmap(i) for i in range(our_cmap.N)]
			# set colors to grey for absolute values < threshold
			istart = int(norm(-threshold, clip=True) * (our_cmap.N - 1))
			istop = int(norm(threshold, clip=True) * (our_cmap.N - 1))
			for i in range(istart, istop):
				cmaplist[i] = (0.5, 0.5, 0.5, 1.0)
			our_cmap = LinearSegmentedColormap.from_list(
				"Custom cmap", cmaplist, our_cmap.N
			)

		# we need to create a proxy mappable
		proxy_mappable = ScalarMappable(cmap=our_cmap, norm=norm)
		proxy_mappable.set_array(overlay_faces)
		cax = plt.axes([0.38, 0.466, 0.24, 0.024])
		plt.colorbar(
			proxy_mappable,
			cax=cax,
			boundaries=bounds,
			ticks=ticks,
			orientation="horizontal",
		)

	# add annotations
	if title is not None:
		fig.text(0.5, 0.51, title, ha="center", va="bottom", fontsize="large")
	fig.text(0.25, 0.975, "Left", ha="center", va="top")
	fig.text(0.75, 0.975, "Right", ha="center", va="top")
	fig.text(0.025, 0.75, "Lateral", ha="left", va="center", rotation=90)
	fig.text(0.025, 0.25, "Medial", ha="left", va="center", rotation=90)
	fig.subplots_adjust(left=0, right=1, top=1, bottom=0, wspace=0, hspace=0)

	# save file
	fig.savefig(output_file, dpi=dpi)
