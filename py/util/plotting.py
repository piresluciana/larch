
from io import BytesIO
from ..util.xhtml import XHTML, XML_Builder
import os

import matplotlib.pyplot as plt
import numpy

def plot_as_svg_xhtml(pyplot, classname='figure', headerlevel=2, header=None, anchor=1, **format):
	existing_format_keys = list(format.keys())
	for key in existing_format_keys:
		if key.upper()!=key: format[key.upper()] = format[key]
	if 'GRAPHWIDTH' not in format and 'GRAPHHEIGHT' in format: format['GRAPHWIDTH'] = format['GRAPHHEIGHT']
	if 'GRAPHWIDTH' in format and 'GRAPHHEIGHT' not in format: format['GRAPHHEIGHT'] = format['GRAPHWIDTH']*.67
	import xml.etree.ElementTree as ET
	ET.register_namespace("","http://www.w3.org/2000/svg")
	ET.register_namespace("xlink","http://www.w3.org/1999/xlink")
	imgbuffer = BytesIO()
#	if 'GRAPHWIDTH' in format and 'GRAPHHEIGHT' in format:
#		pyplot.figure(figsize=(format['GRAPHWIDTH'],format['GRAPHHEIGHT']))
	pyplot.savefig(imgbuffer, dpi=None, facecolor='w', edgecolor='w',
        orientation='portrait', papertype=None, format='svg',
        transparent=False, bbox_inches=None, pad_inches=0.1,
        frameon=None)
	x = XML_Builder("div", {'class':classname})
	if header:
		x.hn(headerlevel, header, anchor=anchor)
	xx = x.close()
	xx << ET.fromstring(imgbuffer.getvalue().decode())
	return xx



class default_mplstyle():

	def __enter__(self):
		from matplotlib import pyplot
		sty = os.path.join( os.path.dirname(__file__), 'larch.mplstyle' )
		self._contxt = pyplot.style.context((sty))
		self._contxt.__enter__()

	def __exit__(self, exc_type, exc_value, traceback):
		self._contxt.__exit__(exc_type, exc_value, traceback)


_color_rgb256 = {}
_color_rgb256['sky'] = (35,192,241)
_color_rgb256['ocean'] = (29,139,204)
_color_rgb256['night'] = (100,120,186)
_color_rgb256['forest'] = (39,182,123)
_color_rgb256['lime'] = (128,189,1)

def hexcolor(color):
	c = _color_rgb256[color.casefold()]
	return "#{}{}{}".format(*(hex(c[i])[-2:] for i in range(3)))



def spark_histogram_maker(data, bins=20, title=None, xlabel=None, ylabel=None, xticks=False, yticks=False, frame=False):

	if isinstance(bins, str):
		data = numpy.asarray(data)
		if data.size == 0:
			# handle empty arrays. Can't determine range, so use 0-1.
			mn, mx = 0.0, 1.0
		else:
			mn, mx = data.min() + 0.0, data.max() + 0.0
		width = numpy.lib.function_base._hist_bin_selectors[bins](data)
		if width:
			bins = int(numpy.ceil((mx - mn) / width))
		else:
			bins = 1
		# The spark graphs get hard to read if the bin slices are too thin, so we will max out at 50 bins
		if bins > 50:
			bins = 50
	try:
		n, bins, patches = plt.hist(data, bins, normed=1, facecolor=hexcolor('ocean'), linewidth=0, alpha=1.0)
	except:
		print("<data>\n",data,"</data>")
		print("<bins>\n",bins,"</bins>")
		raise
	fig = plt.gcf()
	fig.set_figheight(0.2)
	fig.set_figwidth(0.75)
	fig.set_dpi(300)
	if xlabel: plt.xlabel(xlabel)
	if ylabel: plt.ylabel(ylabel)
	if title: plt.title(title)
	if not xticks: fig.axes[0].get_xaxis().set_ticks([])
	if not yticks: fig.axes[0].get_yaxis().set_ticks([])
	if not frame: fig.axes[0].axis('off')
	plt.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
	ret = plot_as_svg_xhtml(fig)
	plt.clf()
	return ret





def spark_pie_maker(data):
	fig = plt.gcf()
	fig.set_figheight(0.2)
	fig.set_figwidth(0.75)
	fig.set_dpi(300)
	C_sky = (35,192,241)
	C_night = (100,120,186)
	C_forest = (39,182,123)
	C_ocean = (29,139,204)
	C_lime = (128,189,1)
	# The slices will be ordered and plotted counter-clockwise.
	plt.pie(data, explode=None, labels=None, colors=[hexcolor('sky'),hexcolor('night'),hexcolor('forest'),hexcolor('ocean')],
			#autopct='%1.1f%%',
			shadow=False, startangle=90,
			wedgeprops={'linewidth':0, 'clip_on':False},
			frame=False)
	plt.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
	# Set aspect ratio to be equal so that pie is drawn as a circle.
	plt.axis('equal')
	ret = plot_as_svg_xhtml(fig)
	plt.clf()
	return ret



def spark_histogram(data, *arg, **kwarg):
	try:
		flat_data = data.flatten()
	except:
		flat_data = data
	uniq = numpy.unique(flat_data[:100])
	uniq_counts = None
	if len(uniq)<=5:
		uniq, uniq_counts = numpy.unique(flat_data, return_counts=True)
	if uniq_counts is not None and len(uniq_counts)<=5:
		return spark_pie_maker(uniq_counts)
	return spark_histogram_maker(data, *arg, **kwarg)




