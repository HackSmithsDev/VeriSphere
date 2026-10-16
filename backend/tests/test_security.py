from app.core.security import (
    create_access_token,
    hash_password,
    read_access_token,
    verify_password,
)


def test_password_hash_verifies_only_the_original_password() -> None:
    encoded = hash_password("correct-horse-battery-staple")

    assert encoded != "correct-horse-battery-staple"
    assert verify_password("correct-horse-battery-staple", encoded)
    assert not verify_password("incorrect-password", encoded)
    assert not verify_password("incorrect-password", "not-a-password-hash")


def test_access_token_is_signed_and_exposes_its_subject() -> None:
    token = create_access_token("user-17")

    assert read_access_token(token) == "user-17"
    header, payload, signature = token.split(".")
    changed_payload = ("a" if payload[0] != "a" else "b") + payload[1:]
    changed_token = f"{header}.{changed_payload}.{signature}"
    assert read_access_token(changed_token) is None
    assert read_access_token("not-a-token") is None
