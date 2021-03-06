
import numpy
import pandas

from .util import Dict, dictx
from .model import Model

import logging
from .log import logger_name
logger = logging.getLogger(logger_name)

def doctor(
		dfs,
		repair_ch_av=None,
		repair_ch_zq=None,
		repair_asc=None,
		repair_noch_nowt=None,
		repair_nan_wt=None,
		verbose=3,
):
	problems = dictx()

	if isinstance(dfs, Model) and dfs.dataframes is None:
		raise ValueError('no dataframes loaded, try `.load_data()` first')

	logger.info("checking for chosen-but-zero-quantity")
	dfs, diagnosis = chosen_but_zero_quantity(dfs, repair=repair_ch_zq, verbose=verbose)
	if diagnosis is not None:
		logger.warning(f'problem: chosen-but-zero-quantity ({len(diagnosis)} issues)')
		problems['chosen_but_zero_quantity'] = diagnosis

	logger.info("checking for chosen-but-not-available")
	dfs, diagnosis = chosen_but_not_available(dfs, repair=repair_ch_av, verbose=verbose)
	if diagnosis is not None:
		logger.warning(f'problem: chosen-but-not-available ({len(diagnosis)} issues)')
		problems['chosen_but_not_available'] = diagnosis

	logger.info("checking for nothing-chosen-but-nonzero-weight")
	dfs, diagnosis = nothing_chosen_but_nonzero_weight(dfs, repair=repair_noch_nowt, verbose=verbose)
	if diagnosis is not None:
		logger.warning(f'problem: nothing-chosen-but-nonzero-weight ({len(diagnosis)} issues)')
		problems['nothing_chosen_but_nonzero_weight'] = diagnosis

	logger.info("checking for nan-weight")
	dfs, diagnosis = nan_weight(dfs, repair=repair_nan_wt, verbose=verbose)
	if diagnosis is not None:
		logger.warning(f'problem: nan-weight ({len(diagnosis)} issues)')
		problems['nan_weight'] = diagnosis

	logger.info("checking for low-variance-data-co")
	dfs, diagnosis = low_variance_data_co(dfs, repair=None, verbose=verbose)
	if diagnosis is not None:
		logger.warning(f'problem: low-variance-data-co ({len(diagnosis)} issues)')
		problems['low_variance_data_co'] = diagnosis

	# if repair_asc:
	# 	x = self.cleanup_asc_problems()
	# 	if x is not None:
	# 		problems['asc_for_never_chosen'] = x
	return dfs, problems



def chosen_but_not_available(dfs, repair=None, verbose=3):
	"""
	Check if some observations are chosen but not available

	Parameters
	----------
	dfs : DataFrames or Model
		The data to check
	repair : {None, '+', '-', }
		How to repair the data.
		Plus will make the conflicting alternatives available.
		Minus will make them not chosen (possibly leaving no chosen alternative).
		None effects no repair, and simply emits a warning.
	verbose : int, default 3
		The number of example rows to list for each problem.

	Returns
	-------
	dfs : DataFrames
		The revised dataframe
	diagnosis : pandas.DataFrame
		The number of bad instances, by alternative, and some example rows.

	"""

	if isinstance(dfs, Model):
		m = dfs
		dfs = m.dataframes
	else:
		m = None

	if m is not None and dfs.data_ch.shape[1] == len(m.graph):
		# choice data is wide, make availability data wide
		data_av = dfs.data_av_cascade(m.graph)
	else:
		data_av = dfs.data_av

	_not_avail = (data_av==0).values
	_chosen = (dfs.data_ch > 0).values
	_wid = min(_not_avail.shape[1], _chosen.shape[1])

	chosen_but_not_available = pandas.DataFrame(
		data=_not_avail[:, :_wid] & _chosen[:, :_wid],
		index=data_av.index,
		columns=data_av.columns[:_wid],
	)
	chosen_but_not_available_sum = chosen_but_not_available.sum(0)

	diagnosis = None
	if chosen_but_not_available_sum.sum() > 0:

		i1, i2 = numpy.where(chosen_but_not_available)

		diagnosis = pandas.DataFrame(
			chosen_but_not_available_sum[chosen_but_not_available_sum > 0],
			columns=['n', ],
		)

		for colnum, colname in enumerate(chosen_but_not_available.columns):
			if chosen_but_not_available_sum[colname] > 0:
				diagnosis.loc[colname, 'example rows'] = ", ".join(str(j) for j in i1[i2 == colnum][:verbose])

		if repair == '+':
			dfs.data_av.values[chosen_but_not_available] = 1
		elif repair == '-':
			dfs.data_ch.values[chosen_but_not_available] = 0

	if m is None:
		return dfs, diagnosis
	else:
		return m, diagnosis



