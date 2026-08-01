"""
Validate release artifacts before publishing them.
"""

import argparse
import stat
import tarfile
import zipfile
from email.parser import Parser
from pathlib import Path, PurePosixPath

PROJECT_NAME = "frontmatter-format"
PACKAGE_PATH = "frontmatter_format"

_SDIST_ALLOWED_ROOT_FILES = {
    ".gitignore",
    "LICENSE",
    "PKG-INFO",
    "README.md",
    "pyproject.toml",
}
_SDIST_REQUIRED_ROOT_FILES = {"LICENSE", "PKG-INFO", "README.md", "pyproject.toml"}
_SDIST_SOURCE_DIRS = {"src", f"src/{PACKAGE_PATH}"}
_SDIST_SOURCE_PREFIX = f"src/{PACKAGE_PATH}/"
MINIMUM_ROOTED_PATH_PARTS = 2
"""
Minimum path segments for a member beneath a common archive root.
"""
EXPECTED_SINGLETON_COUNT = 1
"""
Required count whenever a validated value must be unique.
"""
ZIP_MODE_SHIFT_BITS = 16
"""
Bit shift from a ZIP external attribute to its Unix file mode.
"""
SUCCESS_EXIT_CODE = 0
"""
Process exit code after every requested validation succeeds.
"""


class DistributionValidationError(ValueError):
    """
    Raised when a built distribution is unsafe or internally inconsistent.
    """


def _validate_member_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if not name or path.is_absolute() or ".." in path.parts or "\\" in name:
        raise DistributionValidationError(f"Unsafe archive path: {name!r}")
    return path


def _metadata_version(metadata_text: str, source: Path) -> str:
    metadata = Parser().parsestr(metadata_text)
    name = metadata.get("Name")
    version = metadata.get("Version")
    if not name or not version:
        raise DistributionValidationError(f"Missing Name or Version metadata in {source}")
    if name != PROJECT_NAME:
        raise DistributionValidationError(f"Unexpected project name in {source}: {name!r}")
    return version


def validate_sdist(path: Path, expected_version: str | None = None) -> str:
    """
    Validate an sdist's paths and metadata, returning its package version.
    """
    with tarfile.open(path, mode="r:gz") as archive:
        members = archive.getmembers()
        if not members:
            raise DistributionValidationError(f"Empty source distribution: {path}")
        member_names = [member.name for member in members]
        if len(member_names) != len(set(member_names)):
            raise DistributionValidationError(f"Source distribution has duplicate paths: {path}")

        roots: set[str] = set()
        relative_paths: set[str] = set()
        metadata_member: tarfile.TarInfo | None = None
        for member in members:
            member_path = _validate_member_path(member.name)
            if len(member_path.parts) < MINIMUM_ROOTED_PATH_PARTS:
                raise DistributionValidationError(
                    f"Source distribution member lacks a common root: {member.name!r}"
                )
            roots.add(member_path.parts[0])
            relative_path = PurePosixPath(*member_path.parts[1:]).as_posix()
            relative_paths.add(relative_path)

            if member.issym() or member.islnk() or not (member.isdir() or member.isfile()):
                raise DistributionValidationError(
                    f"Source distribution contains a non-regular member: {member.name!r}"
                )
            if (
                relative_path not in _SDIST_ALLOWED_ROOT_FILES
                and relative_path not in _SDIST_SOURCE_DIRS
                and not relative_path.startswith(_SDIST_SOURCE_PREFIX)
            ):
                raise DistributionValidationError(
                    f"Unexpected source distribution member: {relative_path!r}"
                )
            if relative_path == "PKG-INFO":
                metadata_member = member

        if len(roots) != EXPECTED_SINGLETON_COUNT:
            raise DistributionValidationError(
                f"Source distribution must have one common root, found: {sorted(roots)}"
            )

        required_paths = _SDIST_REQUIRED_ROOT_FILES | {f"src/{PACKAGE_PATH}/__init__.py"}
        missing_paths = required_paths - relative_paths
        if missing_paths:
            raise DistributionValidationError(
                f"Source distribution is missing required files: {sorted(missing_paths)}"
            )
        if metadata_member is None:
            raise DistributionValidationError("Source distribution is missing PKG-INFO")
        metadata_file = archive.extractfile(metadata_member)
        if metadata_file is None:
            raise DistributionValidationError("Could not read source distribution PKG-INFO")
        version = _metadata_version(metadata_file.read().decode("utf-8"), path)
        expected_root = f"{PACKAGE_PATH}-{version}"
        actual_root = next(iter(roots))
        if actual_root != expected_root:
            raise DistributionValidationError(
                f"Source distribution root {actual_root!r} does not match {expected_root!r}"
            )

    if expected_version is not None and version != expected_version:
        raise DistributionValidationError(
            f"Source distribution version {version!r} does not match {expected_version!r}"
        )
    return version


