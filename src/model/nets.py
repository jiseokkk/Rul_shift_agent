"""원본 Transformer_pre_model.py + Transformer_ft_serialatten_model.py 의 모델 정의 통합.

모듈 이름(linear, pos_embedding, encoder.{i}.attn/attn2/norm1/fc1/fc2/norm2, out, classout)을
원본과 동일하게 유지하므로 원본 pre_FD0013.pt (encoder state_dict) 를 그대로 로드할 수 있다.

원본과 다른 점: EncoderLayer 의 attn2 embed_dim 이 45 로 하드코딩되어 있던 것을 seq_len 인자로 받음
(기본 45, heads 5 → 원본과 동일). query/key/value Linear 는 원본에서도 forward 에 쓰이지 않지만
state_dict 호환을 위해 남겨둔다.
"""
from __future__ import annotations

import torch
import torch.nn as nn


class EncoderLayer(nn.Module):
    def __init__(self, num_hidden, ffn_hidden, heads=1, dropout=0.5, seq_len=45, seq_heads=5):
        super().__init__()
        self.query = nn.Linear(num_hidden, num_hidden)
        self.key = nn.Linear(num_hidden, num_hidden)
        self.value = nn.Linear(num_hidden, num_hidden)
        # 시퀀스(시간축) attention: (seq, batch, hidden)
        self.attn = nn.MultiheadAttention(embed_dim=num_hidden, num_heads=heads, dropout=dropout)
        # feature attention: (hidden, batch, seq) — seq_len 이 embed_dim
        self.attn2 = nn.MultiheadAttention(embed_dim=seq_len, num_heads=seq_heads, dropout=dropout)
        self.norm1 = nn.LayerNorm(num_hidden)
        self.fc1 = nn.Linear(num_hidden, ffn_hidden)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(ffn_hidden, num_hidden)
        self.dropout = nn.Dropout(dropout)
        self.norm2 = nn.LayerNorm(num_hidden)

    def forward(self, X):
        X = X.permute(1, 0, 2)
        Y, _ = self.attn(X, X, X)
        X = X.permute(1, 0, 2)
        Y = Y.permute(1, 0, 2)

        Y = Y.permute(2, 0, 1)
        Y, _ = self.attn2(Y, Y, Y)
        Y = Y.permute(1, 2, 0)

        X = self.norm1(X + self.dropout(Y))
        Y = self.fc2(self.relu(self.fc1(X)))
        X = self.norm2(X + self.dropout(Y))
        return X


class MLP(nn.Module):
    def __init__(self, num_inputs, num_hiddens):
        super().__init__()
        self.mlp = nn.Sequential(nn.Linear(num_inputs, num_hiddens), nn.ReLU(),
                                 nn.LayerNorm(num_hiddens), nn.Linear(num_hiddens, 1))

    def forward(self, X):
        return self.mlp(X)


class CLASSMLP(nn.Module):
    def __init__(self, num_inputs, num_hiddens):
        super().__init__()
        self.mlp = nn.Sequential(nn.Linear(num_inputs, num_hiddens), nn.ReLU(),
                                 nn.LayerNorm(num_hiddens), nn.Linear(num_hiddens, 2),
                                 nn.ReLU(), nn.Softmax(-1))

    def forward(self, X):
        return self.mlp(X)


class GradReverse(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, constant):
        ctx.constant = constant
        return x.view_as(x)

    @staticmethod
    def backward(ctx, grad_output):
        return grad_output.neg() * ctx.constant, None


def _build_encoder(num_hidden, ffn_hidden, encoder_layers, heads, dropout, seq_len):
    enc = nn.Sequential()
    for i in range(encoder_layers):
        enc.add_module(f"{i}", EncoderLayer(num_hidden, ffn_hidden, heads, dropout, seq_len=seq_len))
    return enc


class Transformer_pre(nn.Module):
    """사전학습: RUL 회귀 + (grad reverse) 도메인 분류."""

    def __init__(self, input_size, num_hidden, seq_len, ffn_hidden, mlp_size, encoder_layers=1, heads=1, dropout=0.5):
        super().__init__()
        self.linear = nn.Linear(input_size, num_hidden)
        self.pos_embedding = nn.Parameter(torch.randn(1, seq_len, num_hidden))
        self.encoder = _build_encoder(num_hidden, ffn_hidden, encoder_layers, heads, dropout, seq_len)
        self.out = MLP(num_hidden, mlp_size)
        self.classout = CLASSMLP(num_hidden, mlp_size)

    def forward(self, X):
        X = self.linear(X) + self.pos_embedding
        for enc_layer in self.encoder:
            X = enc_layer(X)
        Y = self.out(X[:, -1, :])
        X = GradReverse.apply(X, 1)
        CLASSY = self.classout(X[:, -1, :])
        return Y, CLASSY


class Transformer_ft(nn.Module):
    """미세조정/추론: encoder 는 사전학습 weight 로드 후 freeze, linear·pos_embedding·out 학습."""

    def __init__(self, input_size, num_hidden, seq_len, ffn_hidden, mlp_size, encoder_layers=1, heads=1, dropout=0.5):
        super().__init__()
        self.linear = nn.Linear(input_size, num_hidden)
        self.pos_embedding = nn.Parameter(torch.randn(1, seq_len, num_hidden))
        self.encoder = _build_encoder(num_hidden, ffn_hidden, encoder_layers, heads, dropout, seq_len)
        self.out = MLP(num_hidden, mlp_size)

    def forward(self, X):
        X = self.linear(X) + self.pos_embedding
        for enc_layer in self.encoder:
            X = enc_layer(X)
        return self.out(X[:, -1, :])


def build_pre(cfg: dict) -> Transformer_pre:
    return Transformer_pre(cfg["input_size"], cfg["num_hidden"], cfg["seq_len"], cfg["ffn_hidden"],
                           cfg["mlp_size"], cfg["encoder_layers"], cfg["n_heads"], cfg["dropout"])


def build_ft(cfg: dict) -> Transformer_ft:
    return Transformer_ft(cfg["input_size"], cfg["num_hidden"], cfg["seq_len"], cfg["ffn_hidden"],
                          cfg["mlp_size"], cfg["encoder_layers"], cfg["n_heads"], cfg["dropout"])


def my_score(target, pred) -> float:
    """원본 utils.myScore (PHM08 scoring)."""
    import math

    target = [float(v) for v in target]
    pred = [float(v) for v in pred]
    tmp1 = tmp2 = 0.0
    for t, p in zip(target, pred):
        if t > p:
            tmp1 += math.exp((-p + t) / 13.0) - 1
        else:
            tmp2 += math.exp((p - t) / 10.0) - 1
    return tmp1 + tmp2
