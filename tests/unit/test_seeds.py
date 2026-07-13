import random

import numpy as np

from mavs10d.core.seeds import derive_seed, set_deterministic_seed


def test_set_deterministic_seed_repeats_python_and_numpy_sequences() -> None:
    set_deterministic_seed(17)
    python_a = [random.random() for _ in range(3)]
    numpy_a = np.random.random(3).tolist()

    set_deterministic_seed(17)
    python_b = [random.random() for _ in range(3)]
    numpy_b = np.random.random(3).tolist()

    assert python_a == python_b
    assert numpy_a == numpy_b


def test_derive_seed_is_stable_and_namespaced() -> None:
    assert derive_seed(10, "env") == derive_seed(10, "env")
    assert derive_seed(10, "env") != derive_seed(10, "method")

