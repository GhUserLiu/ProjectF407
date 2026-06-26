#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
golden_test.py — INT8 线性 SVM 导出契约自洽校验。

无 host gcc/QEMU，无法在主机跑真实 C 的 Model_Predict。本脚本转而：
解析 model_weights.c 的 const 参数（w_q/threshold/sx/sw/b/A/B），用与 model.c 相同
的 INT8 公式重算每个 golden 输入的 dot/score/is_attack/p_attack，与 golden_pairs.json
比对。一致即说明导出格式与推理公式自洽；C 侧按同公式实现即可产生同样结果。

用法：python src/projects/can-ids/golden_test.py
"""
import json
import os
import re
import sys

import numpy as np

INPUT_DIM = 17


def parse_array_int(txt, name):
    m = re.search(name + r"\[.*?\]\s*=\s*\{(.*?)\}", txt, re.S)
    return np.array([int(x) for x in re.findall(r"-?\d+", m.group(1))], dtype=np.int32)


def parse_array_float(txt, name):
    m = re.search(name + r"\[.*?\]\s*=\s*\{(.*?)\}", txt, re.S)
    return np.array([float(x) for x in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", m.group(1))],
                    dtype=np.float64)


def parse_scalar(txt, name, cast):
    m = re.search(name + r"\s*=\s*([-+]?[\d.eE+-]+)", txt)
    return cast(m.group(1))


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    wc = os.path.join(here, "model_weights.c")
    gj = os.path.join(here, "golden_pairs.json")
    if not os.path.exists(wc) or not os.path.exists(gj):
        print("缺少 model_weights.c 或 golden_pairs.json，请先运行 train_svm.py")
        sys.exit(1)

    txt = open(wc, "r", encoding="utf-8").read()
    wq = parse_array_int(txt, "g_svm_wq")
    sx = parse_array_float(txt, "g_svm_sx")
    T = parse_scalar(txt, "g_svm_threshold", int)
    sw = parse_scalar(txt, "g_svm_sw", float)
    b = parse_scalar(txt, "g_svm_b", float)
    pA = parse_scalar(txt, "g_svm_platt_A", float)
    pB = parse_scalar(txt, "g_svm_platt_B", float)
    assert wq.size == INPUT_DIM and sx.size == INPUT_DIM, "维度不符"
    print(f"解析参数: w_q[{wq.size}] int8, threshold={T}, sw={sw:.4e}, b={b:.4e}, A={pA:.4f}, B={pB:.4f}")

    golden = json.load(open(gj, "r", encoding="utf-8"))
    tol_p, tol_margin = 1e-6, 1e-3
    worst_p, worst_m, ok = 0.0, 0.0, True
    for i, pair in enumerate(golden["pairs"]):
        x = np.array(pair["input"], dtype=np.float64)
        xq = np.clip(np.round(x / sx).astype(np.int32), -128, 127)
        dot = int((xq * wq).sum())
        is_attack = (dot >= T)
        margin = sw * dot + b
        p = float(1.0 / (1.0 + np.exp(-(pA * margin + pB))))
        dp = abs(p - pair["p_attack"]); dm = abs(margin - pair["margin"])
        worst_p = max(worst_p, dp); worst_m = max(worst_m, dm)
        flag = "OK" if (is_attack == pair["is_attack"] and dp <= tol_p and dm <= tol_margin) else "FAIL"
        if flag == "FAIL":
            ok = False
        print(f"  pair {i}: dot={dot:4d} T={T} attack={int(is_attack)} "
              f"p={p:.5f} exp_p={pair['p_attack']:.5f} [{flag}]")

    print(f"\n最大误差: p={worst_p:.2e}  margin={worst_m:.2e}")
    print("结果: " + ("PASS —— INT8 SVM 导出契约自洽" if ok else "FAIL"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
