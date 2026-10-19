"""Opt-in CLI inspection of actual production composition; no product endpoint or worker run."""

import hashlib
import inspect
import json
import os
from pathlib import Path
from urllib.parse import urlsplit


def _identity(value):
    cls = type(value)
    path = Path(inspect.getsourcefile(cls) or "").resolve()
    package = Path(__file__).resolve().parents[1]
    if not path.is_relative_to(package):
        raise ValueError("H02 nonlocal binding")
    _, line = inspect.getsourcelines(cls)
    return {
        "type": cls.__module__ + "." + cls.__qualname__,
        "path": "backend/src/" + path.relative_to(package.parent).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "line": line,
    }


def _application_routes(routes, depth=0):
    """Follow FastAPI's actual included-router contexts, including effective prefixes."""
    if depth > 12:
        raise ValueError("H02 router nesting limit")
    for route in routes:
        if callable(getattr(route, "effective_candidates", None)):
            yield from _application_routes(route.effective_candidates(), depth + 1)
        else:
            yield route


def capture(environment):
    if (
        environment.get("APP_ENVIRONMENT") not in {"local", "test"}
        or environment.get("CONTROLPROOF_H02_INSPECT_ENABLED") != "true"
        or environment.get("CONTROLPROOF_EXTERNAL_AI_ALLOWED") != "false"
        or environment.get("CONTROLPROOF_MODEL_FIXTURE_ID") != "h02-capability-v1"
        or urlsplit(
            environment.get("DATABASE_URL", "").replace("postgresql+psycopg", "postgresql")
        ).hostname
        not in {"localhost", "127.0.0.1", "::1"}
    ):
        raise RuntimeError("H02 inspector disabled")
    # The worker composition constructs the same production API runtime internally. Build an
    # independent API runtime with the actual selected dependencies, never an in-memory fallback.
    from interview_evidence.runtime.aws import create_aws_runtime_dependencies
    from interview_evidence.runtime.production import create_production_runtime
    from interview_evidence.runtime.worker import create_production_worker_runtime

    aws = create_aws_runtime_dependencies(environment)
    runtime = create_production_runtime(
        environment,
        principal_provider=aws.principal_provider,
        object_storage=aws.object_storage,
        media_storage=aws.media_storage,
        email_sender=aws.email_sender,
        search_index=aws.search_index,
        model=aws.model,
        embedder=aws.embedder,
        queues=aws.queues,
        metrics=aws.metrics,
        speech_to_text=aws.speech_to_text,
        text_to_speech=aws.text_to_speech,
    )
    worker = create_production_worker_runtime(environment)
    readers = {}
    visited = set()

    def closures(function, depth=0):
        if not inspect.isfunction(function) or depth > 4 or id(function) in visited:
            return
        visited.add(id(function))
        values = inspect.getclosurevars(function).nonlocals
        for key, value in values.items():
            if (
                key in {"pipeline_reader", "answer_service", "search_service", "company_service"}
                and value is not None
            ):
                readers[key] = _identity(value)
            if inspect.isfunction(value):
                closures(value, depth + 1)

    routes = []
    for route in _application_routes(runtime.app.routes):
        if "/assistant/" in getattr(route, "path", ""):
            for method in sorted(route.methods):
                routes.append(f"{method} {route.path}")
            closures(route.endpoint)
    return {
        "schema_version": "controlproof.h02-runtime-binding.v1",
        "routes": sorted(routes),
        "assistant_readers": readers,
        "helpers": {key: _identity(value) for key, value in runtime.worker_handlers.items()},
        "routing": dict(sorted(worker.dispatcher._routing.items())),
        "consumers": [
            {
                "name": c._consumer_name,
                "handlers": {key: _identity(value) for key, value in c._handlers.items()},
            }
            for c in worker.consumers
        ],
        "assistant_answer": _identity(runtime.resources["assistant_answers"]),
        "assistant_model": _identity(runtime.resources["assistant_answers"]._model),
        "ran_worker": False,
    }


def main():
    try:
        print(json.dumps(capture(dict(os.environ)), sort_keys=True))
    except Exception as error:
        # Stable class code only: dependency/configuration exceptions may contain credentials.
        print(json.dumps({"error_code": type(error).__name__, "binding_complete": False}))
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
