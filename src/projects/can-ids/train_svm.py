#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
train_svm.py — 训练 INT8 线性 SVM 并导出为 C const 数组（CAN 入侵检测，STM32F407）。

模型：线性 SVM，二分类（0=正常, 1=攻击）。
  决策 f(x) = w·x + b；攻击 ⟺ f(x) >= 0。

INT8 量化（全整型核心推理）：
  - 每维输入有独立 scale s_x[i] = max(|x_train[:,i]|)/127，x_q[i]=round(x[i]/s_x[i]) clamp[-128,127]
  - 把输入 scale 折进权重：w_eff[i] = w[i]*s_x[i]；单一权重 scale s_w = max(|w_eff|)/127
    w_q[i] = round(w_eff[i]/s_w) clamp int8
  - 则 w·x ≈ s_w * Σ w_q[i]*x_q[i] = s_w * dot_q；f = s_w*dot_q + b
  - 整数阈值 T = round(-b/s_w)；攻击 ⟺ dot_q >= T   ← 核心分类全整型
  - 边缘：输入量化(17 次 / ) 与 Platt 概率(1 次 expf) 为浮点（校准元数据）

输出（const，链入 FLASH，0 字节 RAM）：
  model_weights.c/.h : g_svm_wq[17](int8) g_svm_threshold(int32) g_svm_sx[17](float)
                       g_svm_sw g_svm_b g_svm_platt_A g_svm_platt_B (float)
  golden_pairs.json  : 8 组 (输入, is_attack, margin, p_attack)

