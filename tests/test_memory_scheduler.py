from finance_forecast_agent.experiment_memory import ExperimentMemoryRecord
from finance_forecast_agent.memory_scheduler import GlobalMemoryScheduler, ResearchTaskCandidate
from finance_forecast_agent.research_journal import ReusableCapability


def _memory(run_id: str, mode: str, status: str) -> ExperimentMemoryRecord:
    return ExperimentMemoryRecord(
        run_id=run_id,
        run_mode=mode,
        task_fingerprint="task",
        method_id="method",
        model_family="model",
        status=status,
        metrics={},
        blockers=[] if status == "success" else ["failed"],
        artifact_path="report.json",
        experiment_type="signal_backtest",
        data_domain="us_equity",
    )


def test_scheduler_uses_reusable_capabilities_and_keeps_modes_isolated() -> None:
    capability = ReusableCapability("backtest", "Backtest", "protocol", {}, [])
    capability.status = "reusable_validated"
    candidates = [
        ResearchTaskCandidate(
            "strict-ready", "paper-a", "native_reproduction", "signal_backtest", "us_equity", ["backtest"], 0
        ),
        ResearchTaskCandidate(
            "explore-blocked", "paper-b", "common_benchmark", "signal_backtest", "us_equity", ["missing"], 2
        ),
    ]
    ranked = GlobalMemoryScheduler().rank(
        candidates,
        memory=[_memory("strict", "native_reproduction", "success"), _memory("explore", "common_benchmark", "blocked")],
        papers=[],
        capabilities={"backtest": capability},
    )
    assert ranked[0]["task_id"] == "strict-ready"
    assert ranked[0]["similar_successes"] == 1
    assert ranked[1]["similar_successes"] == 0
    assert ranked[1]["missing_capabilities"] == ["missing"]
