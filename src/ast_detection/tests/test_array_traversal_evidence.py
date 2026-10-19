"""Array evidence must refer to executed element use in the same loop."""
import ast

import pytest

from src.ast_detection.detectors.array_traversal import ArrayTraversalDetector


@pytest.mark.parametrize("source", [
    "for index, item in enumerate(values):\n    print(item)",
    "for offset, entry in enumerate(records, 1):\n    output.append((offset, entry))",
    "for item in values:\n    output.append(item)",
    "for index in range(len(values)):\n    output.append(values[index])",
    "for index, item in enumerate(values):\n    output[index] = item * 2",
])
def test_used_elements_are_recognized_across_supported_iteration_forms(source):
    result = ArrayTraversalDetector().detect(ast.parse(source))
    assert result.detected
    assert result.confidence > 0


@pytest.mark.parametrize("source", [
    "def solve(values: List[int]):\n    for i in range(10):\n        pass",
    "def first():\n    for i in range(10):\n        pass\ndef second(values):\n    return values[0]",
    "for i in range(10):\n    print(values[0])",
    "for index, item in enumerate(values):\n    output.append(index)",
    "for index, item in enumerate(values):\n    pass",
    "for item in values:\n    def other():\n        return item",
    "def solve(values, enumerate):\n    for index, item in enumerate(values):\n        print(item)",
    "for i in range(10):\n    cached: List[i] = None",
])
def test_annotations_unused_elements_and_disconnected_access_are_not_evidence(source):
    result = ArrayTraversalDetector().detect(ast.parse(source))
    assert not result.detected
    assert result.evidence == []