def validate_wheel(path: Path, expected_version: str | None = None) -> str:
    """
    Validate a wheel's paths and metadata, returning its package version.
    """
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if not infos:
            raise DistributionValidationError(f"Empty wheel: {path}")
        member_names = [info.filename for info in infos]
        if len(member_names) != len(set(member_names)):
            raise DistributionValidationError(f"Wheel has duplicate paths: {path}")

        metadata_infos: list[zipfile.ZipInfo] = []
        for info in infos:
            member_path = _validate_member_path(info.filename)
            mode = info.external_attr >> ZIP_MODE_SHIFT_BITS
            if stat.S_ISLNK(mode):
                raise DistributionValidationError(f"Wheel contains a symlink: {info.filename!r}")
            if (
                len(member_path.parts) == MINIMUM_ROOTED_PATH_PARTS
                and member_path.parts[0].startswith(f"{PACKAGE_PATH}-")
                and member_path.parts[0].endswith(".dist-info")
                and member_path.parts[1] == "METADATA"
            ):
                metadata_infos.append(info)

        if len(metadata_infos) != EXPECTED_SINGLETON_COUNT:
            raise DistributionValidationError(
                f"Wheel must contain exactly one METADATA file, found {len(metadata_infos)}"
            )
        metadata_info = metadata_infos[0]
        dist_info_prefix = f"{PurePosixPath(metadata_info.filename).parts[0]}/"

        for info in infos:
            if not (
                info.filename.startswith(f"{PACKAGE_PATH}/")
                or info.filename.startswith(dist_info_prefix)
            ):
                raise DistributionValidationError(f"Unexpected wheel member: {info.filename!r}")

        version = _metadata_version(archive.read(metadata_info).decode("utf-8"), path)
        required_paths = {
            f"{PACKAGE_PATH}/__init__.py",
            f"{dist_info_prefix}METADATA",
            f"{dist_info_prefix}RECORD",
            f"{dist_info_prefix}WHEEL",
        }
        missing_paths = required_paths - set(archive.namelist())
        if missing_paths:
            raise DistributionValidationError(
                f"Wheel is missing required files: {sorted(missing_paths)}"
            )

    if expected_version is not None and version != expected_version:
        raise DistributionValidationError(
            f"Wheel version {version!r} does not match {expected_version!r}"
        )
    return version


def validate_dist_directory(dist_dir: Path, expected_version: str | None = None) -> str:
    """
    Validate the sole wheel and sdist in a build output directory.
    """
    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    if len(wheels) != EXPECTED_SINGLETON_COUNT or len(sdists) != EXPECTED_SINGLETON_COUNT:
        message = f"Expected one wheel and one sdist in {dist_dir}; "
        message += f"found {len(wheels)} wheel(s) and {len(sdists)} sdist(s)"
        raise DistributionValidationError(message)

    wheel_version = validate_wheel(wheels[0], expected_version)
    sdist_version = validate_sdist(sdists[0], expected_version)
    if wheel_version != sdist_version:
        raise DistributionValidationError(
            f"Artifact versions differ: wheel={wheel_version!r}, sdist={sdist_version!r}"
        )
    return wheel_version


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist_dir", nargs="?", type=Path, default=Path("dist"))
    parser.add_argument("--version", dest="expected_version")
    args = parser.parse_args()

    version = validate_dist_directory(args.dist_dir, args.expected_version)
    print(f"Validated {PROJECT_NAME} {version} wheel and source distribution.")
    return SUCCESS_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
