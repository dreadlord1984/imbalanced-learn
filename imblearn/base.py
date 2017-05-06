﻿"""Base class for sampling"""

# Authors: Guillaume Lemaitre <g.lemaitre58@gmail.com>
#          Christos Aridas
# License: MIT

from __future__ import division

import logging
import warnings
from numbers import Real
from abc import ABCMeta, abstractmethod
from collections import Counter

import numpy as np
from sklearn.base import BaseEstimator
from sklearn.externals import six
from sklearn.utils import check_X_y
from sklearn.utils.multiclass import type_of_target
from sklearn.utils.validation import check_is_fitted


class SamplerMixin(six.with_metaclass(ABCMeta, BaseEstimator)):
    """Mixin class for samplers with abstact method.

    Warning: This class should not be used directly. Use the derive classes
    instead.
    """

    _estimator_type = 'sampler'

    def fit(self, X, y):
        """Find the classes statistics before to perform sampling.

        Parameters
        ----------
        X : ndarray, shape (n_samples, n_features)
            Matrix containing the data which have to be sampled.

        y : ndarray, shape (n_samples, )
            Corresponding label for each sample in X.

        Returns
        -------
        self : object,
            Return self.

        """

        # Check the consistency of X and y
        X, y = check_X_y(X, y)

        self.min_c_ = None
        self.maj_c_ = None
        self.stats_c_ = {}
        self.X_shape_ = None

        if hasattr(self, 'ratio'):
            self._validate_ratio()

        if hasattr(self, 'size_ngh'):
            self._validate_size_ngh_deprecation()
        elif hasattr(self, 'k') and not hasattr(self, 'm'):
            self._validate_k_deprecation()
        elif hasattr(self, 'k') and hasattr(self, 'm'):
            self._validate_k_m_deprecation()

        self.logger.info('Compute classes statistics ...')

        # Raise an error if there is only one class
        if np.unique(y).size <= 1:
            raise ValueError("Sampler can't balance when only one class is"
                             " present.")

        # Store the size of X to check at sampling time if we have the
        # same data
        self.X_shape_ = X.shape

        # Create a dictionary containing the class statistics
        self.stats_c_ = Counter(y)

        # Find the minority and majority classes
        self.min_c_ = min(self.stats_c_, key=self.stats_c_.get)
        self.maj_c_ = max(self.stats_c_, key=self.stats_c_.get)

        self.logger.info('%s classes detected: %s',
                         np.unique(y).size, self.stats_c_)

        # Check if the ratio provided at initialisation make sense
        if isinstance(self.ratio, Real):
            if self.ratio < (self.stats_c_[self.min_c_] /
                             self.stats_c_[self.maj_c_]):
                raise RuntimeError('The ratio requested at initialisation'
                                   ' should be greater or equal than the'
                                   ' balancing ratio of the current data.'
                                   ' Got {} < {}.'.format(
                                       self.ratio,
                                       self.stats_c_[self.min_c_] /
                                       self.stats_c_[self.maj_c_]))

        return self

    def sample(self, X, y):
        """Resample the dataset.

        Parameters
        ----------
        X : ndarray, shape (n_samples, n_features)
            Matrix containing the data which have to be sampled.

        y : ndarray, shape (n_samples, )
            Corresponding label for each sample in X.

        Returns
        -------
        X_resampled : ndarray, shape (n_samples_new, n_features)
            The array containing the resampled data.

        y_resampled : ndarray, shape (n_samples_new)
            The corresponding label of `X_resampled`

        """

        # Check the consistency of X and y
        X, y = check_X_y(X, y)

        # Check that the data have been fitted
        check_is_fitted(self, 'stats_c_')

        # Check if the size of the data is identical than at fitting
        if X.shape != self.X_shape_:
            raise RuntimeError('The data that you attempt to resample do not'
                               ' seem to be the one earlier fitted. Use the'
                               ' fitted data. Shape of data is {}, got {}'
                               ' instead.'.format(X.shape, self.X_shape_))

        if hasattr(self, 'ratio'):
            self._validate_ratio()

        if hasattr(self, 'size_ngh'):
            self._validate_size_ngh_deprecation()
        elif hasattr(self, 'k') and not hasattr(self, 'm'):
            self._validate_k_deprecation()
        elif hasattr(self, 'k') and hasattr(self, 'm'):
            self._validate_k_m_deprecation()

        return self._sample(X, y)

    def fit_sample(self, X, y):
        """Fit the statistics and resample the data directly.

        Parameters
        ----------
        X : ndarray, shape (n_samples, n_features)
            Matrix containing the data which have to be sampled.

        y : ndarray, shape (n_samples, )
            Corresponding label for each sample in X.

        Returns
        -------
        X_resampled : ndarray, shape (n_samples_new, n_features)
            The array containing the resampled data.

        y_resampled : ndarray, shape (n_samples_new)
            The corresponding label of `X_resampled`

        """

        return self.fit(X, y).sample(X, y)

    def _validate_ratio(self):
        # The ratio correspond to the number of samples in the minority class
        # over the number of samples in the majority class. Thus, the ratio
        # cannot be greater than 1.0
        if isinstance(self.ratio, Real):
            if self.ratio > 1:
                raise ValueError('Ratio cannot be greater than one.'
                                 ' Got {}.'.format(self.ratio))
            elif self.ratio <= 0:
                raise ValueError('Ratio cannot be negative.'
                                 ' Got {}.'.format(self.ratio))

        elif isinstance(self.ratio, six.string_types):
            if self.ratio != 'auto':
                raise ValueError("Unknown string for the parameter ratio."
                                 " Got {} instead of 'auto'".format(
                                     self.ratio))
        else:
            raise ValueError('Unknown parameter type for ratio.'
                             ' Got {} instead of float or str'.format(
                                 type(self.ratio)))

    def _validate_size_ngh_deprecation(self):
        "Private function to warn about the deprecation about size_ngh."

        # Announce deprecation if necessary
        if self.size_ngh is not None:
            warnings.warn('`size_ngh` will be replaced in version 0.4. Use'
                          ' `n_neighbors` instead.', DeprecationWarning)
            self.n_neighbors = self.size_ngh

    def _validate_k_deprecation(self):
        """Private function to warn about deprecation of k in ADASYN"""
        if self.k is not None:
            warnings.warn('`k` will be replaced in version 0.4. Use'
                          ' `n_neighbors` instead.', DeprecationWarning)
            self.n_neighbors = self.k

    def _validate_k_m_deprecation(self):
        """Private function to warn about deprecation of k in ADASYN"""
        if self.k is not None:
            warnings.warn('`k` will be replaced in version 0.4. Use'
                          ' `k_neighbors` instead.', DeprecationWarning)
            self.k_neighbors = self.k

        if self.m is not None:
            warnings.warn('`m` will be replaced in version 0.4. Use'
                          ' `m_neighbors` instead.', DeprecationWarning)
            self.m_neighbors = self.m

    @abstractmethod
    def _sample(self, X, y):
        """Resample the dataset.

        Parameters
        ----------
        X : ndarray, shape (n_samples, n_features)
            Matrix containing the data which have to be sampled.

        y : ndarray, shape (n_samples, )
            Corresponding label for each sample in X.

        Returns
        -------
        X_resampled : ndarray, shape (n_samples_new, n_features)
            The array containing the resampled data.

        y_resampled : ndarray, shape (n_samples_new)
            The corresponding label of `X_resampled`
        """
        pass

    def __getstate__(self):
        """Prevent logger from being pickled."""
        object_dictionary = self.__dict__.copy()
        del object_dictionary['logger']
        return object_dictionary

    def __setstate__(self, dict):
        """Re-open the logger."""
        logger = logging.getLogger(__name__)
        self.__dict__.update(dict)
        self.logger = logger


