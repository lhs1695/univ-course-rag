from __future__ import annotations

import shutil
from pathlib import Path
from uuid import UUID


class StorageError(RuntimeError):
    pass


class StorageBoundaryError(StorageError):
    pass


def _resolved_root(upload_dir: Path) -> Path:
    return upload_dir.resolve()


def _require_within(path: Path, parent: Path) -> Path:
    resolved = path.resolve()
    if resolved == parent or not resolved.is_relative_to(parent):
        raise StorageBoundaryError("storage target is outside its expected directory")
    return resolved


def store_upload(
    upload_dir: Path,
    course_id: UUID,
    document_id: UUID,
    filename: str,
    data: bytes,
) -> Path:
    safe_name = Path(filename).name
    if not safe_name or safe_name != filename:
        raise StorageBoundaryError("invalid upload filename")
    root = _resolved_root(upload_dir)
    document_dir = _require_within(root / str(course_id) / str(document_id), root)
    destination = _require_within(document_dir / safe_name, document_dir)
    try:
        document_dir.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    except OSError as exc:
        try:
            destination.unlink(missing_ok=True)
        except OSError:
            pass
        raise StorageError("could not store upload") from exc
    return destination


def get_document_upload(
    upload_dir: Path,
    course_id: UUID,
    document_id: UUID,
    storage_path: str,
) -> Path:
    root = _resolved_root(upload_dir)
    document_dir = _require_within(root / str(course_id) / str(document_id), root)
    target = _require_within(Path(storage_path), document_dir)
    try:
        if not target.is_file():
            raise StorageError("document upload is unavailable")
    except OSError as exc:
        raise StorageError("document upload is unavailable") from exc
    return target


def delete_document_upload(
    upload_dir: Path,
    course_id: UUID,
    document_id: UUID,
    storage_path: str,
) -> None:
    root = _resolved_root(upload_dir)
    document_dir = _require_within(root / str(course_id) / str(document_id), root)
    target = _require_within(Path(storage_path), document_dir)
    try:
        if target.exists():
            if not target.is_file():
                raise StorageBoundaryError("document storage target is not a file")
            target.unlink()
        if document_dir.is_dir() and not any(document_dir.iterdir()):
            document_dir.rmdir()
        course_dir = document_dir.parent
        if course_dir != root and course_dir.is_dir() and not any(course_dir.iterdir()):
            course_dir.rmdir()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise StorageError("could not delete document upload") from exc


def delete_course_uploads(upload_dir: Path, course_id: UUID) -> None:
    root = _resolved_root(upload_dir)
    course_dir = _require_within(root / str(course_id), root)
    if not course_dir.exists():
        return
    if not course_dir.is_dir():
        raise StorageBoundaryError("course storage target is not a directory")
    try:
        shutil.rmtree(course_dir)
    except OSError as exc:
        raise StorageError("could not delete course uploads") from exc
