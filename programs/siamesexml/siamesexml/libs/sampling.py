import numpy as np
import _pickle as pickle
from functools import partial
import warnings


class BaseSampler(object):
    """Sampler with support for sampling from
        multinomial distribution
    Parameters:
    ----------
    a: int
        sample spce
    num_samples: int
        #samples
    probs: np.ndarray or None, optional, default=None
        probability of each item
    replace: boolean, optional, default=False
        with or without replacement
    """
    def __init__(self, size, num_samples, prob=None, replace=True):
        self.size = size
        self.num_samples = num_samples
        self.prob = prob
        self.replace = replace
        self.index = None
        self._construct()

    def _construct(self):
        """Create a partial function with given parameters
        Index should take one argument i.e. size during querying
        """
        self.index = partial(np.random.randint, low=0, high=self.size)

    def _query(self):
        """Query for one sample
        """
        return (self.index(size=self.num_samples), [1.0]*self.num_samples)

    def query(self, num_instances, *args, **kwargs):
        """Query shortlist for one or more samples
        """
        if num_instances == 1:
            return self._query()
        else:
            out = [self._query() for _ in range(num_instances)]
            return out

    def save(self, fname):
        """
            Save object
        """
        state = self.__dict__
        pickle.dump(state, open(fname, 'wb'))

    def load(self, fname):
        """ Load object
        """
        self = pickle.load(open(fname, 'rb'))

    @property
    def data_init(self):
        return True if self.index is not None else False


class NegativeSampler(BaseSampler):
    """Negative sampler with support for sampling from
        multinomial distribution
    Parameters:
    ----------
    num_samples: int
        sample spce
    num_negatives: int
        #samples
    probs: np.ndarray or None, optional, default=None
        probability of each item
    replace: boolean, optional, default=False
        with or without replacement
    """
    def __init__(self, num_labels, num_negatives, prob=None, replace=True):
        super().__init__(num_labels, num_negatives, prob, replace)

    def _construct(self):
        self.index = partial(
            np.random.default_rng().choice, a=self.size,
            replace=self.replace, p=self.prob)


class Sampler(BaseSampler):
    """Sampler with support for sampling from
        multinomial distribution
    Parameters:
    ----------
    size: int
        sample from this space
    num_samples: int
        #samples
    probs: np.ndarray or None, optional, default=None
        probability of each item
    replace: boolean, optional, default=False
        with or without replacement
    """
    def __init__(self, num_labels, num_samples, prob=None, replace=True):
        warnings.warn("Support only for one sample as of now.")
        super().__init__(num_labels, num_samples, prob, replace)

    def _construct(self):
        self.index = partial(
            np.random.default_rng().choice,
            replace=self.replace)

    def _query(self, ind):
        """Query for one sample
        """
        prob = None
        if self.prob is not None:
            prob = self.prob[ind]
        return (self.index(a=ind, p=prob), [1.0])

    def query(self, num_instances, ind, *args, **kwargs):
        """Query shortlist for one or more samples;
        Pick labels from given indices
        """
        if num_instances == 1:
            return self._query(ind)
        else:
            out = [self._query(ind[i]) for i in range(num_instances)]
            return out
