from app.domain.policies.normalization import normalize_title


def test_should_normalize_service_prefixes_and_punctuation() -> None:
    assert normalize_title("Breaking: BMW, launches  new model!") == "bmw launches new model"
