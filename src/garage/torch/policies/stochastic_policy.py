"""Base Stochastic Policy."""
import abc

import numpy as np
import torch

from garage.torch import as_torch, PolicyInput, PolicyMode
from garage.torch.policies.policy import Policy


class StochasticPolicy(Policy, abc.ABC):
    """Abstract base class for torch stochastic policies."""

    def get_action(self, observation):
        r"""Get a single action given an observation.

        Args:
            observation (np.ndarray): Observation from the environment.
                Shape is :math:`env_spec.observation_space`.

        Returns:
            tuple:
                * np.ndarray: Predicted action. Shape is
                    :math:`env_spec.action_space`.
                * dict:
                    * np.ndarray[float]: Mean of the distribution
                    * np.ndarray[float]: Standard deviation of logarithmic
                        values of the distribution.
        """
        if not isinstance(observation, np.ndarray) and not isinstance(
                observation, torch.Tensor):
            observation = self._env_spec.observation_space.flatten(observation)
        elif isinstance(observation,
                        np.ndarray) and len(observation.shape) > 1:
            observation = self._env_spec.observation_space.flatten(observation)
        elif isinstance(observation,
                        torch.Tensor) and len(observation.shape) > 1:
            observation = torch.flatten(observation)
        with torch.no_grad():
            if not isinstance(observation, torch.Tensor):
                observation = as_torch(observation)
            observation = observation.unsqueeze(0)
            action, agent_infos = self.get_actions(observation)
            return action[0], {k: v[0] for k, v in agent_infos.items()}

    def get_actions(self, observations):
        r"""Get actions given observations.

        Args:
            observations (np.ndarray): Observations from the environment.
                Shape is :math:`batch_dim \bullet env_spec.observation_space`.

        Returns:
            tuple:
                * np.ndarray: Predicted actions.
                    :math:`batch_dim \bullet env_spec.action_space`.
                * dict:
                    * np.ndarray[float]: Mean of the distribution.
                    * np.ndarray[float]: Standard deviation of logarithmic
                        values of the distribution.
        """
        if not isinstance(observations[0], np.ndarray) and not isinstance(
                observations[0], torch.Tensor):
            observations = self._env_spec.observation_space.flatten_n(
                observations)

        # frequently users like to pass lists of torch tensors or lists of
        # numpy arrays. This handles those conversions.
        if isinstance(observations, list):
            if isinstance(observations[0], np.ndarray):
                observations = np.stack(observations)
            elif isinstance(observations[0], torch.Tensor):
                observations = torch.stack(observations)

        if isinstance(observations[0],
                      np.ndarray) and len(observations[0].shape) > 1:
            observations = self._env_spec.observation_space.flatten_n(
                observations)
        elif isinstance(observations[0],
                        torch.Tensor) and len(observations[0].shape) > 1:
            observations = torch.flatten(observations, start_dim=1)
        with torch.no_grad():
            if not isinstance(observations, torch.Tensor):
                observations = as_torch(observations)
            policy_input = PolicyInput(PolicyMode.ROLLOUT, observations)
            dist, info = self.forward(policy_input)
            return dist.sample().cpu().numpy(), {
                k: v.detach().cpu().numpy()
                for (k, v) in info.items()
            }

    # pylint: disable=arguments-differ
    @abc.abstractmethod
    def forward(self, policy_input):
        """Compute the action distributions from the observations.

        Args:
            policy_input (PolicyInput): Datatype containing observations.

        Returns:
            torch.distributions.Distribution: Batch distribution of actions.
            dict[str, torch.Tensor]: Additional agent_info, as torch Tensors.
                Do not need to be detached, and can be on any device.
        """
