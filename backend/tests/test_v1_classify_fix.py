def test_classify_hs_no_json(client, api_key_header):
    """
    非JSONリクエスト（Content-Typeなし、Bodyなし）を送った場合に
    500 Internal Server Error にならず、400 Bad Request 等が返ることを確認
    """
    # Content-Typeを指定せずにPOST
    response = client.post("/v1/classify/hs", headers=api_key_header)

    assert response.status_code != 500
    # 期待値: 400 (Bad Request), 415 (Unsupported Media Type), or 422 (Unprocessable Entity)
    assert response.status_code in [400, 415, 422]


def test_classify_hs_invalid_json(client, api_key_header):
    """
    不正なJSONを送った場合の挙動
    """
    response = client.post(
        "/v1/classify/hs",
        data="invalid json",
        content_type="application/json",
        headers=api_key_header,
    )
    assert response.status_code != 500
    assert response.status_code in [400, 422]
