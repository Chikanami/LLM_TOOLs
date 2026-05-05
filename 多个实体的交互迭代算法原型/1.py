# ============================================================
# f() —— 返回实体A的定义
# ============================================================
def f():
    W = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8, 9, 7, 9]
    return W
# ============================================================
# kappa() —— 返回实体B的定义
# ============================================================
def kappa():
    O = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j',
         'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
         'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3',
         '4', '5', '6', '7', '8', '9', '!', '?', ' ', ',']
    return O
# ============================================================
# h() —— 封装完整的交互过程
#       输入：两个实体 + 规则 P
#       输出：整个交互轨迹
# ============================================================
def h(entity_A, entity_B, P):
    traces = []
    for rnd in range(1, P["iterations"] + 1):
        # ---- 单步交互：A 的每个值映射到 B 的某个位置 ----
        result = ""
        for value in entity_A:
            index = value % len(entity_B)
            result += entity_B[index]
        traces.append((rnd, result))
        # ---- 迭代：按 P 中定义的规则改变实体 ----
        entity_A = P["mutate_A"](entity_A, rnd)
        entity_B = P["mutate_B"](entity_B, rnd)
    return traces
# ============================================================
# P —— 迭代规则（一个包裹，里面塞什么都可以）
# ============================================================
def pm_P():
    P = {
		"iterations": 5,
		"mutate_A": lambda entity_A, round_num: (
			[v + round_num for v in entity_A]
		),
		"mutate_B": lambda entity_B, round_num: (
			entity_B[round_num % len(entity_B):] +
			entity_B[:round_num % len(entity_B)]
		),
	}
	return P

def g():
    W = f()
    O = kappa()
    P = pm_P()
    return h(W, O, P)
if __name__ == "__main__":
    traces = g()
    for rnd, output in traces:
        print(f"轮次 {rnd}: {output}")
