from app.llm.mock_client import MockLlmClient


def test_mock_llm_client_generates_response() -> None:
    client = MockLlmClient(model="mock-test")

    response = client.generate(
        prompt="Analyze this CV.",
        system_prompt="You are an HR document checking agent.",
    )

    assert response.provider == "mock"
    assert response.model == "mock-test"
    assert response.used_mock is True
    assert response.text


def test_mock_llm_client_is_available() -> None:
    client = MockLlmClient()

    assert client.is_available() is True