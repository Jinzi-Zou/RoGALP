# -*- coding: utf-8 -*-
# Adapted from https://github.com/zhitao-wang/PLNLP

import torch
from torch import nn
def calculate_loss(pos_out, neg_out, num_neg, margin=None, loss_func_name='CE'):
    if loss_func_name == 'CE':
        loss = ce_loss(pos_out, neg_out)
    elif loss_func_name == 'AUC+CE':
        loss = ce_loss(pos_out, neg_out)+auc_loss(pos_out, neg_out, num_neg)
    elif loss_func_name == 'WeightedCE':
        loss = weighted_ce_loss(pos_out, neg_out, num_neg, margin)
    elif loss_func_name == 'InfoNCE':
        loss = info_nce_loss(pos_out, neg_out, num_neg)
    elif loss_func_name == 'LogRank':
        loss = log_rank_loss(pos_out, neg_out, num_neg)
    elif loss_func_name == 'Hinge':
        loss = hinge_loss(pos_out, neg_out, num_neg)
    elif loss_func_name == 'WeightedHinge':
        loss = weighted_hinge_loss(pos_out, neg_out, num_neg, margin)
    elif loss_func_name == 'HingeAUC':
        loss = hinge_auc_loss(pos_out, neg_out, num_neg)
    elif loss_func_name == 'AdaAUC' and margin is not None:
        loss = adaptive_auc_loss(pos_out, neg_out, num_neg, margin)
    elif loss_func_name == 'WeightedAUC' and margin is not None:
        loss = weighted_auc_loss(pos_out, neg_out, num_neg, margin)
    elif loss_func_name == 'AdaHingeAUC' and margin is not None:
        loss = adaptive_hinge_auc_loss(pos_out, neg_out, num_neg, margin)
    elif loss_func_name == 'WeightedHingeAUC' and margin is not None:
        loss = weighted_hinge_auc_loss(pos_out, neg_out, num_neg, margin)
    else:
        loss = auc_loss(pos_out, neg_out, num_neg)
    return loss

def auc_loss(pos_out, neg_out, num_neg):
    pos_out = torch.reshape(pos_out, (-1, 1))
    neg_out = torch.reshape(neg_out, (-1, num_neg))
    # return torch.square(1 - (pos_out - neg_out)).sum()/ (neg_out.size(0) * neg_out.size(1))
    return torch.square(1 - (pos_out - neg_out)).sum()

def hinge_loss(pos_out, neg_out, num_neg):
    times = 10
    loss = []
    for _ in range(times):
        perm = torch.randperm(neg_out.size(0))
        loss.append(torch.square(1 - (pos_out.view(-1, 1) - neg_out[perm].view(-1, num_neg))))
    loss = torch.stack(loss, dim=-1)
    return loss.max(-1)[0].sum()

def weighted_hinge_loss(pos_out, neg_out, num_neg, weight):
    times = 10
    loss = []
    for _ in range(times):
        perm = torch.randperm(neg_out.size(0))
        loss.append(weight.view(-1, 1) * torch.square(1 - (pos_out.view(-1, 1) - neg_out[perm].view(-1, num_neg))))
    loss = torch.stack(loss, dim=-1)
    return loss.max(-1)[0].mean()


def hinge_auc_loss(pos_out, neg_out, num_neg):
    pos_out = torch.reshape(pos_out, (-1, 1))
    neg_out = torch.reshape(neg_out, (-1, num_neg))
    return (torch.square(torch.clamp(1 - (pos_out - neg_out), min=0))).sum()


def weighted_auc_loss(pos_out, neg_out, num_neg, weight):
    weight = torch.reshape(weight, (-1, 1))
    pos_out = torch.reshape(pos_out, (-1, 1))
    neg_out = torch.reshape(neg_out, (-1, num_neg))
    return (weight*torch.square(1 - (pos_out - neg_out))).sum()


def adaptive_auc_loss(pos_out, neg_out, num_neg, margin):
    margin = torch.reshape(margin, (-1, 1))
    pos_out = torch.reshape(pos_out, (-1, 1))
    neg_out = torch.reshape(neg_out, (-1, num_neg))
    return (torch.square(margin - (pos_out - neg_out))).sum()


