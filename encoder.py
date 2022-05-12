import torch
import torch.nn as nn
import numpy as np

from typing import Union

from util import ReshapeLast

class Encoder(nn.Module):
    """ ## FROM https://github.com/EmilienDupont/neural-processes/ ##
    Maps an (x_i, y_i) pair to either a representation r_i or to parameter set s_i.
    Parameters
    ----------
    x_dim : int
        Dimension of x values.
    y_dim : int
        Dimension of y values.
    r_dim : Union[int, tuple]
        Dimension of representation r or parameter set s.
    """
    def __init__(self, x_dim: int, y_dim: int, r_dim:Union[int, tuple]):
        super(Encoder, self).__init__()

        self.x_dim = x_dim
        self.y_dim = y_dim
        self.r_dim = r_dim  if isinstance(r_dim, tuple) else (r_dim, 1)

    def forward(self, x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        """
        Input
        -----
        x : torch.Tensor
            Shape (batch_size, x_dim)
        y : torch.Tensor
            Shape (batch_size, y_dim)
        Returns
        -------
        r : torch.Tensor
            Shape (batch_size, r_dim)
        """
        raise NotImplementedError("Abstract method.")


class MLPEncoder(Encoder):
    def __init__(self, x_dim: int, y_dim: int, r_dim: Union[int, tuple], h_dim: int):
        super().__init__(x_dim, y_dim, r_dim)
        output_shape = self.r_dim
        output_size = np.prod(output_shape)
        layers = [nn.Linear(x_dim + y_dim, h_dim),
                  nn.ReLU(inplace=True),
                  nn.Linear(h_dim, h_dim),
                  nn.ReLU(inplace=True),
                  nn.Linear(h_dim, output_size),
                  ReshapeLast(output_shape)]

        self.input_to_r = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        input = torch.cat((x,y), dim=2)
        return self.input_to_r(input)

class AttentiveEncoder(Encoder):
    def __init__(self, x_dim, y_dim, r_dim):
        super().__init__(x_dim, y_dim, r_dim)
        # TODO implement attentive encoder
