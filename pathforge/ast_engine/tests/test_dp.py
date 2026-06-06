import ast
import pytest
from pathforge.ast_engine.sanitizer import sanitize_code
from pathforge.ast_engine.extractor import extract_features
from pathforge.ast_engine.classifier import classify_pattern
from pathforge.ast_engine.patterns import DP_1D_FORWARD, DP_1D_SEQUENCE, DP_2D_GRID, DP_INTERVAL, DP_KNAPSACK, DP_STATE_MACHINE

def run_classifier(code_string):
    is_safe, errors, root = sanitize_code(code_string)
    assert is_safe, f"Sanitization failed: {errors}"
    features = extract_features(root)
    scores = classify_pattern(features)
    return scores

def test_clean_dp_1d():
    code = """
def climbStairs(n: int) -> int:
    if n <= 2:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    dp[2] = 2
    for i in range(3, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]
"""
    scores = run_classifier(code)
    # DP array (0.4) + index lookback (0.3) + loop (0.2) + no recursion (0.1) = 1.0
    assert scores[DP_1D_FORWARD] >= 0.9

def test_messy_dp_1d():
    code = """
class MessyDPSolution:
    def get_climbing_ways(self, total_stairs_count):
        print("Climbing steps calculation started for:", total_stairs_count)
        if total_stairs_count <= 2:
            return total_stairs_count
            
        # Messy array definition and auxiliary variables
        states_memo_array = [0] * (total_stairs_count + 1)
        states_memo_array[1] = 1
        states_memo_array[2] = 2
        
        loop_ptr_index = 3
        while loop_ptr_index <= total_stairs_count:
            # Lookback with renamed variables and prints
            step_prev_1 = states_memo_array[loop_ptr_index - 1]
            step_prev_2 = states_memo_array[loop_ptr_index - 2]
            summed_value = step_prev_1 + step_prev_2
            print("Processing index:", loop_ptr_index, "value:", summed_value)
            states_memo_array[loop_ptr_index] = summed_value
            loop_ptr_index += 1
            
        final_computed_ans = states_memo_array[total_stairs_count]
        print("Done. Answer:", final_computed_ans)
        return final_computed_ans
"""
    scores = run_classifier(code)
    # DP array (0.4) + index lookback (0.3) + loop (0.2) + no recursion (0.1) = 1.0
    assert scores[DP_1D_FORWARD] >= 0.9


@pytest.mark.parametrize("pattern,code", [
    (DP_2D_GRID, "def f(grid):\n dp=[[0]*len(grid[0]) for _ in grid]\n for r in range(1,len(grid)):\n  for c in range(1,len(grid[0])): dp[r][c]=dp[r-1][c]+dp[r][c-1]\n return dp[-1][-1]\n"),
    (DP_2D_GRID, "def f(g):\n table=[[0]*len(g[0]) for _ in g]\n for i in range(1,len(g)):\n  for j in range(1,len(g[0])): table[i][j]=table[i-1][j]+table[i][j-1]\n return table\n"),
    (DP_KNAPSACK, "def f(w,cap):\n dp=[[0]*(cap+1) for _ in w]\n for i in range(len(w)):\n  for c in range(cap+1):\n   if c>=w[i]: dp[i][c]=max(dp[i-1][c], dp[i-1][c-w[i]]+1)\n return dp[-1][cap]\n"),
    (DP_KNAPSACK, "def f(weight, capacity):\n memo=[[0]*(capacity+1) for _ in weight]\n for i in range(len(weight)):\n  for cap in range(capacity+1):\n   if cap>=weight[i]: memo[i][cap]=max(memo[i][cap],1)\n return memo\n"),
    (DP_1D_SEQUENCE, "def f(nums):\n dp=[1]*len(nums)\n for i in range(len(nums)):\n  for j in range(i): dp[i]=max(dp[i],dp[j]+1)\n return max(dp)\n"),
    (DP_1D_SEQUENCE, "def f(a):\n best=[1]*len(a)\n for x in range(len(a)):\n  for y in range(x): best[x]=max(best[x], best[y]+1)\n return best\n"),
    (DP_INTERVAL, "def f(nums):\n dp=[[0]*len(nums) for _ in nums]\n for l in range(len(nums)):\n  for r in range(l,len(nums)): dp[l][r]=max(dp[l][r], nums[r])\n return dp[0][-1]\n"),
    (DP_INTERVAL, "def f(a):\n table=[[0]*len(a) for _ in a]\n for start in range(len(a)):\n  for end in range(start,len(a)): table[start][end]=max(table[start][end], a[end])\n return table\n"),
    (DP_STATE_MACHINE, "def f(prices):\n dp=[0]*len(prices)\n hold=-prices[0]\n for p in prices:\n  if p>0: dp[0]=max(dp[0], hold+p)\n return dp[0]\n"),
    (DP_STATE_MACHINE, "def f(vals):\n state=[0]*3\n for v in vals:\n  if v: state[1]=max(state[1], state[0]+v)\n return state[1]\n"),
])
def test_expanded_dp_patterns(pattern, code):
    assert run_classifier(code)[pattern] >= 0.55
