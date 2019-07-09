

from matplotlib import pyplot as plt
import pandas, numpy
from .plotting import plot_as_svg_xhtml

def distribution_on_continuous_idca_variable(
		model,
		continuous_variable,
		continuous_variable_label=None,
		bins=25,
		range=None,
		prob_label="Modeled",
		obs_label="Observed",
		header=None,
		subselector=None,
		probability=None,
		style='line',
		bw_method=None,
):
	"""

	Parameters
	----------
	model : Model
	continuous_variable : str
	continuous_variable_label
	bins
	range
	prob_label : str, optional
		A label to put in the legend for the modeled probabilities
	obs_label : str, optional
		A label to put in the legend for the observed choices
	header : str, optional
	subselector : str or array-like, optional


	probability : array-like, optional
		The pre-calculated probability array for all cases in this analysis.
		If not given, the probability array is calculated at the current parameter
		values.

	Returns
	-------
	Elem
	"""

	if model is None:
		return lambda x: distribution_on_continuous_idca_variable(
		x,
		continuous_variable,
		continuous_variable_label=continuous_variable_label,
		bins=bins,
		range=range,
		prob_label=prob_label,
		obs_label=obs_label,
		header=header,
		subselector=subselector,
		)

	cv = model.dataservice.make_dataframes({'ca': [continuous_variable]}, explicit=True).array_ca().reshape(-1)

	if probability is None:
		probability = model.probability()

	model_result = probability[:, :model.dataframes.n_alts]
	model_choice = model.dataframes.data_ch.values
	if model.dataframes.data_wt is not None:
		model_result = model_result.copy()
		model_result *= model.dataframes.data_wt.values[:,None]
		model_choice = model_choice.copy()
		model_choice *= model.dataframes.data_wt.values[:,None]

	if subselector is not None:
		if isinstance(subselector, str):
			subselector = model.dataservice.make_dataframes({'co': [subselector]}, explicit=True).array_co().reshape(-1)
		model_result = model_result[subselector]
		model_choice = model_choice[subselector]

	if style == 'kde':
		import scipy.stats
		kernel_result = scipy.stats.gaussian_kde(cv, bw_method=bw_method, weights=model_result.reshape(-1))
		common_bw = kernel_result.covariance_factor()
		kernel_choice = scipy.stats.gaussian_kde(cv, bw_method=common_bw, weights=model_choice.reshape(-1))

		if range is None:
			range = (cv.min(), cv.max())

		x_midpoints = numpy.linspace(*range, 250)
		y = kernel_result(x_midpoints)
		y_ = kernel_choice(x_midpoints)


	else:
		y, x = numpy.histogram(
			cv,
			weights=model_result.reshape(-1),
			bins=bins,
			range=range,
		)

		y_, x_ = numpy.histogram(
			cv,
			weights=model_choice.reshape(-1),
			bins=x,
		)
		x_midpoints = (x[1:] + x[:-1]) / 2

		x_doubled = numpy.zeros((x.shape[0]-1)*2)
		x_doubled[::2] = x[:-1]
		x_doubled[1::2] = x[1:]

		y_doubled = numpy.zeros((y.shape[0])*2)
		y_doubled_ = numpy.zeros((y.shape[0])*2)

		y_doubled[::2] = y
		y_doubled[1::2] = y
		y_doubled_[::2] = y_
		y_doubled_[1::2] = y_

		y, y_ = y_doubled, y_doubled_
		x_midpoints = x_doubled

	if continuous_variable_label is None:
		continuous_variable_label = continuous_variable


	plt.ioff()
	plt.clf()
	if style=='kde':
		plt.plot(x_midpoints, y, label=prob_label, lw=1.5)
		plt.fill_between(x_midpoints, y_, label=obs_label, step=None, facecolor='#ffbe4d', edgecolor='#ffa200', lw=1.5)
	else:
		plt.plot(x_midpoints, y, label=prob_label, lw=1.5)
		plt.fill_between(x_midpoints, y_, label=obs_label, step=None, facecolor='#ffbe4d', edgecolor='#ffa200', lw=1.5)
	plt.legend()
	plt.xlabel(continuous_variable_label)
	plt.tight_layout(pad=0.5)
	result = plot_as_svg_xhtml(plt, header=header)
	plt.clf()
	return result