class BaseBinarySampler(six.with_metaclass(ABCMeta, SamplerMixin)):
    """Base class for all binary class sampler.

    Warning: This class should not be used directly. Use derived classes
    instead.

    """

    def __init__(self, ratio='auto', random_state=None):
        """Initialize this object and its instance variables.

        Parameters
        ----------
        ratio : str or float, optional (default='auto')
            If 'auto', the ratio will be defined automatically to balanced
            the dataset. Otherwise, the ratio will corresponds to the number
            of samples in the minority class over the the number of samples
            in the majority class.

        random_state : int, RandomState or None, optional (default=None)

            - If int, random_state is the seed used by the random number
            generator;
            - If RandomState instance, random_state is the random number
            generator;
            - If None, the random number generator is the RandomState instance
            used by np.random.

        Returns
        -------
        None

        """
        self.ratio = ratio
        self.random_state = random_state
        self.logger = logging.getLogger(__name__)

    def fit(self, X, y):
        """Find the classes statistics before to perform sampling.

        Parameters
        ----------
        X : ndarray, shape (n_samples, n_features)
            Matrix containing the data which have to be sampled.

        y : ndarray, shape (n_samples, )
            Corresponding label for each sample in X.

        Returns
        -------
        self : object,
            Return self.

        """

        super(BaseBinarySampler, self).fit(X, y)

        # Check that the target type is binary
        if not type_of_target(y) == 'binary':
            warnings.simplefilter('always', UserWarning)
            warnings.warn('The target type should be binary.')

        return self


class BaseMulticlassSampler(six.with_metaclass(ABCMeta, SamplerMixin)):
    """Base class for all multiclass sampler.

    Warning: This class should not be used directly. Use derived classes
    instead.

    """
    def __init__(self, ratio='auto', random_state=None):
        """Initialize this object and its instance variables.

        Parameters
        ----------
        ratio : str or float, optional (default='auto')
            If 'auto', the ratio will be defined automatically to balanced
            the dataset. Otherwise, the ratio will corresponds to the number
            of samples in the minority class over the the number of samples
            in the majority class.

        random_state : int, RandomState or None, optional (default=None)

            - If int, random_state is the seed used by the random number
            generator;
            - If RandomState instance, random_state is the random number
            generator;
            - If None, the random number generator is the RandomState instance
            used by np.random.

        Returns
        -------
        None

        """
        self.ratio = ratio
        self.random_state = random_state
        self.logger = logging.getLogger(__name__)

    def fit(self, X, y):
        """Find the classes statistics before to perform sampling.

        Parameters
        ----------
        X : ndarray, shape (n_samples, n_features)
            Matrix containing the data which have to be sampled.

        y : ndarray, shape (n_samples, )
            Corresponding label for each sample in X.

        Returns
        -------
        self : object,
            Return self.

        """

        super(BaseMulticlassSampler, self).fit(X, y)

        # Check that the target type is either binary or multiclass
        if not (type_of_target(y) == 'binary' or
                type_of_target(y) == 'multiclass'):
            warnings.simplefilter('always', UserWarning)
            warnings.warn('The target type should be binary or multiclass.')

        return self