def weighted_hinge_auc_loss(pos_out, neg_out, num_neg, weight):
    weight = torch.reshape(weight, (-1, 1))
    pos_out = torch.reshape(pos_out, (-1, 1))
    neg_out = torch.reshape(neg_out, (-1, num_neg))
    return (weight*torch.square(torch.clamp(weight - (pos_out - neg_out), min=0))).sum()


def adaptive_hinge_auc_loss(pos_out, neg_out, num_neg, weight):
    weight = torch.reshape(weight, (-1, 1))
    pos_out = torch.reshape(pos_out, (-1, 1))
    neg_out = torch.reshape(neg_out, (-1, num_neg))
    return (torch.square(torch.clamp(weight - (pos_out - neg_out), min=0))).sum()


def log_rank_loss(pos_out, neg_out, num_neg):
    pos_out = torch.reshape(pos_out, (-1, 1))
    neg_out = torch.reshape(neg_out, (-1, num_neg))
    return -torch.log(torch.sigmoid(pos_out - neg_out) + 1e-15).mean()


def ce_loss(pos_out, neg_out):
    pos_loss = -torch.log(torch.sigmoid(pos_out) + 1e-15).mean()
    neg_loss = -torch.log(1 - torch.sigmoid(neg_out) + 1e-15).mean()
    return pos_loss + neg_loss

def weighted_ce_loss(pos_out, neg_out, num_neg, weight):
    weight = torch.reshape(weight, (-1, 1))
    pos_out = torch.reshape(pos_out, (-1, 1))
    neg_out = torch.reshape(neg_out, (-1, num_neg))
    pos_loss = -torch.log(torch.sigmoid(pos_out) + 1e-15)
    neg_loss = -torch.log(1 - torch.sigmoid(neg_out) + 1e-15)
    return (weight * (pos_loss + neg_loss)).mean().mean(-1)

def info_nce_loss(pos_out, neg_out, num_neg):
    pos_out = torch.reshape(pos_out, (-1, 1))
    neg_out = torch.reshape(neg_out, (-1, num_neg))
    pos_exp = torch.exp(pos_out)
    neg_exp = torch.sum(torch.exp(neg_out), 1, keepdim=True)
    return -torch.log(pos_exp / (pos_exp + neg_exp) + 1e-15).mean()


class GCELoss(nn.Module):

    def __init__(self, q=0.9):
        super(GCELoss, self).__init__()
        self.q = q
        # self.ignore_index = ignore_index

    def forward(self, pos_out, neg_out,num_neg):
        # vanilla cross entropy when q = 0
        if self.q == 0:
            raise Exception("q has to be greater than 0 ")
        else:

            pos_pred = torch.sigmoid(pos_out)
            neg_pred = 1-torch.sigmoid(neg_out)
            pred = torch.cat((pos_pred,neg_pred),0)
            pred = torch.clamp(pred, min=1e-10, max=1 - 1e-10)

            pos_out = torch.reshape(pos_out, (-1, 1))
            neg_out = torch.reshape(neg_out, (-1, num_neg))
            # pos_out = torch.sigmoid(pos_out)
            # neg_out = torch.sigmoid(neg_out)
            auc_loss = torch.square(1 - (pos_out - neg_out)).sum()
            # auc_loss = auc_loss / pos_out.size(0)
            auc_loss = auc_loss / (neg_out.size(0) * neg_out.size(1))

            ro_loss = (1 - pred ** self.q) / self.q
            # ro_loss = - torch.log(pred)


        ro_loss = ro_loss.sum() / ro_loss.size(0)
        # loss = ro_loss+auc_loss
        # loss = loss.sum() / loss.size(0)
        # loss = loss.sum() + auc_loss
        # loss = loss.sum() / loss.size(0) + auc_loss
        # loss2 = (loss * weights).sum() / weights.sum()
        # loss2 = loss2.float()
        # if math.isnan(loss2):
        #     print("weight",weights)
        #     print("loss:",loss)
        # n = input()
        return ro_loss,auc_loss