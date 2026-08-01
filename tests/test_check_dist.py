import tarfile
import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from devtools.check_dist import (
    DistributionValidationError,
    validate_dist_directory,
    validate_sdist,
    validate_wheel,
)


def _metadata(version: str) -> bytes:
    return f"Metadata-Version: 2.4\nName: frontmatter-format\nVersion: {version}\n".encode()


def _write_sdist(path: Path, version: str, extra_path: str | None = None) -> None:
    root = f"frontmatter_format-{version}"
    files = {
        ".gitignore": b"__pycache__/\n",
        "LICENSE": b"MIT\n",
        "PKG-INFO": _metadata(version),
        "README.md": b"# Frontmatter Format\n",
        "pyproject.toml": b"[build-system]\n",
        "src/frontmatter_format/__init__.py": b"",
    }
    if extra_path is not None:
        files[extra_path] = b"unexpected\n"

    with tarfile.open(path, mode="w:gz") as archive:
        for relative_path, contents in files.items():
            info = tarfile.TarInfo(f"{root}/{relative_path}")
            info.size = len(contents)
            archive.addfile(info, BytesIO(contents))


def _write_wheel(path: Path, version: str) -> None:
    dist_info = f"frontmatter_format-{version}.dist-info"
    with zipfile.ZipFile(path, mode="w") as archive:
        archive.writestr("frontmatter_format/__init__.py", "")
        archive.writestr(f"{dist_info}/METADATA", _metadata(version))
        archive.writestr(f"{dist_info}/RECORD", "")
        archive.writestr(f"{dist_info}/WHEEL", "Wheel-Version: 1.0\n")


def test_validate_dist_directory_accepts_minimal_artifacts(tmp_path: Path):
    version = "0.4.0"
    _write_sdist(tmp_path / f"frontmatter_format-{version}.tar.gz", version)
    _write_wheel(tmp_path / f"frontmatter_format-{version}-py3-none-any.whl", version)

    assert validate_dist_directory(tmp_path, expected_version=version) == version


def test_validate_sdist_rejects_internal_repository_state(tmp_path: Path):
    path = tmp_path / "frontmatter_format-0.4.0.tar.gz"
    _write_sdist(path, "0.4.0", extra_path=".tbd/issues.jsonl")

    with pytest.raises(DistributionValidationError, match="Unexpected source distribution"):
        validate_sdist(path)


def test_validate_sdist_rejects_path_traversal(tmp_path: Path):
    path = tmp_path / "frontmatter_format-0.4.0.tar.gz"
    _write_sdist(path, "0.4.0", extra_path="../outside.txt")

    with pytest.raises(DistributionValidationError, match="Unsafe archive path"):
        validate_sdist(path)


def test_validate_dist_directory_rejects_mismatched_versions(tmp_path: Path):
    _write_sdist(tmp_path / "frontmatter_format-0.4.0.tar.gz", "0.4.0")
    _write_wheel(tmp_path / "frontmatter_format-0.4.1-py3-none-any.whl", "0.4.1")

    with pytest.raises(DistributionValidationError, match="Artifact versions differ"):
        validate_dist_directory(tmp_path)


def test_validate_wheel_rejects_unexpected_files(tmp_path: Path):
    path = tmp_path / "frontmatter_format-0.4.0-py3-none-any.whl"
    _write_wheel(path, "0.4.0")
    with zipfile.ZipFile(path, mode="a") as archive:
        archive.writestr("repository-secret.txt", "not publishable\n")

    with pytest.raises(DistributionValidationError, match="Unexpected wheel member"):
        validate_wheel(path)
