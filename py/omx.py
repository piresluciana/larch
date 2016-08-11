
import tables as _tb
import numpy
import pandas
from .core import LarchError
from .util import dicta

class OMXBadFormat(LarchError):
	pass

class OMXIncompatibleShape(OMXBadFormat):
	pass

class OMXNonUniqueLookup(LarchError):
	pass

class OMX(_tb.file.File):

	def __init__(self, *arg, complevel=5, complib='zlib', **kwarg):
		if 'filters' in kwarg:
			super().__init__(*arg, **kwarg)
		else:
			super().__init__(*arg, filters=_tb.Filters(complib=complib, complevel=complevel), **kwarg)
		try:
			self.data = self._getOrCreatePath("/data", True)
		except _tb.exceptions.FileModeError:
			raise OMXBadFormat("the '/data' node does not exist and cannot be created")
		try:
			self.lookup = self._getOrCreatePath("/lookup", True)
		except _tb.exceptions.FileModeError:
			raise OMXBadFormat("the '/lookup' node does not exist and cannot be created")
		if 'OMX_VERSION' not in self.root._v_attrs:
			try:
				self.root._v_attrs.OMX_VERSION = "0.2"
			except _tb.exceptions.FileModeError:
				raise OMXBadFormat("the root OMX_VERSION attribute does not exist and cannot be created")
		if 'SHAPE' not in self.root._v_attrs:
			try:
				self.root._v_attrs.SHAPE = numpy.zeros(2, dtype=int)
			except _tb.exceptions.FileModeError:
				raise OMXBadFormat("the root SHAPE attribute does not exist and cannot be created")
		self.rlookup = dicta()
		self.rlookup._helper = self.get_reverse_lookup

	@property
	def shape(self):
		sh = self.root._v_attrs.SHAPE[:]
		proposal = (sh[0],sh[1])
		if proposal==(0,0) and self.data._v_nchildren>0:
			first_child_name = next(iter(self.data._v_children.keys()))
			proposal = self.data._v_children[first_child_name].shape
			shp = numpy.empty(2, dtype=int)
			shp[0] = proposal[0]
			shp[1] = proposal[1]
			self.root._v_attrs.SHAPE = shp
		return proposal

	@shape.setter
	def shape(self, x):
		if self.data._v_nchildren>0:
			if x[0] != self.shape[0] and x[1] != self.shape[1]:
				raise OMXIncompatibleShape('this omx has shape {!s} but you want to set {!s}'.format(self.shape, x))
		if self.data._v_nchildren == 0:
			shp = numpy.empty(2, dtype=int)
			shp[0] = x[0]
			shp[1] = x[1]
			self.root._v_attrs.SHAPE = shp

	def add_blank_matrix(self, name, atom=None, shape=None, **kwargs):
		"""

		Note
		----
		This method allows you to add a blank matrix of 3 or more dimemsions, only the first 2 must match the OMX.

		"""
		if name in self.data._v_children:
			return self.data._v_children[name]
		if atom is None:
			atom = _tb.Float64Atom()
		if self.shape == (0,0):
			raise OMXBadFormat('must set a nonzero shape first')
		if shape is not None:
			if shape[:2] != self.shape:
				raise OMXIncompatibleShape('this omx has shape {!s} but you want to set {!s}'.format(self.shape, shape[:2]))
		else:
			shape = self.shape
		return self.create_carray(self.data, name, atom=atom, shape=shape, **kwargs)

	def add_matrix(self, name, obj, *, overwrite=False, **kwargs):
		if len(obj.shape) != 2:
			raise OMXIncompatibleShape('all omx arrays must have 2 dimensional shape')
		if self.data._v_nchildren>0:
			if obj.shape != self.shape:
				raise OMXIncompatibleShape('this omx has shape {!s} but you want to add {!s}'.format(self.shape, obj.shape))
		if self.data._v_nchildren == 0:
			shp = numpy.empty(2, dtype=int)
			shp[0] = obj.shape[0]
			shp[1] = obj.shape[1]
			self.root._v_attrs.SHAPE = shp
		if name in self.data._v_children:
			self.remove_node(self.data, name)
		return self.create_carray(self.data, name, obj=obj, **kwargs)

	def add_lookup(self, name, obj, **kwargs):
		if len(obj.shape) != 1:
			raise OMXIncompatibleShape('all omx lookups must have 1 dimensional shape')
		if self.data._v_nchildren>0:
			if obj.shape[0] not in self.shape:
				raise OMXIncompatibleShape('this omx has shape {!s} but you want to add a lookup with {!s}'.format(self.shape, obj.shape))
		if self.data._v_nchildren == 0:
			raise OMXIncompatibleShape("don't add lookup to omx with no data")
		return self.create_carray(self.lookup, name, obj=obj, **kwargs)

	def get_reverse_lookup(self, name):
		labels = self.lookup._v_children[name][:]
		label_to_i = dict(enumerate(labels))
		self.rlookup[name] = label_to_i
		return label_to_i

	def lookup_to_index(self, lookupname, arr):
		"""Convert an array of lookup-able values into indexes.
		
		If you have an array of lookup-able values (e.g., TAZ identifiers) and you
		want to convert them to 0-based indexes for use in accessing matrix data,
		this is the function for you.
		
		Parameters
		----------
		lookupname : str
			The name of the lookup in the open matrix file. This lookup must already
			exist and have a set of unique lookup values.
		arr : array-like
			An array of values that appear in the lookup. This method uses 
			numpy.digitize to process values, so any target value that appears in `arr` but does
			not appear in the lookup will be assigned the index of the smallest lookup
			value that is greater than the target, or the maximum lookup value if no lookup value
			is greater than the target.
			
		Returns
		-------
		array
			An array of index (int) values, with the same shape as `arr`.
			
		Raises
		------
		OMXNonUniqueLookup
			When the lookup does not contain a set of unique values, this tool is not appropriate.
		
		"""
		from .util.arraytools import is_sorted_and_unique
		labels = self.lookup._v_children[name][:]
		if is_sorted_and_unique(labels):
			return numpy.digitize(arr, labels, right=True)
		uniq_labels, uniq_indexes = numpy.unique(labels, return_inverse=True)
		if len(uniq_labels) != len(labels):
			raise OMXNonUniqueLookup("lookup '{}' does not have unique labels for each item".format(lookupname))
		index_malordered = numpy.digitize(arr, uniq_labels, right=True)
		return uniq_indexes[index_malordered]


	def import_datatable(self, filepath, one_based=True, chunksize=10000, column_map=None, default_atom='float32', log=None):
		"""Import a table in r,c,x,x,x... format into the matrix.
		
		The r and c columns need to be either 0-based or 1-based index values
		(this may be relaxed in the future). The matrix must already be set up
		with the correct size before importing the datatable.
		
		Parameters
		----------
		filepath : str or buffer
			This argument will be fed directly to the :func:`pandas.read_csv` function.
		chunksize : int
			The number of rows of the source file to read as a chunk.  Reading a giant file in moderate sized
			chunks can be much faster and less memory intensive than reading the entire file.
		column_map : dict or None
			If given, this dict maps columns of the input file to OMX tables, with the keys as
			the columns in the input and the values as the tables in the output.
		default_atom : str or dtype
			The default atomic type for imported data when the table does not already exist in this
			openmatrix.
			
		"""
		if log is not None: log("START import_datatable")
		from .util.smartread import SmartFileReader
		sfr = SmartFileReader(filepath)
		reader = pandas.read_csv(sfr, chunksize=chunksize)
		chunk0 = next(pandas.read_csv(filepath, chunksize=10))
		offset = 1 if one_based else 0
		
		if column_map is None:
			column_map = {i:i for i in chunk0.columns}

		if isinstance(default_atom, str):
			default_atom = _tb.Atom.from_dtype(numpy.dtype(default_atom))
		elif isinstance(default_atom, numpy.dtype):
			default_atom = _tb.Atom.from_dtype(default_atom)

		for t in column_map.values():
			self.add_blank_matrix(t, atom=default_atom)

		for n,chunk in enumerate(reader):
			if log is not None: log("PROCESSING CHUNK {} [{}]".format(n, sfr.progress()))
			r = (chunk.iloc[:,0].values-offset)
			c = (chunk.iloc[:,1].values-offset)
			
			if not numpy.issubdtype(r.dtype, numpy.integer):
				r = r.astype(int)
			if not numpy.issubdtype(c.dtype, numpy.integer):
				c = c.astype(int)
			
			for col in chunk.columns:
				if col in column_map:
					self.data._v_children[column_map[col]][r,c] = chunk[col].values
					self.data._v_children[column_map[col]].flush()
			if log is not None:
				log("finished processing chunk {} [{}]".format(n, sfr.progress()))

			self.flush()

