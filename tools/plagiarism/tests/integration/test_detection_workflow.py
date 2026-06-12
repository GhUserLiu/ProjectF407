"""
查重检测集成测试
"""

import pytest
from tools.plagiarism.core import PlagiarismDetector, SimilarityMethod


class TestDetectionWorkflow:
    """检测工作流集成测试"""
    
    def test_basic_detection(self, sample_submission):
        """测试基础检测流程"""
        detector = PlagiarismDetector(
            method=SimilarityMethod.HYBRID,
            threshold=60.0
        )
        
        submissions = {
            '001': sample_submission,
            '002': {
                **sample_submission,
                'student_id': '002',
                'name': '李四'
            }
        }
        
        results = detector.detect(submissions)
        assert results is not None
    
    def test_cross_group_detection(self, sample_submission):
        """测试跨组检测"""
        detector = PlagiarismDetector(
            method=SimilarityMethod.HYBRID,
            threshold=60.0,
            group_info={'001': 'A', '002': 'B'}
        )
        
        submissions = {
            '001': sample_submission,
            '002': {**sample_submission, 'student_id': '002'}
        }
        
        results = detector.detect(submissions)
        # 验证跨组标记
        for result in results:
            if result.similar_to in detector.group_info:
                if detector.group_info.get(result.student_id) != detector.group_info.get(result.similar_to):
                    assert result.is_cross_group == True
