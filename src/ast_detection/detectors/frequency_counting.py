"""Occurrence updates on a linked local mapping, including Counter snippets."""
from src.ast_detection.collection_links import collection_events
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class FrequencyCountingDetector(BaseDetector):
    pattern_id = 'hash_map_frequency'

    def detect(self, ast_root):
        events = [e for e in collection_events(ast_root)
                  if e['kind'] in ('frequency_increment', 'constructor_count')]
        evidence = []
        if events:
            event = events[0]
            state, operation = event['collection'], event['node']
            observations = [('empty_dict_creation', state.creation, 0.25, 'Linked counting collection')]
            if state.imported:
                observations.append(('counter_import', state.imported, 0.20, 'Standard collections import'))
            if event['kind'] == 'frequency_increment':
                observations.append(('frequency_increment', operation, 0.35, 'Unit occurrence update on the same collection and key'))
                observations.append(('counting_loop', event['loop'], 0.20, 'Loop containing the occurrence update'))
            else:
                observations.append(('counter_constructor', operation, 0.30, 'Counter constructed from an iterable'))
            for kind, node, weight, description in observations:
                evidence.append(EvidenceItem(type=kind, description=description,
                    location=f'{node.lineno}:{node.col_offset}', weight=weight))
        return DetectionResult(pattern_id=self.pattern_id, detected=bool(evidence),
            confidence=min(sum(e.weight for e in evidence), 1.0), evidence=evidence)
