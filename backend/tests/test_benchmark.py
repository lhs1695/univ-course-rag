import json
from pathlib import Path

import pytest
from app.benchmark import (
    BENCHMARK_VERSION,
    BenchmarkConfig,
    BenchmarkError,
    main,
    parse_scales,
    run_benchmark,
    synthetic_markdown,
)
from app.db import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_synthetic_markdown_is_repeatable_and_has_exact_chunks() -> None:
    first = synthetic_markdown(7)
    second = synthetic_markdown(7)

    assert first == second
    assert first.count("# Synthetic Unit") == 7
    assert "student" not in first.lower()
    assert "course material" in first


@pytest.mark.parametrize("value", ["", "0", "10001", "2,1", "1,1", "x"])
def test_scale_validation_is_bounded(value: str) -> None:
    with pytest.raises(BenchmarkError):
        parse_scales(value)


def test_sqlite_benchmark_reports_only_aggregates(tmp_path: Path) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    report = run_benchmark(
        factory,
        database_path="sqlite_exact_python",
        source_root=tmp_path,
        config=BenchmarkConfig(scales=(3, 7), batch_size=2, retrieval_runs=3),
        cleanup_persistent=False,
    )
    dumped = json.dumps(report)

    assert report["benchmark_version"] == BENCHMARK_VERSION
    assert report["database_path"] == "sqlite_exact_python"
    assert report["synthetic_data"]["generator"] == "deterministic-v2"
    assert report["synthetic_data"]["raw_payload_persisted"] is False
    assert [row["actual_chunk_count"] for row in report["results"]] == [3, 7]
    assert [row["ingest"]["embedding_batch_count"] for row in report["results"]] == [2, 4]
    assert report["correctness"] == {
        "all_ingest_counts_exact": True,
        "all_retrievals_returned_results": True,
        "all_top_hits_correct": True,
    }
    assert "Synthetic benchmark scale" not in dumped
    assert "synthetic-benchmark-not-a-login" not in dumped
    assert "database_url" not in dumped
    assert "course_id" not in dumped
    assert "user_id" not in dumped
    assert "document_id" not in dumped


def test_cli_defaults_to_dry_run_and_requires_postgres_acknowledgement(capsys) -> None:
    assert main(["--database", "sqlite", "--scales", "3,7"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "mode": "dry-run",
        "database": "sqlite",
        "scales": [3, 7],
    }

    assert main(["--run", "--database", "postgres", "--scales", "3"]) == 2
    assert "requires --allow-postgres" in capsys.readouterr().err
