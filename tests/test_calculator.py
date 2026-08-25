from assistant.calculator import calculate


def test_addition():
    assert calculate("10 mais 20") == (30, None)


def test_subtraction():
    assert calculate("20 menos 5") == (15, None)


def test_multiplication():
    assert calculate("5 vezes 4") == (20, None)


def test_division():
    assert calculate("20 dividido por 4") == (5, None)


def test_division_by_zero():
    value, error = calculate("10 dividido por 0")
    assert value is None
    assert error == "division_by_zero"


def test_invalid_expression():
    value, error = calculate("banana")
    assert value is None
    assert error == "invalid_expression"


def test_numbers_spelled_out():
    assert calculate("dez mais vinte") == (30, None)


def test_ignores_filler_words_around_numbers():
    value, error = calculate("quanto e 10 mais 20 por favor")
    assert error is None
    assert value == 30
