# cython: language_level=3

from .general_precision cimport *
from .model.controller cimport Model5c

from libc.stdint cimport int8_t, int64_t

cdef class DataFrames:

	cdef:
		# Pandas DataFrames
		object _data_co
		object _data_ca
		object _data_ce
		object _data_av
		object _data_ch
		object _data_wt
		# Internal array references
		l4_float_t[:,:]   _array_co
		l4_float_t[:,:,:] _array_ca
		l4_float_t[:,:]   _array_ce
		object            _array_ce_caseindexes
		object            _array_ce_altindexes
		int64_t[:,:]      _array_ce_reversemap
		int8_t    [:,:]   _array_av
		l4_float_t[:,:]   _array_ch
		l4_float_t[:]     _array_wt
		# Model position mappings
		int[:] model_utility_ca_param
		int[:] model_utility_ca_data
		int[:] model_utility_co_alt
		int[:] model_utility_co_param
		int[:] model_utility_co_data
		int[:] model_quantity_ca_param
		int[:] model_quantity_ca_data
		int    model_quantity_scale_param
		# Model parameter values
		l4_float_t[:] model_utility_ca_param_value
		int8_t[:]     model_utility_ca_param_holdfast
		l4_float_t[:] model_utility_co_param_value
		int8_t[:]     model_utility_co_param_holdfast
		l4_float_t[:] model_quantity_ca_param_value
		int8_t[:]     model_quantity_ca_param_holdfast
		l4_float_t    model_quantity_scale_param_value
		int8_t        model_quantity_scale_param_holdfast

		# Data scalers
		object _std_scaler_ca
		object _std_scaler_co
		object _std_scaler_ce
		l4_float_t _weight_normalization

		# Aux data
		object _alternative_codes
		object _alternative_names

		# Linked Model Attributes
		int _n_model_params
		object _model_param_names
		Model5c _model

	# cdef void _compute_utility_onecase(
	# 		self,
	# 		int c,
	# 		l4_float_t[:] U,
	# ) nogil

	cdef void _compute_d_utility_onecase(
			self,
			int c,
			l4_float_t[:] U,
			l4_float_t[:,:] dU,
			int n_alts,
	) nogil

	cdef void _compute_utility_onecase(
			self,
			int c,
			l4_float_t[:] U,
			int n_alts,
	) nogil


	cdef l4_float_t[:] _get_choice_onecase(
			self,
			int c,
	) nogil

	cdef void _copy_choice_onecase(
			self,
			int c,
			l4_float_t[:] into_array,
	) nogil

	cdef int _n_alts(self)

	cdef int _n_cases(self)

	cdef void _read_in_model_parameters(self)

	cdef void _link_to_model_structure(
			self,
			Model5c model,
	)

	cdef int _check_data_is_sufficient_for_model(
			self,
			Model5c model,
	) except -1
