"""
HS分類 E2Eシナリオテスト (リコール計測)
"""

import pytest
import json
import os
from pathlib import Path
from flask.testing import FlaskClient

# テストデータのパス
DATA_FILE = Path(__file__).parent.parent / "data" / "hs_test_cases.json"

def load_test_cases():
    """テストケースを読み込む"""
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="module")
def test_cases():
    return load_test_cases()

class TestHSScenarios:
    """E2Eシナリオテスト"""
    
    def test_recall_rate(self, client: FlaskClient, api_key_header, test_cases):
        """リコール率の計測と検証"""
        if not test_cases:
            pytest.skip("No test cases found")
            
        results = []
        
        print(f"\nRunning {len(test_cases)} scenarios...")
        
        for case in test_cases:
            case_id = case["id"]
            expected_hs = case["expected_hs"]
            expect_review = case.get("expect_review", False)
            
            # APIリクエスト
            response = client.post(
                "/v1/classify/hs",
                json={
                    "product": case["product"],
                    "traceId": f"E2E-{case_id}"
                },
                headers=api_key_header
            )
            
            # 結果判定
            is_success = False
            actual_hs = None
            review_required = False
            confidence = 0.0
            
            if response.status_code == 200:
                data = response.get_json()
                actual_hs = data.get("final_hs_code")
                review_required = data.get("review_required", False)
                if data.get("hs_candidates"):
                    confidence = data["hs_candidates"][0].get("confidence", 0.0)
                
                # HSコードの一致確認 (期待値が設定されている場合)
                if expected_hs:
                    # review_requiredがTrueなら、HSコードが一致しなくても正解とするケースもあるかもしれないが
                    # ここではHSコードの一致を厳密に見るか、review判定を見るかで判断
                    
                    if actual_hs == expected_hs:
                        is_success = True
                    elif expect_review and review_required:
                         # レビュー必須が期待され、実際にレビュー必須ならOKとする場合も
                         # しかし今回はリコール率＝正解率とするため、HSコードの一致を重視
                         # ただし、expected_hsがnullの場合は「分類不能」が正解
                         pass
                elif expected_hs is None:
                    # 分類不能が期待される場合
                    # 422エラーまたはcandidatesなしならOK
                    # 200 OK で返ってきても、信頼度が低いなど
                    pass

            # エラーケース (422) のハンドリング
            elif response.status_code == 422 and expected_hs is None:
                 is_success = True
            
            # 結果記録
            result = {
                "id": case_id,
                "expected": expected_hs,
                "actual": actual_hs,
                "success": is_success,
                "review_required": review_required,
                "expect_review": expect_review
            }
            results.append(result)
            
            status_mark = "✅" if is_success else "❌"
            print(f"{status_mark} {case_id}: Expected {expected_hs}, Got {actual_hs} (Rev: {review_required})")
            
        # 集計
        total = len(results)
        # expected_hsがあるもののうち、正解した数
        valid_cases = [r for r in results if r["expected"] is not None]
        correct_count = sum(1 for r in valid_cases if r["success"])
        
        recall = correct_count / len(valid_cases) if valid_cases else 0.0
        
        print(f"\nRecall Rate: {recall:.2%} ({correct_count}/{len(valid_cases)})")
        
        # 目標: 80%以上
        # ただし、現在のルールセットは最小限なので、低い可能性がある
        # 失敗したケースの詳細を出力してデバッグに役立てる
        
        failures = [r for r in valid_cases if not r["success"]]
        if failures:
            print("\nFailures:")
            for f in failures:
                print(f"  - {f['id']}: Expected {f['expected']}, Got {f['actual']}")
        
        # 目標: 80%以上
        # ルールセットが拡張されたため、要件通りの閾値を設定
        assert recall >= 0.8