def chosen_but_zero_quantity(dfs, repair=None, verbose=3):
	"""
	Check if some observations are chosen but have zero quantity.

	Parameters
	----------
	dfs : DataFrames or Model
		The data to check
	repair : {None, '-', }
		How to repair the data.
		Minus will make them not chosen (possibly leaving no chosen alternative).
		None effects no repair, and simply emits a warning.
	verbose : int, default 3
		The number of example rows to list for each problem.

	Returns
	-------
	dfs : DataFrames
		The revised dataframe
	diagnosis : pandas.DataFrame
		The number of bad instances, by alternative, and some example rows.

	"""

	if repair not in ('-', None):
		raise ValueError(f'invalid repair setting "{repair}"')

	if isinstance(dfs, Model):
		m = dfs
		dfs = m.dataframes
	else:
		m = None

	try:
		zero_q = dfs.get_zero_quantity_ca()
	except ValueError:
		diagnosis = None

	else:
		_zero_q = (zero_q>0).values
		_chosen = (dfs.data_ch > 0).values
		_wid = min(_zero_q.shape[1], _chosen.shape[1])

		chosen_but_zero_quantity = pandas.DataFrame(
			data=_zero_q[:, :_wid] & _chosen[:, :_wid],
			index=dfs.data_av.index,
			columns=dfs.data_av.columns[:_wid],
		)
		chosen_but_zero_quantity_sum = chosen_but_zero_quantity.sum(0)

		diagnosis = None
		if chosen_but_zero_quantity_sum.sum() > 0:

			i1, i2 = numpy.where(chosen_but_zero_quantity)

			diagnosis = pandas.DataFrame(
				chosen_but_zero_quantity_sum[chosen_but_zero_quantity_sum > 0],
				columns=['n', ],
			)

			for colnum, colname in enumerate(chosen_but_zero_quantity.columns):
				if chosen_but_zero_quantity_sum[colname] > 0:
					diagnosis.loc[colname, 'example rows'] = ", ".join(str(j) for j in i1[i2 == colnum][:verbose])

			if repair == '-':
				dfs.data_ch.values[chosen_but_zero_quantity] = 0

	if m is None:
		return dfs, diagnosis
	else:
		return m, diagnosis




def nothing_chosen_but_nonzero_weight(dfs, repair=None, verbose=3):
	"""
	Check if some observations are chosen but not available

	Parameters
	----------
	dfs : DataFrames or Model
		The data to check
	repair : {None, '-', '*'}
		How to repair the data.
		Minus will make the weight zero.
		Star will make the weight zero plus autoscale all remaining weights.
		None effects no repair, and simply emits a warning.
	verbose : int, default 3
		The number of example rows to list for each problem.

	Returns
	-------
	dfs : DataFrames
		The revised dataframe
	diagnosis : pandas.DataFrame
		The number of bad instances, by alternative, and some example rows.

	"""

	if isinstance(dfs, Model):
		m = dfs
		dfs = m.dataframes
	else:
		m = None

	diagnosis = None

	if dfs is None:
		raise ValueError('data not loaded')

	if dfs.data_wt is not None and dfs.data_ch is not None:

		nothing_chosen = (dfs.array_ch().sum(1) == 0)
		nothing_chosen_some_weight = nothing_chosen & (dfs.array_wt().reshape(-1) > 0)
		if nothing_chosen_some_weight.sum() > 0:

			i1 = numpy.where(nothing_chosen_some_weight)[0]

			diagnosis = pandas.DataFrame(
				[nothing_chosen_some_weight.sum(), ],
				columns=['n', ],
				index=['nothing_chosen_some_weight', ]
			)

			diagnosis.loc['nothing_chosen_some_weight', 'example rows'] = ", ".join(str(j) for j in i1[:verbose])
			if repair == '+':
				raise ValueError("cannot resolve chosen_but_zero_quantity by assuming some choice")
			elif repair == '-':
				dfs.array_wt()[nothing_chosen] = 0
			elif repair == '*':
				dfs.array_wt()[nothing_chosen] = 0
				dfs.autoscale_weights()
	if m is None:
		return dfs, diagnosis
	else:
		return m, diagnosis


def nan_weight(dfs, repair=None, verbose=3):
	"""
	Check if some observations are chosen but not available

	Parameters
	----------
	dfs : DataFrames or Model
		The data to check
	repair : None or bool
		Whether to repair the data.
		Any true value will make NaN values in the weight zero.
		None effects no repair, and simply emits a warning.
	verbose : int, default 3
		The number of example rows to list for each problem.

	Returns
	-------
	dfs : DataFrames
		The revised dataframe
	diagnosis : pandas.DataFrame
		The number of bad instances, and some example rows.

	"""
	if isinstance(dfs, Model):
		m = dfs
		dfs = m.dataframes
	else:
		m = None

	diagnosis = None
	if dfs.data_wt is not None:
		nan_wgt = numpy.isnan(dfs.data_wt.iloc[:, 0])

		if nan_wgt.sum():
			i = numpy.where(nan_wgt)[0]

			diagnosis = pandas.DataFrame(
				data=[[nan_wgt.sum(), '']],
				columns=['n', 'example rows'],
				index=['nan_weight'],
			)

			diagnosis.loc['nan_weight', 'example rows'] = ", ".join(str(j) for j in i[:verbose])

		if repair:
			dfs.data_wt.fillna(0, inplace=True)

	if m is None:
		return dfs, diagnosis
	else:
		return m, diagnosis



def low_variance_data_co(dfs, repair=None, verbose=3):
	"""
	Check if any data_co columns have very low variance.

	Parameters
	----------
	dfs : DataFrames or Model
		The data to check
	repair : None
		Not implemented.
	verbose : int, default 3
		The number of example columns to list if
		there is a problem.

	Returns
	-------
	dfs : DataFrames
		The revised dataframe
	diagnosis : pandas.DataFrame
		The number of bad instances, and some example rows.

	"""
	if isinstance(dfs, Model):
		m = dfs
		dfs = m.dataframes
	else:
		m = None

	diagnosis = None
	if dfs.data_co is not None:
		variance = dfs.data_co.var()
		if variance.min() < 1e-3:
			i = numpy.where(variance < 1e-3)[0]

			diagnosis = pandas.DataFrame(
				data=[[len(i), '']],
				columns=['n', 'example cols'],
				index=['low_variance_co'],
			)

			diagnosis.loc['low_variance_co', 'example cols'] = ", ".join(str(dfs.data_co.columns[j]) for j in i[:verbose])

	if m is None:
		return dfs, diagnosis
	else:
		return m, diagnosis
