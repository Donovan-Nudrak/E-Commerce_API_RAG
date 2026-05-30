import pytest

pytestmark = pytest.mark.integration


def test_rag_query_history_exceeds_max_returns_422(client):
    long_history = [
        {
            "role": "user" if index % 2 == 0 else "assistant",
            "content": f"Message {index}",
        }
        for index in range(11)
    ]

    response = client.post(
        "/api/v1/rag/query",
        json={"query": "auriculares baratos", "history": long_history},
    )

    assert response.status_code == 422
