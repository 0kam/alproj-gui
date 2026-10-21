"""Tests for cancelling camera parameter estimation runs."""

import threading

import numpy as np
import pandas as pd
import pytest
from alproj.optimize import CMAOptimizer, LsqOptimizer, project

from app.services.georectify import (
    EstimationCancelled,
    _make_cancellable,
    finish_estimation_run,
    start_estimation_run,
)

PARAMS = {
    "x": 0.0, "y": 0.0, "z": 0.0, "fov": 60.0, "pan": 0.0, "tilt": 0.0, "roll": 0.0,
    "a1": 1.0, "a2": 1.0, "k1": 0.0, "k2": 0.0, "k3": 0.0, "k4": 0.0, "k5": 0.0, "k6": 0.0,
    "p1": 0.0, "p2": 0.0, "s1": 0.0, "s2": 0.0, "s3": 0.0, "s4": 0.0,
    "w": 640, "h": 480, "cx": 320.0, "cy": 240.0,
}  # fmt: skip


def _gcps() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(0)
    obj = pd.DataFrame(
        {
            "x": rng.uniform(-500, 500, 30),
            "y": rng.uniform(1000, 3000, 30),
            "z": rng.uniform(-200, 200, 30),
        }
    )
    img = pd.DataFrame(project(obj, PARAMS), columns=["u", "v"])
    return obj, img


@pytest.mark.parametrize("optimizer_cls", [CMAOptimizer, LsqOptimizer])
def test_optimizer_stops_when_cancelled(optimizer_cls: type) -> None:
    obj, img = _gcps()
    cancel_event = threading.Event()
    cancel_event.set()
    opt = _make_cancellable(optimizer_cls(obj, img, PARAMS), cancel_event)
    opt.set_target(["pan", "tilt"])

    with pytest.raises(EstimationCancelled):
        opt.optimize()


def test_optimizer_runs_normally_when_not_cancelled() -> None:
    obj, img = _gcps()
    opt = _make_cancellable(CMAOptimizer(obj, img, PARAMS), threading.Event())
    opt.set_target(["pan", "tilt"])

    _, error = opt.optimize(generation=5, population_size=5)

    assert np.isfinite(error)


def test_cancellation_is_not_swallowed_by_broad_exception_handlers() -> None:
    with pytest.raises(EstimationCancelled):
        try:
            raise EstimationCancelled()
        except Exception:  # pipeline fallbacks catch Exception
            pytest.fail("EstimationCancelled must not be caught as Exception")


def test_new_estimation_run_cancels_previous_one() -> None:
    first = start_estimation_run()
    second = start_estimation_run()

    assert first.is_set()
    assert not second.is_set()

    finish_estimation_run(first)  # finishing a superseded run keeps the active one
    third = start_estimation_run()
    assert second.is_set()

    finish_estimation_run(third)
    assert not start_estimation_run().is_set()
