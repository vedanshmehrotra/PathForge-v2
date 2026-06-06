import ast
import pytest
from pathforge.ast_engine.sanitizer import sanitize_code
from pathforge.ast_engine.extractor import extract_features
from pathforge.ast_engine.classifier import classify_pattern
from pathforge.ast_engine.patterns import (
    BACKTRACKING_PERMUTATION, BACKTRACKING_SUBSET, BINARY_SEARCH_ANSWER,
    BINARY_SEARCH_STANDARD, DP_1D_FORWARD, FAST_SLOW_POINTERS, GREEDY_INTERVAL,
    GREEDY_LOCAL, HEAP_TOP_K, LINKED_LIST_REVERSAL, MONOTONIC_STACK, UNION_FIND,
)

def run_classifier(code_string):
    is_safe, errors, root = sanitize_code(code_string)
    assert is_safe, f"Sanitization failed: {errors}"
    features = extract_features(root)
    scores = classify_pattern(features)
    return scores

def test_clean_greedy_local():
    code = """
def maxSubArray(nums):
    max_so_far = nums[0]
    curr_max = nums[0]
    for i in range(1, len(nums)):
        curr_max = max(nums[i], curr_max + nums[i])
        max_so_far = max(max_so_far, curr_max)
    return max_so_far
"""
    scores = run_classifier(code)
    # loop (0.4) + max/min call (0.3) + no DP array/lookback (0.2) + no recursion (0.1) = 1.0
    assert scores[GREEDY_LOCAL] >= 0.9
    # DP array should be 0 because it's greedy (no dp table allocated or lookback index offset)
    assert scores[DP_1D_FORWARD] < 0.5

def test_messy_greedy_jump_game():
    code = """
class MessyGreedySolution:
    def canReachDestination(self, jump_limits_list):
        print("Starting messy greedy check...")
        furthest_reachable_index = 0
        list_length = len(jump_limits_list)
        
        # Verbose, messy loop using while and print statements
        curr_idx = 0
        while curr_idx < list_length:
            if curr_idx > furthest_reachable_index:
                print("Cannot move past index:", curr_idx)
                return False
                
            local_leap_reach = curr_idx + jump_limits_list[curr_idx]
            # Call to max() representing a greedy choice
            furthest_reachable_index = max(furthest_reachable_index, local_leap_reach)
            print("Current reachable index updated to:", furthest_reachable_index)
            curr_idx += 1
            
        print("Successfully reached the end!")
        return True
"""
    scores = run_classifier(code)
    # loop (0.4) + max/min call (0.3) + no DP array/lookback (0.2) + no recursion (0.1) = 1.0
    assert scores[GREEDY_LOCAL] >= 0.9
    assert scores[DP_1D_FORWARD] < 0.5


@pytest.mark.parametrize("pattern,code", [
    (HEAP_TOP_K, "from heapq import heappush, heappop\ndef f(nums,k):\n h=[]\n for x in nums:\n  heappush(h,x)\n  if len(h)>k: heappop(h)\n return h\n"),
    (HEAP_TOP_K, "from heapq import heapify, heapreplace\ndef f(a):\n heapify(a)\n for x in a: heapreplace(a,x)\n return a\n"),
    (GREEDY_INTERVAL, "def f(intervals):\n intervals.sort(key=lambda x:x[1])\n end=0\n for start,finish in intervals:\n  if start>=end: end=finish\n return end\n"),
    (GREEDY_INTERVAL, "def f(items):\n ordered=sorted(items,key=lambda item:item[0])\n for start,end in ordered: best=end\n return best\n"),
    (UNION_FIND, "def f(edges):\n parent={}; rank={}\n def find(x): return parent.get(x,x)\n def union(a,b): parent[find(a)]=find(b)\n for a,b in edges: union(a,b)\n return parent\n"),
    (UNION_FIND, "def f(pairs):\n parent=[]; rank=[]\n def find_parent(x): return x\n def union_find(a,b): return find_parent(a)\n for a,b in pairs: union_find(a,b)\n return rank\n"),
    (BACKTRACKING_PERMUTATION, "def f(nums):\n ans=[]\n def dfs(path):\n  if len(path)==len(nums): ans.append(path[:]); return\n  for x in nums:\n   if x not in path: dfs(path+[x])\n dfs([]); return ans\n"),
    (BACKTRACKING_PERMUTATION, "def f(a):\n out=[]\n def go(path):\n  for x in a:\n   if x not in path: go(path.copy()+[x])\n go([]); return out\n"),
    (BACKTRACKING_SUBSET, "def f(nums):\n ans=[]\n def dfs(i,path):\n  if i==len(nums): ans.append(path[:]); return\n  dfs(i+1,path); dfs(i+1,path+[nums[i]])\n dfs(0,[]); return ans\n"),
    (BACKTRACKING_SUBSET, "def f(a):\n res=[]\n def walk(i,cur):\n  if i>=len(a): res.append(cur.copy()); return\n  walk(i+1,cur); walk(i+1,cur+[a[i]])\n walk(0,[]); return res\n"),
    (BINARY_SEARCH_STANDARD, "def f(nums,t):\n l=0; r=len(nums)-1\n while l<=r:\n  mid=(l+r)//2\n  if nums[mid]==t: return mid\n  if nums[mid]<t: l=mid+1\n  else: r=mid-1\n return -1\n"),
    (BINARY_SEARCH_STANDARD, "def f(a,x):\n left=0; right=len(a)-1\n while left<=right:\n  mid=(left+right)//2\n  if a[mid]<x: left=mid+1\n  else: right=mid-1\n return left\n"),
    (BINARY_SEARCH_ANSWER, "def f(n):\n def ok(x): return x*x>=n\n lo=0; hi=n; ans=n\n while lo<=hi:\n  mid=(lo+hi)//2\n  if ok(mid): ans=mid; hi=mid-1\n  else: lo=mid+1\n return ans\n"),
    (BINARY_SEARCH_ANSWER, "def f(limit):\n def good(v): return v>3\n left=0; right=limit; answer=0\n while left<=right:\n  mid=(left+right)//2\n  if good(mid): answer=mid; right=mid-1\n  else: left=mid+1\n return answer\n"),
    (LINKED_LIST_REVERSAL, "def f(head):\n prev=None; cur=head\n while cur:\n  nxt=cur.next; cur.next=prev; prev=cur; cur=nxt\n return prev\n"),
    (LINKED_LIST_REVERSAL, "def f(node):\n before=None\n while node:\n  after=node.next; node.next=before; before=node; node=after\n return before\n"),
    (FAST_SLOW_POINTERS, "def f(head):\n slow=head; fast=head\n while fast and fast.next:\n  slow=slow.next; fast=fast.next.next\n  if slow==fast: return True\n return False\n"),
    (FAST_SLOW_POINTERS, "def f(start):\n slow=start; fast=start\n while fast and fast.next:\n  slow=slow.next; fast=fast.next.next\n return slow\n"),
    (MONOTONIC_STACK, "def f(nums):\n st=[]; ans=[]\n for x in nums:\n  while st and st[-1]<x: ans.append(st.pop())\n  st.append(x)\n return ans\n"),
    (MONOTONIC_STACK, "def f(a):\n stack=[]\n for v in a:\n  while stack and stack[-1]>v: stack.pop()\n  stack.append(v)\n return stack\n"),
])
def test_expanded_greedy_patterns(pattern, code):
    assert run_classifier(code)[pattern] >= 0.55
