import ast
import pytest
from pathforge.ast_engine.sanitizer import sanitize_code
from pathforge.ast_engine.extractor import extract_features
from pathforge.ast_engine.classifier import classify_pattern
from pathforge.ast_engine.patterns import (
    HASH_MAP_LOOKUP, HASH_MAP_FREQUENCY, PREFIX_SUM, SLIDING_WINDOW_FIXED,
    SLIDING_WINDOW_VARIABLE, TWO_POINTERS_OPPOSITE, TWO_POINTERS_SAME,
)

def run_classifier(code_string):
    is_safe, errors, root = sanitize_code(code_string)
    assert is_safe, f"Sanitization failed: {errors}"
    features = extract_features(root)
    scores = classify_pattern(features)
    return scores

def test_clean_hashmap_lookup():
    code = """
def twoSum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        diff = target - num
        if diff in seen:
            return [seen[diff], i]
        seen[num] = i
    return []
"""
    scores = run_classifier(code)
    # Membership check (0.4) + Dict creation (0.3) + No increments (0.2) + Loop (0.1) = 1.0
    assert scores[HASH_MAP_LOOKUP] >= 0.8
    # Increments should be 0 because it's lookup (no += 1 or dict.get(..., 0)+1)
    # freq_score: dict_increments (0) + loop (0.2) + dict (0.2) + membership (0.1) = 0.5
    assert scores[HASH_MAP_FREQUENCY] < 0.6

def test_clean_hashmap_frequency():
    code = """
def frequencyCounter(s):
    counts = {}
    for char in s:
        counts[char] = counts.get(char, 0) + 1
    return counts
"""
    scores = run_classifier(code)
    # Increments (0.5) + Loop (0.2) + Dict (0.2) = 0.9
    assert scores[HASH_MAP_FREQUENCY] >= 0.8
    # Since dict_increments is True, lookup score: membership(0) + dict(0.3) + no_increments(0) + loop(0.1) = 0.4
    assert scores[HASH_MAP_LOOKUP] < 0.5

def test_messy_counter_frequency():
    code = """
from collections import Counter

class MessyFreqSolution:
    def solve_anagrams(self, word_a, word_b):
        print("Comparing two words using messy counter...")
        if len(word_a) != len(word_b):
            print("Lengths differ!")
            return False
            
        # Messy assignments and Counter usage
        freq_mapping_a = Counter(word_a)
        freq_mapping_b = Counter()
        
        # Extra prints and weird loop constructs
        for char_item in word_b:
            print("Processing character:", char_item)
            freq_mapping_b[char_item] += 1
            
        print("Frequency map A is:", freq_mapping_a)
        print("Frequency map B is:", freq_mapping_b)
        
        return freq_mapping_a == freq_mapping_b
"""
    scores = run_classifier(code)
    # Has increments (Counter / += 1) (0.5) + Loop (0.2) + Dict (0.2) = 0.9
    assert scores[HASH_MAP_FREQUENCY] >= 0.8
    assert scores[HASH_MAP_LOOKUP] < 0.5


@pytest.mark.parametrize("pattern,code", [
    (PREFIX_SUM, "def f(nums):\n pref=[0]*len(nums)\n pref[0]=nums[0]\n for i in range(1,len(nums)): pref[i]=pref[i-1]+nums[i]\n return pref\n"),
    (PREFIX_SUM, "def f(a):\n store=[0]*len(a)\n for idx in range(1,len(a)): store[idx]=store[idx-1]+a[idx]\n return store\n"),
    (SLIDING_WINDOW_FIXED, "def f(nums,k):\n total=0\n for i in range(k): total+=nums[i]\n for i in range(k,len(nums)): total+=nums[i]-nums[i-k]\n return total\n"),
    (SLIDING_WINDOW_FIXED, "def f(a,size):\n s=0\n for i in range(size): s+=a[i]\n for j in range(size,len(a)): s+=a[j]-a[j-size]\n return s\n"),
    (SLIDING_WINDOW_VARIABLE, "def f(s):\n seen={}; left=0\n for right,ch in enumerate(s):\n  if ch in seen: left=max(left,seen[ch]+1)\n  seen[ch]=right\n return left\n"),
    (SLIDING_WINDOW_VARIABLE, "def f(items):\n counts={}; start=0\n for end,x in enumerate(items):\n  if x in counts: start+=1\n  counts[x]=end\n return start\n"),
    (TWO_POINTERS_OPPOSITE, "def f(nums,target):\n left=0; right=len(nums)-1\n while left<right:\n  if nums[left]+nums[right]<target: left+=1\n  else: right-=1\n return False\n"),
    (TWO_POINTERS_OPPOSITE, "def f(a):\n l=0; r=len(a)-1\n while l<r:\n  if a[l]==a[r]: l+=1\n  else: r-=1\n return True\n"),
    (TWO_POINTERS_SAME, "def f(nums):\n slow=0; fast=0\n while fast<len(nums):\n  if nums[fast]!=0: slow+=1\n  fast+=1\n return slow\n"),
    (TWO_POINTERS_SAME, "def f(a):\n write=0; read=0\n while read<len(a):\n  if a[read]: write+=1\n  read+=1\n return write\n"),
])
def test_expanded_array_patterns(pattern, code):
    assert run_classifier(code)[pattern] >= 0.55
