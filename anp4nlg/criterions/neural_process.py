
import torch
import math
from fairseq import metrics, modules, utils
from fairseq.criterions import FairseqCriterion, register_criterion

from torch.distributions.kl import kl_divergence

@register_criterion("neural_process")
class NeuralProcessCriterion(FairseqCriterion):
    """
    Implementation for the loss used in masked language model (MLM) training.
    """

    def __init__(self, task):
        super().__init__(task)

    def _compute_loss(self, p_y_pred, y_target, q_target, q_context):
        """
        Computes Neural Process loss.
        Parameters
        ----------
        p_y_pred : one of torch.distributions.Distribution
            Distribution over y output by Neural Process.
        y_target : torch.Tensor
            Shape (batch_size, num_target, y_dim)
        q_target : one of torch.distributions.Distribution
            Latent distribution for target points.
        q_context : one of torch.distributions.Distribution
            Latent distribution for context points.
        """
        # Log likelihood has shape (batch_size, num_target, y_dim). Take mean
        # over batch and sum over number of targets and dimensions of y
        log_likelihood = torch.distributions.Categorical(
            logits=p_y_pred).log_prob(y_target).sum(dim=1).mean()
        # KL has shape (batch_size, r_dim). Take mean over batch and sum over
        # r_dim (since r_dim is dimension of normal distribution)
        kl = kl_divergence(q_target, q_context).sum(dim=1).mean()
        return log_likelihood, kl

    def forward(self, model, sample, reduce=True):
        """Compute the loss for the given sample.
        Returns a tuple with three elements:
        1) the loss
        2) the sample size, which is used as the denominator for the gradient
        3) logging outputs to display while training
        """

        sample_size = sample["nsentences"]

        # Rare: when all tokens are masked, project all tokens.
        # We use torch.where to avoid device-to-host transfers,
        # except on CPU where torch.where is not well supported
        # (see github.com/pytorch/pytorch/issues/26247).

        src_tokens = sample['net_input']['src_tokens']
        y_target = sample["target"]

        p_y_pred, _, q_context, q_target = model(src_tokens)
        q_target = q_context if q_target is None else q_target

        ll, kl = self._compute_loss(p_y_pred, y_target, q_target, q_context)

        loss = -ll + kl
        
        logging_output = {
            "loss": loss,
            "ll": -ll,
            "kl": kl,
            "ntokens": sample["ntokens"],
            "nsentences": sample["nsentences"],
            "sample_size": sample_size
        }
        return loss, sample_size, logging_output

    @staticmethod
    def reduce_metrics(logging_outputs) -> None:
        """Aggregate logging outputs from data parallel training."""
        loss_sum = sum(log.get("loss", 0) for log in logging_outputs)
        ll_sum = sum(log.get("ll", 0) for log in logging_outputs)
        kl_sum = sum(log.get("kl", 0) for log in logging_outputs)
        sample_size = sum(log.get("sample_size", 0) for log in logging_outputs)

        metrics.log_scalar(
            "loss", loss_sum / sample_size / math.log(2), sample_size, round=3
        )
        metrics.log_scalar(
            "ll", ll_sum / sample_size / math.log(2), sample_size, round=3
        )
        metrics.log_scalar(
            "kl", kl_sum / sample_size / math.log(2), sample_size, round=3
        )
