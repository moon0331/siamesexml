import torch
import torch.nn.functional as F


class _Loss(torch.nn.Module):
    def __init__(self, reduction='mean', pad_ind=None):
        super(_Loss, self).__init__()
        self.reduction = reduction
        self.pad_ind = pad_ind

    def _reduce(self, loss):
        if self.reduction == 'none':
            return loss
        elif self.reduction == 'mean':
            return loss.mean()
        else:
            return loss.sum()

    def _mask_at_pad(self, loss):
        """
        Mask the loss at padding index, i.e., make it zero
        """
        if self.pad_ind is not None:
            loss[:, self.pad_ind] = 0.0
        return loss

    def _mask(self, loss, mask=None):
        """
        Mask the loss at padding index, i.e., make it zero
        * Mask should be a boolean array with 1 where loss needs
        to be considered.
        * it'll make it zero where value is 0
        """
        if mask is not None:
            loss = loss.masked_fill(~mask, 0.0)
        return loss


def _convert_labels_for_svm(y):
    """
        Convert labels from {0, 1} to {-1, 1}
    """
    return 2.*y - 1.0


class HingeLoss(_Loss):
    r""" Hinge loss
    * it'll automatically convert target to +1/-1 as required by hinge loss

    Arguments:
    ----------
    margin: float, optional (default=1.0)
        the margin in hinge loss
    reduction: string, optional (default='mean')
        Specifies the reduction to apply to the output:
        * 'none': no reduction will be applied
        * 'mean' or 'sum': mean or sum of loss terms
    pad_ind: int/int64 or None (default=None)
        ignore loss values at this index
        useful when some index has to be used as padding index
    """

    def __init__(self, margin=1.0, reduction='mean', pad_ind=None):
        super(HingeLoss, self).__init__(reduction, pad_ind)
        self.margin = margin

    def forward(self, input, target, mask=None):
        """
        Arguments:
        ---------
        input: torch.FloatTensor
            real number pred matrix of size: batch_size x output_size
            typically logits from the neural network
        target:  torch.FloatTensor
            0/1 ground truth matrix of size: batch_size x output_size
            * it'll automatically convert to +1/-1 as required by hinge loss
        mask: torch.BoolTensor or None, optional (default=None)
            ignore entries [won't contribute to loss] where mask value is zero

        Returns:
        -------
        loss: torch.FloatTensor
            dimension is defined based on reduction
        """
        loss = F.relu(self.margin - _convert_labels_for_svm(target)*input)
        loss = self._mask_at_pad(loss)
        loss = self._mask(loss, mask)
        return self._reduce(loss)


class SquaredHingeLoss(_Loss):
    r""" Squared Hinge loss
    * it'll automatically convert target to +1/-1 as required by hinge loss

    Arguments:
    ----------
    margin: float, optional (default=1.0)
        the margin in squared hinge loss
    reduction: string, optional (default='mean')
        Specifies the reduction to apply to the output:
        * 'none': no reduction will be applied
        * 'mean' or 'sum': mean or sum of loss terms
    pad_ind: int/int64 or None (default=None)
        ignore loss values at this index
        useful when some index has to be used as padding index
    """

    def __init__(self, margin=1.0, size_average=None, reduce=True,
                 reduction='mean'):
        super(SquaredHingeLoss, self).__init__(size_average, reduce, reduction)
        self.margin = margin

    def forward(self, input, target, mask=None):
        """
        Arguments:
        ---------
        input: torch.FloatTensor
            real number pred matrix of size: batch_size x output_size
            typically logits from the neural network
        target:  torch.FloatTensor
            0/1 ground truth matrix of size: batch_size x output_size
            * it'll automatically convert to +1/-1 as required by hinge loss
        mask: torch.BoolTensor or None, optional (default=None)
            ignore entries [won't contribute to loss] where mask value is zero

        Returns:
        -------
        loss: torch.FloatTensor
            dimension is defined based on reduction
        """
        loss = F.relu(self.margin - _convert_labels_for_svm(target)*input)
        loss = loss**2
        loss = self._mask_at_pad(loss)
        loss = self._mask(loss, mask)
        return self._reduce(loss)


