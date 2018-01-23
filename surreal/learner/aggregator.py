"""
Aggregate experience tuple into pytorch-ready tensors
"""
import numpy as np
from easydict import EasyDict
import torch
import surreal.utils as U
from surreal.utils.pytorch import GpuVariable as Variable
from surreal.env import ActionType


aggreagator_registry = {}

def _obs_concat(obs_list):
    # convert uint8 to float32, if any
    return Variable(U.to_float_tensor(np.stack(obs_list)))


def register_aggregator(target_class):
    aggreagator_registry[target_class.__name__] = target_class

def aggregatorFactory(aggregator_name):
    return aggreagator_registry[aggregator_name]

class AggregatorMeta(type):
    def __new__(meta, name, bases, class_dict):
        cls = type.__new__(meta, name, bases, class_dict)
        register_aggregator(cls)
        return cls

# https://effectivepython.com/2015/02/02/register-class-existence-with-metaclasses/
class AggregatorBase(metaclass=AggregatorMeta):
    def __init__(self, obs_spec, action_spec):
        raise NotImplementedError

    def aggregate(self, exp_list):
        raise NotImplementedError

class SSARConcat(AggregatorBase):
    def __init__(self, obs_spec, action_spec):
        U.assert_type(obs_spec, dict)
        U.assert_type(action_spec, dict)
        self.action_type = ActionType[action_spec['type']]
        self.action_spec = action_spec
        self.obs_spec = obs_spec

    def aggregate(self, exp_list):
        # TODO add support for more diverse obs_spec and action_spec
        """

        Args:
            exp_list:
        
        Returns:
            aggregated experience
        """
        
        obs0, actions, rewards, obs1, dones = [], [], [], [], []
        for exp in exp_list:  # dict
            obs0.append(np.array(exp['obs'][0], copy=False))
            actions.append(exp['action'])
            rewards.append(exp['reward'])
            obs1.append(np.array(exp['obs'][1], copy=False))
            dones.append(float(exp['done']))
        if self.action_type == ActionType.continuous:
            actions = _obs_concat(actions)
        elif self.action_type == ActionType.discrete:
            actions = Variable(torch.LongTensor(actions).unsqueeze(1))
        else:
            raise NotImplementedError('action_spec unsupported '+str(self.action_spec))
        return dict(
            obs=_obs_concat(obs0),
            obs_next=_obs_concat(obs1),
            actions=actions,
            rewards=Variable(torch.FloatTensor(rewards).unsqueeze(1)),
            dones=Variable(torch.FloatTensor(dones).unsqueeze(1)),
        )