用法：python src/projects/can-ids/train_svm.py
"""
import json
import os

import numpy as np
from sklearn.svm import LinearSVC
from sklearn.linear_model import LogisticRegression

INPUT_DIM = 17
SEED = 42


def generate_data(n=4000, seed=SEED):
    """与 train_model.py 一致的合成 CAN 特征：正常 vs 攻击窗口。"""
    rng = np.random.default_rng(seed)
    half = n // 2
    normal = np.stack([
        rng.normal(400, 40, half), rng.normal(60, 10, half), rng.normal(1.4, 0.15, half),
        rng.normal(6, 1.5, half), rng.normal(7.0, 0.4, half), rng.normal(1.0, 0.2, half),
        rng.normal(120, 15, half), rng.normal(60, 6, half), rng.normal(3.5, 0.2, half),
        rng.normal(5000, 400, half), rng.normal(500, 80, half), rng.normal(200, 20, half),
        rng.normal(0.30, 0.05, half), rng.normal(0.20, 0.04, half), rng.normal(0.15, 0.03, half),
        rng.normal(0.10, 0.03, half), rng.normal(0.08, 0.02, half),
    ], axis=1)
    attack = np.stack([
        rng.normal(700, 120, half), rng.normal(260, 40, half), rng.normal(3.6, 0.25, half),
        rng.normal(45, 10, half), rng.normal(7.0, 0.6, half), rng.normal(1.5, 0.3, half),
        rng.normal(128, 30, half), rng.normal(74, 10, half), rng.normal(5.2, 0.25, half),
        rng.normal(900, 250, half), rng.normal(2600, 500, half), rng.normal(1200, 300, half),
        rng.normal(0.12, 0.04, half), rng.normal(0.10, 0.03, half), rng.normal(0.09, 0.03, half),
        rng.normal(0.08, 0.02, half), rng.normal(0.07, 0.02, half),
    ], axis=1)
    X = np.vstack([normal, attack]).astype(np.float64)
    y = np.concatenate([np.zeros(half), np.ones(half)]).astype(np.int64)
    perm = rng.permutation(len(X))
    return X[perm], y[perm]


def quantize_int8(value):
    """clamp 到 int8 范围。"""
    v = int(np.round(value))
    return 128 if v > 127 else (-128 if v < -128 else v)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    X, y = generate_data()
    split = int(0.85 * len(X))
    Xtr, ytr = X[:split], y[:split]
    Xva, yva = X[split:], y[split:]

    print("=" * 60)
    print("INT8 线性 SVM 训练（sklearn）")
    print("=" * 60)

    # 1. 训练 float 线性 SVM
    svm = LinearSVC(C=1.0, max_iter=10000, random_state=SEED)
    svm.fit(Xtr, ytr)
    w = svm.coef_[0].copy()            # (17,)
    b = float(svm.intercept_[0])
    # 保证 attack(1) 对应 f>=0：若训练集上 attack 的均值 f<normal，翻转符号
    f_tr = Xtr @ w + b
    if f_tr[ytr == 1].mean() < f_tr[ytr == 0].mean():
        w, b = -w, -b
        svm.coef_[0], svm.intercept_ = w, b

    float_acc = (((Xva @ w + b) >= 0).astype(int) == yva).mean()
    print(f"float SVM val_acc = {float_acc:.4f}")

    # 2. 每维输入 scale（对称量化）
    sx = (np.abs(Xtr).max(axis=0) / 127.0)           # (17,)
    sx = np.where(sx > 1e-12, sx, 1.0)

    # 3. 折入权重：w_eff = w*sx，单一权重 scale
    w_eff = w * sx
    sw = float(np.abs(w_eff).max() / 127.0)
    if sw < 1e-12:
        sw = 1e-12
    wq = np.array([quantize_int8(v / sw) for v in w_eff], dtype=np.int32)

    # 4. 整数阈值 T = round(-b/sw)
    T = int(np.round(-b / sw))

    # 5. int8 推理精度校验
    def int8_predict(X):
        Xq = np.clip(np.round(X / sx).astype(np.int32), -128, 127)
        dot = (Xq * wq[None, :]).sum(axis=1)
        return (dot >= T).astype(int), dot
    int_pred, int_dot = int8_predict(Xva)
    int_acc = (int_pred == yva).mean()
    print(f"int8  SVM val_acc = {int_acc:.4f}  (量化损失 {float_acc-int_acc:+.4f})")

    # 6. Platt 概率（在 float margin 上拟合 logistic）
    margin_tr = Xtr @ w + b
    lr = LogisticRegression(max_iter=10000)
    lr.fit(margin_tr.reshape(-1, 1), ytr)
    platt_A = float(lr.coef_[0, 0])
    platt_B = float(lr.intercept_[0])
    # int8 margin（用 dequant 还原）≈ float margin
    margin_int = sw * int_dot + b
    p_attack = 1.0 / (1.0 + np.exp(-(platt_A * margin_int + platt_B)))
    print(f"Platt A={platt_A:.4f} B={platt_B:.4f}")

    # 7. 导出 model_weights.c/.h（const，FLASH）
    export_c(here, wq, T, sx, sw, b, platt_A, platt_B)
    export_golden(here, Xva, yva, sx, wq, T, sw, b, platt_A, platt_B)

    print(f"\n模型 int8 参数 = {INPUT_DIM} 字节 (w_q)  + 阈值4B + 校准元数据(sx/sw/b/A/B)")
    print("完成。运行 golden_test.py 做导出自洽校验。")


def export_c(here, wq, T, sx, sw, b, platt_A, platt_B):
    wq_str = ", ".join(str(int(v)) for v in wq)
    sx_str = ", ".join(f"{v:.8e}f" for v in sx)
    c = (
        "/**\n * @file model_weights.c\n"
        " * @brief INT8 线性 SVM 参数（train_svm.py 导出，const 链入 FLASH）\n"
        f" * w_q: {INPUT_DIM} int8  | threshold: int32  | sx/sw/b/A/B: 校准元数据(float)\n"
        " */\n"
        '#include "model.h"\n\n'
        f"const int8_t  g_svm_wq[MODEL_INPUT_DIM] = {{ {wq_str} }};\n"
        f"const int32_t g_svm_threshold = {int(T)};\n"
        f"const float   g_svm_sx[MODEL_INPUT_DIM] = {{ {sx_str} }};\n"
        f"const float   g_svm_sw = {sw:.8e}f;\n"
        f"const float   g_svm_b  = {b:.8e}f;\n"
        f"const float   g_svm_platt_A = {platt_A:.8e}f;\n"
        f"const float   g_svm_platt_B = {platt_B:.8e}f;\n\n"
        "/* 权重已作为 const 链入 FLASH；此函数保留 API 连续性，恒返回 true */\n"
        "bool Model_LoadPretrainedWeights(void) { return true; }\n"
    )
    with open(os.path.join(here, "model_weights.c"), "w", encoding="utf-8") as f:
        f.write(c)
    h = (
        "/**\n * @file model_weights.h\n * @brief INT8 线性 SVM 参数声明\n */\n"
        "#ifndef MODEL_WEIGHTS_H\n#define MODEL_WEIGHTS_H\n"
        '#include "model.h"\n#include <stdbool.h>\n\n'
        "extern const int8_t  g_svm_wq[MODEL_INPUT_DIM];\n"
        "extern const int32_t g_svm_threshold;\n"
        "extern const float   g_svm_sx[MODEL_INPUT_DIM];\n"
        "extern const float   g_svm_sw;\n"
        "extern const float   g_svm_b;\n"
        "extern const float   g_svm_platt_A;\n"
        "extern const float   g_svm_platt_B;\n\n"
        "bool Model_LoadPretrainedWeights(void);\n\n"
        "#endif /* MODEL_WEIGHTS_H */\n"
    )
    with open(os.path.join(here, "model_weights.h"), "w", encoding="utf-8") as f:
        f.write(h)
    print(f"导出 model_weights.c/.h  (w_q {INPUT_DIM}B int8 + 元数据)")


def export_golden(here, Xva, yva, sx, wq, T, sw, b, platt_A, platt_B, n=8):
    rng = np.random.default_rng(7)
    idx = rng.choice(len(Xva), size=min(n, len(Xva)), replace=False)
    pairs = []
    for i in idx:
        x = Xva[i]
        xq = np.clip(np.round(x / sx).astype(np.int32), -128, 127)
        dot = int((xq * wq).sum())
        is_attack = bool(dot >= T)
        margin = sw * dot + b
        p = float(1.0 / (1.0 + np.exp(-(platt_A * margin + platt_B))))
        pairs.append({"input": x.tolist(), "is_attack": is_attack,
                      "margin": margin, "p_attack": p, "y": int(yva[i])})
    with open(os.path.join(here, "golden_pairs.json"), "w", encoding="utf-8") as f:
        json.dump({"pairs": pairs}, f, indent=2)
    print(f"导出 golden_pairs.json ({len(pairs)} 组)")


if __name__ == "__main__":
    main()