class BCEWithLogitsLoss(_Loss):
    r""" BCE loss (expects logits; numercial stable)
    This loss combines a `Sigmoid` layer and the `BCELoss` in one single
    class. This version is more numerically stable than using a plain `Sigmoid`
    followed by a `BCELoss` as, by combining the operations into one layer,
    we take advantage of the log-sum-exp trick for numerical stability.

    Arguments:
    ----------
    weight: torch.Tensor or None, optional (default=None))
        a manual rescaling weight given to the loss of each batch element.
        If given, has to be a Tensor of size batch_size
    reduction: string, optional (default='mean')
        Specifies the reduction to apply to the output:
        * 'none': no reduction will be applied
        * 'mean' or 'sum': mean or sum of loss terms
    pos_weight: torch.Tensor or None, optional (default=None)
        a weight of positive examples.
        it must be a vector with length equal to the number of classes.
    pad_ind: int/int64 or None (default=None)
        ignore loss values at this index
        useful when some index has to be used as padding index
    """
    __constants__ = ['weight', 'pos_weight', 'reduction']

    def __init__(self, weight=None, reduction='mean',
                 pos_weight=None, pad_ind=None):
        super(BCEWithLogitsLoss, self).__init__(reduction, pad_ind)
        self.register_buffer('weight', weight)
        self.register_buffer('pos_weight', pos_weight)

    def forward(self, input, target, mask=None):
        """
        Arguments:
        ---------
        input: torch.FloatTensor
            real number pred matrix of size: batch_size x output_size
            typically logits from the neural network
        target:  torch.FloatTensor
            0/1 ground truth matrix of size: batch_size x output_size
        mask: torch.BoolTensor or None, optional (default=None)
            ignore entries [won't contribute to loss] where mask value is zero

        Returns:
        -------
        loss: torch.FloatTensor
            dimension is defined based on reduction
        """
        loss = F.binary_cross_entropy_with_logits(input, target,
                                                  self.weight,
                                                  pos_weight=self.pos_weight,
                                                  reduction='none')
        loss = self._mask_at_pad(loss)
        loss = self._mask(loss, mask)
        return self._reduce(loss)


class CosineEmbeddingLoss(_Loss):
    r""" Cosine embedding loss (expects cosine similarity)

    Arguments:
    ----------
    weight: torch.Tensor or None, optional (default=None))
        a manual rescaling weight given to the loss of each batch element.
        If given, has to be a Tensor of size batch_size
    reduction: string, optional (default='mean')
        Specifies the reduction to apply to the output:
        * 'none': no reduction will be applied
        * 'mean' or 'sum': mean or sum of loss terms
    pos_weight: float or None, optional (default=None)
        weight of loss with positive target
    pad_ind: int/int64 or None (default=None)
        ignore loss values at this index
        useful when some index has to be used as padding index
    """

    def __init__(self, margin=0.8, reduction='mean', pos_weight=1.0):
        super(CosineEmbeddingLoss, self).__init__(reduction=reduction)
        self.margin = margin
        self.pos_weight = pos_weight

    def forward(self, input, target, mask=None):
        """
        Arguments:
        ---------
        input: torch.FloatTensor
            real number pred matrix of size: batch_size x output_size
            cosine similarity b/w label and document
        target:  torch.FloatTensor
            0/1 ground truth matrix of size: batch_size x output_size
        mask: torch.BoolTensor or None, optional (default=None)
            ignore entries [won't contribute to loss] where mask value is zero

        Returns:
        -------
        loss: torch.FloatTensor
            dimension is defined based on reduction
        """
        loss = torch.where(target > 0, (1-input) * self.pos_weight,
                           torch.max(
                               torch.zeros_like(input), input - self.margin))
        loss = self._mask_at_pad(loss)
        loss = self._mask(loss, mask)
        return self._reduce(loss)
    
    
    class TripletMarginLossOHNM(_Loss):
    r""" Triplet Margin Loss with Online Hard Negative Mining 

    Arguments:
    ----------
    weight: torch.Tensor or None, optional (default=None))
        a manual rescaling weight given to the loss of each batch element.
        If given, has to be a Tensor of size batch_size
    reduction: string, optional (default='mean')
        Specifies the reduction to apply to the output:
        * 'none': no reduction will be applied
        * 'mean' or 'sum': mean or sum of loss terms
    pos_weight: float or None, optional (default=None)
        weight of loss with positive target
    pad_ind: int/int64 or None (default=None)
        ignore loss values at this index
        useful when some index has to be used as padding index
    """

    def __init__(self, margin=0.8, reduction='mean'):
        super(TripletMarginLossOHNM, self).__init__(reduction=reduction)
        self.margin = margin

    def forward(self, doc_embeddings, label_embeddings, selection):
        """
        Arguments:
        ---------
        doc_embeddings: torch.FloatTensor
            real number matrix of size: batch_size x embedding dimension
            embedding of documents in minibatch
        label_embeddings: torch.FloatTensor
            real number matrix of size: batch_size x embedding dimension
            embedding of positive labels in minibatch corresponding to each document
        selection: torch.FloatTensor
            0/1 matrix of size batch_size x batch_size
            (i, j)th entry is 1 if label j is positive for document i else 0

        Returns:
        -------
        loss: torch.FloatTensor
            dimension is defined based on reduction
        """
        
        similarities = torch.min(doc_embeddings @ label_embeddings.T, 1 - selection)
        _, indices = torch.topk(similarities, largest=True, dim=1, k=1)
        negative_label_embeddings = label_embeddings[indices[:, 0]]
        
        sim_p = F.cosine_similarity(doc_embeddings, label_embeddings, dim = 1, eps = self._eps)
        sim_n = F.cosine_similarity(doc_embeddings, negative_label_embeddings, dim = 1, eps = self._eps)
        
        loss = torch.max(torch.zeros_like(sim_p), sim_n - sim_p + margin)

        if (self._reduction == "mean"):
            reduced_loss = loss.mean()
        else:
            reduced_loss = loss.sum()
            
        return reduced_loss