#			if n>5:
#				break
		log("import_datatable({}) complete".format(filepath))

	def import_datatable_3d(self, filepath, one_based=True, chunksize=10000, default_atom='float32', log=None):
		"""Import a table in r,c,x,x,x... format into the matrix.
		
		The r and c columns need to be either 0-based or 1-based index values
		(this may be relaxed in the future). The matrix must already be set up
		with the correct size before importing the datatable.
		
		Parameters
		----------
		filepath : str or buffer
			This argument will be fed directly to the :func:`pandas.read_csv` function.
		chunksize : int
			The number of rows of the source file to read as a chunk.  Reading a giant file in moderate sized
			chunks can be much faster and less memory intensive than reading the entire file.
		default_atom : str or dtype
			The default atomic type for imported data when the table does not already exist in this
			openmatrix.
			
		"""
		if log is not None: log("START import_datatable")
		from .util.smartread import SmartFileReader
		sfr = SmartFileReader(filepath)
		reader = pandas.read_csv(sfr, chunksize=chunksize)
		chunk0 = next(pandas.read_csv(filepath, chunksize=10))
		offset = 1 if one_based else 0
		
		if isinstance(default_atom, str):
			default_dtype = numpy.dtype(default_atom)
			default_atom = _tb.Atom.from_dtype(numpy.dtype(default_atom))
		elif isinstance(default_atom, numpy.dtype):
			default_dtype = default_atom
			default_atom = _tb.Atom.from_dtype(default_atom)
		else:
			default_dtype = default_atom.dtype

		#self.add_blank_matrix(matrixname, atom=default_atom, shape=self.shape+(len(chunk0.columns)-2,))

		#temp_slug = self.data._v_children[matrixname][:]
		temp_slug = numpy.zeros( self.shape+(len(chunk0.columns)-2,), dtype=default_dtype )

		for n,chunk in enumerate(reader):
			if log is not None: log("PROCESSING CHUNK {} [{}]".format(n, sfr.progress()))
			r = (chunk.iloc[:,0].values-offset)
			c = (chunk.iloc[:,1].values-offset)
			
			if not numpy.issubdtype(r.dtype, numpy.integer):
				r = r.astype(int)
			if not numpy.issubdtype(c.dtype, numpy.integer):
				c = c.astype(int)
	
			#print("chunk.values",chunk.values.shape)
			#print("self.data._v_children[matrixname][r]",self.data._v_children[matrixname][r].shape)
	
			temp_slug[r,c] = chunk.values[:,2:]
			#self.data._v_children[matrixname].flush()
			if log is not None:
				log("finished processing chunk {} [{}]".format(n, sfr.progress()))

			self.flush()

#			if n>5:
#				break

		for cn,colname in enumerate(chunk0.columns[2:]):
			self.add_blank_matrix(colname, atom=default_atom, shape=self.shape)
			self.data._v_children[colname][:] = temp_slug[:,:,cn]
		
		#self.data._v_children[matrixname][:] = temp_slug[:]
		log("import_datatable({}) complete".format(filepath))

	def __getitem__(self, key):
		if isinstance(key,str):
			if key in self.data._v_children:
				return self.data._v_children[key]
			raise KeyError("matrix named {} not found".format(key))
		raise TypeError("OMX matrix access must be by name (str)")

	def __getattr__(self, key):
		try:
			return super().__getattr__(key)
		except AttributeError:
			if key in self.data._v_children and key not in self.lookup._v_children:
				return self.data._v_children[key]
			if key not in self.data._v_children and key in self.lookup._v_children:
				return self.lookup._v_children[key]
			raise

	def import_omx(self, otherfile, tablenames):
		oth = OMX(otherfile, mode='r')
		for tab in tablenames:
			self.add_matrix(tab, oth.data._v_children[tab][:])


