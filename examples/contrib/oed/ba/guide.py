import torch
from torch import nn

import pyro
import pyro.distributions as dist


class Ba_lm_guide(nn.Module):

    def __init__(self, regu_shape, scale_tril_shape, w_sizes):
        super(Ba_lm_guide, self).__init__()
        self.regu = nn.Parameter(-2.*torch.ones(regu_shape))
        self.scale_tril = nn.Parameter(10.*torch.ones(scale_tril_shape))
        self.w_sizes = w_sizes
        self.softplus = nn.Softplus()

    def forward(self, y, design, target_label):

        # TODO fix this
        design = design[..., :self.w_sizes[target_label]]

        anneal = torch.diag(self.softplus(self.regu))
        xtx = torch.matmul(design.transpose(-1, -2), design) + anneal
        xtxi = tensorized_matrix_inverse(xtx)
        mu = torch.matmul(xtxi, torch.matmul(design.transpose(-1, -2), y.unsqueeze(-1))).squeeze(-1)

        scale_tril = tensorized_tril(self.scale_tril)

        return mu, scale_tril

    def guide(self, y_dict, design, observation_labels, target_labels):

        target_label = target_labels[0]
        pyro.module("ba_guide", self)

        y = y_dict["y"]
        mu, scale_tril = self.forward(y, design, target_label)

        # guide distributions for w
        w_dist = dist.MultivariateNormal(mu, scale_tril=scale_tril)
        w = pyro.sample(target_label, w_dist)


def tensorized_matrix_inverse(M):
    if M.shape[-1] == 1:
        return 1./M
    elif M.shape[-1] == 2:
        det = M[..., 0, 0]*M[..., 1, 1] - M[..., 1, 0]*M[..., 0, 1]
        inv = torch.zeros(M.shape)
        inv[..., 0, 0] = M[..., 1, 1]
        inv[..., 1, 1] = M[..., 0, 0]
        inv[..., 0, 1] = -M[..., 0, 1]
        inv[..., 1, 0] = -M[..., 1, 0]
        inv = inv/det.unsqueeze(-1).unsqueeze(-1)
        return inv
    else:
        raise NotImplemented()


def tensorized_tril(M):
    if M.shape[-1] == 1:
        return M.unsqueeze(-1)
    if M.shape[-1] == 3:
        tril = torch.zeros(M.shape[:-1] + (2, 2))
        tril[..., 0, 0] = M[..., 0]
        tril[..., 1, 0] = M[..., 1]
        tril[..., 1, 1] = M[..., 2]
        return tril
    else:
        raise NotImplemented()
