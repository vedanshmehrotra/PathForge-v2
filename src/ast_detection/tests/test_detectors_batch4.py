"""Tests for detector implementations in Batch 4 (Linked List patterns)."""

import ast
from src.ast_detection.detectors.fast_slow_pointers import FastSlowPointersDetector
from src.ast_detection.detectors.linked_list_reversal import LinkedListReversalDetector
from src.ast_detection.detector_interface import DetectionResult


class TestFastSlowPointersDetector:
    def setup_method(self):
        self.detector = FastSlowPointersDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "fast_slow_pointers"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_loop(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_plain_traversal(self):
        code = """
def traverse(head):
    curr = head
    while curr:
        print(curr.val)
        curr = curr.next
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_array_pointers(self):
        code = """
def twoSum(arr, target):
    left = 0
    right = len(arr) - 1
    while left < right:
        s = arr[left] + arr[right]
        if s == target:
            return [left, right]
        elif s < target:
            left += 1
        else:
            right -= 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_floyd_cycle_detection(self):
        code = """
def hasCycle(head):
    if not head or not head.next:
        return False
    slow = head
    fast = head.next
    while slow != fast:
        if not fast or not fast.next:
            return False
        slow = slow.next
        fast = fast.next.next
    return True
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "floyd_traversal" for e in result.evidence)
        assert any(e.type == "cycle_check" for e in result.evidence)

    def test_detected_middle_of_linked_list(self):
        code = """
def middleNode(head):
    slow = head
    fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
    return slow
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence >= 0.80  # 0.60 traversal + 0.20 names
        assert any(e.type == "floyd_traversal" for e in result.evidence)
        assert any(e.type == "pointer_names" for e in result.evidence)

    def test_detected_floyd_cycle_detection_ii(self):
        code = """
def detectCycle(head):
    slow = head
    fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow == fast:
            slow = head
            while slow != fast:
                slow = slow.next
                fast = fast.next
            return slow
    return None
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "floyd_traversal" for e in result.evidence)
        assert any(e.type == "cycle_check" for e in result.evidence)

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestLinkedListReversalDetector:
    def setup_method(self):
        self.detector = LinkedListReversalDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "linked_list_reversal"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_rewiring_traversal(self):
        code = """
def printList(head):
    curr = head
    while curr:
        print(curr.val)
        curr = curr.next
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_recursive_sum(self):
        code = """
def sumList(head):
    if not head:
        return 0
    return head.val + sumList(head.next)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_iterative_reversal_classic(self):
        code = """
def reverseList(head):
    prev = None
    curr = head
    while curr:
        next_node = curr.next
        curr.next = prev
        prev = curr
        curr = next_node
    return prev
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence == 1.0
        assert any(e.type == "pointer_rewiring" for e in result.evidence)
        assert any(e.type == "prev_curr_update" for e in result.evidence)
        assert any(e.type == "reversal_variable_names" for e in result.evidence)

    def test_detected_iterative_reversal_tuple(self):
        code = """
def reverseList(head):
    prev = None
    curr = head
    while curr:
        curr.next, prev, curr = prev, curr, curr.next
    return prev
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "pointer_rewiring" for e in result.evidence)

    def test_detected_recursive_reversal_classic(self):
        code = """
def reverseList(head):
    if not head or not head.next:
        return head
    p = reverseList(head.next)
    head.next.next = head
    head.next = None
    return p
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence == 1.0
        assert any(e.type == "recursive_rewiring" for e in result.evidence)
        assert any(e.type == "recursive_call_with_next" for e in result.evidence)

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected
