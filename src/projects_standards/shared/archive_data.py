# Objetivo do script:
# Compactar e descompactar snapshots de dados (bronze, silver, gold), incluindo bundles com core e partes espaciais.
# Processo:
# 1. Ler argumentos CLI (--pack ou --unpack, --layer, --standard opcional, --date opcional).
# 2. Resolver o diretorio base da camada selecionada.
# 3. Localizar snapshots ou arquivos compactados que atendam aos filtros.
# 4. --pack: compactar cada snapshot, usando bundle core+spatial quando houver pasta spatial/.
# 5. --unpack: descompactar ZIPs simples ou bundles core+spatial no diretorio correto.
# 6. Para gold, compactar/descompactar a pasta projects/ diretamente.
# 7. Exibir relatorio de progresso no terminal.

from __future__ import annotations

import argparse
import shutil
import time
import zipfile
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parents[2]
DATA_BASE_DIR = ROOT_DIR / "data" / "project_standards"

LAYER_DIRS = {
    "bronze": DATA_BASE_DIR / "01_bronze",
    "silver": DATA_BASE_DIR / "02_silver",
    "gold": DATA_BASE_DIR / "03_gold",
}

DEFAULT_SPATIAL_SUBDIR_NAME = "spatial"
DEFAULT_SPATIAL_PART_MAX_BYTES = 1_800_000_000
DEFAULT_REMOVE_RETRY_ATTEMPTS = 5
DEFAULT_REMOVE_RETRY_SLEEP_SECONDS = 1.0


# Formata tamanho em bytes para exibicao legivel.
def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


# Coleta snapshots (pastas YYYYMMDD) dentro de cada certificadora da camada.
# Ignora pastas que ja possuem ZIP correspondente simples ou bundle core.
def find_snapshots(layer_dir: Path, standard: str | None, date: str | None) -> list[Path]:
    snapshots: list[Path] = []
    if not layer_dir.exists():
        return snapshots
    for standard_dir in sorted(layer_dir.iterdir()):
        if not standard_dir.is_dir():
            continue
        if standard and standard_dir.name != standard:
            continue
        for snapshot_dir in sorted(standard_dir.iterdir()):
            if not snapshot_dir.is_dir():
                continue
            if date and snapshot_dir.name != date:
                continue
            zip_path = snapshot_dir.parent / f"{snapshot_dir.name}.zip"
            core_zip_path = snapshot_dir.parent / f"{snapshot_dir.name}_core.zip"
            core_part_paths = list(snapshot_dir.parent.glob(f"{snapshot_dir.name}_core_*.zip"))
            if zip_path.exists() or core_zip_path.exists() or core_part_paths:
                continue
            snapshots.append(snapshot_dir)
    return snapshots


# Extrai o nome base do snapshot a partir do nome do arquivo compactado.
def extract_snapshot_name_from_archive_name(archive_stem: str) -> str | None:
    if archive_stem.endswith("_core"):
        return archive_stem[: -len("_core")]
    if "_core_" in archive_stem:
        return archive_stem.split("_core_", 1)[0]
    if "_spatial_" in archive_stem:
        return archive_stem.split("_spatial_", 1)[0]
    return archive_stem


# Coleta ZIPs dentro de cada certificadora da camada.
# Ignora ZIPs que ja possuem pasta correspondente descompactada.
def find_archives(layer_dir: Path, standard: str | None, date: str | None) -> list[Path]:
    archives: list[Path] = []
    if not layer_dir.exists():
        return archives
    for standard_dir in sorted(layer_dir.iterdir()):
        if not standard_dir.is_dir():
            continue
        if standard and standard_dir.name != standard:
            continue

        seen_snapshot_names: set[str] = set()
        for zip_path in sorted(standard_dir.glob("*.zip")):
            snapshot_name = extract_snapshot_name_from_archive_name(zip_path.stem)
            if not snapshot_name:
                continue
            if date and snapshot_name != date:
                continue
            if snapshot_name in seen_snapshot_names:
                continue
            folder_path = zip_path.parent / snapshot_name
            if folder_path.exists():
                continue
            core_zip_path = zip_path.parent / f"{snapshot_name}_core.zip"
            core_part_paths = sorted(zip_path.parent.glob(f"{snapshot_name}_core_*.zip"))
            if core_zip_path.exists():
                archives.append(core_zip_path)
            elif core_part_paths:
                archives.append(core_part_paths[0])
            else:
                archives.append(zip_path)
            seen_snapshot_names.add(snapshot_name)
    return archives


# Coleta pastas compactaveis dentro da gold (ex: projects/).
# Ignora pastas que ja possuem ZIP correspondente.
def find_gold_targets() -> list[Path]:
    targets: list[Path] = []
    gold_dir = LAYER_DIRS["gold"]
    if not gold_dir.exists():
        return targets
    for subdir in sorted(gold_dir.iterdir()):
        if not subdir.is_dir():
            continue
        if subdir.name == "backup":
            continue
        zip_path = gold_dir / f"{subdir.name}.zip"
        if zip_path.exists():
            continue
        targets.append(subdir)
    return targets


# Coleta ZIPs dentro da gold.
# Ignora ZIPs que ja possuem pasta correspondente descompactada.
def find_gold_archives() -> list[Path]:
    gold_dir = LAYER_DIRS["gold"]
    if not gold_dir.exists():
        return []
    archives = []
    for zip_path in sorted(gold_dir.glob("*.zip")):
        folder_path = gold_dir / zip_path.stem
        if folder_path.exists():
            continue
        archives.append(zip_path)
    return archives


# Retorna o caminho relativo a partir da raiz do projeto.
def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


# Lista arquivos relativos abaixo do diretorio alvo.
def list_relative_files(target_dir: Path) -> list[Path]:
    return sorted(path.relative_to(target_dir) for path in target_dir.rglob("*") if path.is_file())


# Soma o tamanho de uma lista de arquivos relativos ao diretorio alvo.
def compute_relative_files_size(target_dir: Path, relative_paths: list[Path]) -> int:
    return sum((target_dir / relative_path).stat().st_size for relative_path in relative_paths)


# Escreve um ZIP com os arquivos relativos informados.
def write_zip_from_relative_files(target_dir: Path, zip_path: Path, relative_paths: list[Path]) -> int:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for relative_path in relative_paths:
            file_path = target_dir / relative_path
            zf.write(file_path, relative_path.as_posix())
    return zip_path.stat().st_size


# Quebra uma lista de arquivos relativos em partes limitadas por tamanho bruto acumulado.
def partition_relative_paths_by_size(
    target_dir: Path,
    relative_paths: list[Path],
    *,
    max_part_bytes: int,
    label: str,
) -> list[tuple[list[Path], int]]:
    if max_part_bytes <= 0:
        raise ValueError("max_part_bytes deve ser maior que zero.")

    partitions: list[tuple[list[Path], int]] = []
    current_paths: list[Path] = []
    current_size = 0

    def flush_partition() -> None:
        nonlocal current_paths, current_size
        if not current_paths:
            return
        partitions.append((current_paths, current_size))
        current_paths = []
        current_size = 0

    for relative_path in relative_paths:
        file_size = (target_dir / relative_path).stat().st_size
        if file_size > max_part_bytes:
            raise ValueError(
                f"Arquivo excede o limite por parte em {label}: "
                f"{rel(target_dir / relative_path)} tem {format_size(file_size)} "
                f"e o teto configurado e {format_size(max_part_bytes)}."
            )
        if current_paths and current_size + file_size > max_part_bytes:
            flush_partition()
        current_paths.append(relative_path)
        current_size += file_size

    flush_partition()
    return partitions


# Remove o diretorio alvo com retry para conviver melhor com locks transitorios no Windows.
def remove_directory_with_retries(
    target_dir: Path,
    *,
    retry_attempts: int = DEFAULT_REMOVE_RETRY_ATTEMPTS,
    retry_sleep_seconds: float = DEFAULT_REMOVE_RETRY_SLEEP_SECONDS,
) -> None:
    attempts_total = retry_attempts + 1
    attempt = 1
    while True:
        try:
            shutil.rmtree(target_dir)
            return
        except OSError:
            if attempt >= attempts_total:
                raise
            time.sleep(retry_sleep_seconds)
            attempt += 1


# Extrai um ZIP no diretorio alvo preservando os caminhos internos.
def extract_zip_to_dir(zip_path: Path, target_dir: Path) -> tuple[int, int]:
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(target_dir)
        file_count = sum(1 for info in zf.infolist() if not info.is_dir())
    restored_size = sum(path.stat().st_size for path in target_dir.rglob("*") if path.is_file())
    return file_count, restored_size


# Verifica se o snapshot possui pasta spatial com arquivos a particionar.
def snapshot_has_spatial_files(
    target_dir: Path,
    *,
    spatial_subdir_name: str = DEFAULT_SPATIAL_SUBDIR_NAME,
) -> bool:
    spatial_dir = target_dir / spatial_subdir_name
    return spatial_dir.exists() and any(path.is_file() for path in spatial_dir.rglob("*"))


# Compacta uma pasta inteira em ZIP e remove a pasta original.
def pack_directory(target_dir: Path, label: str, step: int, total: int) -> tuple[Path, int, int]:
    zip_path = target_dir.parent / f"{target_dir.name}.zip"
    relative_paths = list_relative_files(target_dir)
    original_size = compute_relative_files_size(target_dir, relative_paths)

    print(f"  [{step}/{total}] packing: {rel(target_dir)}")
    print(f"         {len(relative_paths)} files, {format_size(original_size)}")

    zip_size = write_zip_from_relative_files(target_dir, zip_path, relative_paths)
    ratio = (1 - zip_size / original_size) * 100 if original_size > 0 else 0
    print(f"         -> {rel(zip_path)}: {format_size(zip_size)} ({ratio:.0f}% reduction)")
    print("         done.")

    remove_directory_with_retries(target_dir)
    return zip_path, original_size, zip_size


# Compacta um snapshot em bundle core + partes espaciais e remove a pasta original.
def pack_snapshot_bundle(
    target_dir: Path,
    *,
    label: str,
    step: int,
    total: int,
    spatial_subdir_name: str = DEFAULT_SPATIAL_SUBDIR_NAME,
    spatial_part_max_bytes: int = DEFAULT_SPATIAL_PART_MAX_BYTES,
) -> tuple[list[Path], int, int]:
    if spatial_part_max_bytes <= 0:
        raise ValueError("spatial_part_max_bytes deve ser maior que zero.")

    all_relative_paths = list_relative_files(target_dir)
    spatial_prefix = Path(spatial_subdir_name)
    core_relative_paths = [path for path in all_relative_paths if spatial_prefix not in path.parents and path != spatial_prefix]
    spatial_relative_paths = [path for path in all_relative_paths if spatial_prefix in path.parents]
    original_size = compute_relative_files_size(target_dir, all_relative_paths)

    print(f"  [{step}/{total}] packing bundle: {rel(target_dir)}")
    print(
        "         "
        f"{len(core_relative_paths)} core files + {len(spatial_relative_paths)} spatial files, "
        f"{format_size(original_size)} total"
    )

    created_archives: list[Path] = []
    total_zip_size = 0

    core_partitions = partition_relative_paths_by_size(
        target_dir,
        core_relative_paths,
        max_part_bytes=spatial_part_max_bytes,
        label="core",
    )
    use_numbered_core_parts = len(core_partitions) > 1
    for core_index, (core_paths, core_raw_size) in enumerate(core_partitions, start=1):
        if use_numbered_core_parts:
            core_zip_path = target_dir.parent / f"{target_dir.name}_core_{core_index:03d}.zip"
        else:
            core_zip_path = target_dir.parent / f"{target_dir.name}_core.zip"
        core_zip_size = write_zip_from_relative_files(target_dir, core_zip_path, core_paths)
        created_archives.append(core_zip_path)
        total_zip_size += core_zip_size
        print(
            "         -> "
            f"{rel(core_zip_path)}: {len(core_paths)} files, {format_size(core_zip_size)} "
            f"(raw {format_size(core_raw_size)})"
        )

    if spatial_relative_paths:
        spatial_partitions = partition_relative_paths_by_size(
            target_dir,
            spatial_relative_paths,
            max_part_bytes=spatial_part_max_bytes,
            label="spatial",
        )
        for part_index, (current_part_paths, current_part_size) in enumerate(spatial_partitions, start=1):
            part_path = target_dir.parent / f"{target_dir.name}_spatial_{part_index:03d}.zip"
            part_zip_size = write_zip_from_relative_files(target_dir, part_path, current_part_paths)
            created_archives.append(part_path)
            total_zip_size += part_zip_size
            print(
                "         -> "
                f"{rel(part_path)}: {len(current_part_paths)} files, {format_size(part_zip_size)} "
                f"(raw {format_size(current_part_size)})"
            )

    ratio = (1 - total_zip_size / original_size) * 100 if original_size > 0 else 0
    print(
        "         done: "
        f"{len(created_archives)} archive(s), {format_size(total_zip_size)} total ({ratio:.0f}% reduction)"
    )

    remove_directory_with_retries(target_dir)
    return created_archives, original_size, total_zip_size


# Descompacta um ZIP no diretorio correto e remove o ZIP.
def unpack_archive(zip_path: Path, label: str, step: int, total: int) -> tuple[Path, int]:
    target_dir = zip_path.parent / zip_path.stem
    zip_size = zip_path.stat().st_size
    print(f"  [{step}/{total}] unpacking: {rel(zip_path)}")
    print(f"         zip size: {format_size(zip_size)}")

    if target_dir.exists():
        print(f"         WARNING: {rel(target_dir)} already exists, skipping")
        return target_dir, 0

    target_dir.mkdir(parents=True, exist_ok=True)
    file_count, restored_size = extract_zip_to_dir(zip_path, target_dir)
    print(f"         -> {rel(target_dir)}: {file_count} files restored, {format_size(restored_size)}")
    print("         done.")

    zip_path.unlink()
    return target_dir, file_count


# Descompacta um snapshot salvo em bundle core + partes espaciais.
def unpack_snapshot_bundle(
    snapshot_parent_dir: Path,
    snapshot_name: str,
    *,
    label: str,
    step: int,
    total: int,
) -> tuple[Path, int]:
    target_dir = snapshot_parent_dir / snapshot_name
    legacy_zip_path = snapshot_parent_dir / f"{snapshot_name}.zip"
    core_zip_path = snapshot_parent_dir / f"{snapshot_name}_core.zip"
    core_part_paths = sorted(snapshot_parent_dir.glob(f"{snapshot_name}_core_*.zip"))
    spatial_zip_paths = sorted(snapshot_parent_dir.glob(f"{snapshot_name}_spatial_*.zip"))

    if target_dir.exists():
        print(f"  [{step}/{total}] unpacking bundle: {rel(target_dir)}")
        print(f"         WARNING: {rel(target_dir)} already exists, skipping")
        return target_dir, 0

    if legacy_zip_path.exists():
        return unpack_archive(legacy_zip_path, label=label, step=step, total=total)

    if not core_zip_path.exists() and not core_part_paths:
        raise FileNotFoundError(f"Bundle core nao encontrado para snapshot {snapshot_name}")

    bundle_paths = ([core_zip_path] if core_zip_path.exists() else core_part_paths) + spatial_zip_paths
    total_zip_size = sum(path.stat().st_size for path in bundle_paths)
    first_bundle_path = bundle_paths[0]
    print(f"  [{step}/{total}] unpacking bundle: {rel(first_bundle_path)}")
    print(
        "         "
        f"{len(bundle_paths)} archive(s), zip size total: {format_size(total_zip_size)}"
    )

    target_dir.mkdir(parents=True, exist_ok=True)
    total_files = 0
    restored_size = 0
    for bundle_path in bundle_paths:
        file_count, _ = extract_zip_to_dir(bundle_path, target_dir)
        total_files += file_count
        bundle_path.unlink()

    restored_size = sum(path.stat().st_size for path in target_dir.rglob("*") if path.is_file())
    print(f"         -> {rel(target_dir)}: {total_files} files restored, {format_size(restored_size)}")
    print("         done.")
    return target_dir, total_files


# Lista no terminal os itens que serao processados antes de iniciar.
def print_plan(action: str, items: list[Path], layer: str) -> None:
    print(f"\n  {len(items)} item(s) to {action}:")
    for item in items:
        print(f"    - {rel(item)}")
    print()


# Executa --pack para bronze ou silver (estrutura certificadora/YYYYMMDD).
def run_pack_standard_layer(layer: str, standard: str | None, date: str | None) -> int:
    layer_dir = LAYER_DIRS[layer]
    snapshots = find_snapshots(layer_dir, standard, date)
    if not snapshots:
        print(f"no {layer} snapshots found matching filters")
        return 0

    print_plan("pack", snapshots, layer)
    total_original = 0
    total_compressed = 0
    count = len(snapshots)

    for i, snapshot_dir in enumerate(snapshots, start=1):
        label = f"{snapshot_dir.parent.name}/{snapshot_dir.name}"
        if snapshot_has_spatial_files(snapshot_dir):
            _, original_size, zip_size = pack_snapshot_bundle(snapshot_dir, label=label, step=i, total=count)
        else:
            _, original_size, zip_size = pack_directory(snapshot_dir, label, i, count)
        total_original += original_size
        total_compressed += zip_size

    ratio = (1 - total_compressed / total_original) * 100 if total_original > 0 else 0
    print(f"\n  {layer} summary: {format_size(total_original)} -> {format_size(total_compressed)} ({ratio:.0f}% reduction)")
    return 0


# Executa --unpack para bronze ou silver (estrutura certificadora/YYYYMMDD).
def run_unpack_standard_layer(layer: str, standard: str | None, date: str | None) -> int:
    layer_dir = LAYER_DIRS[layer]
    archives = find_archives(layer_dir, standard, date)
    if not archives:
        print(f"no {layer} archives found matching filters")
        return 0

    print_plan("unpack", archives, layer)
    total_files = 0
    count = len(archives)

    for i, zip_path in enumerate(archives, start=1):
        snapshot_name = extract_snapshot_name_from_archive_name(zip_path.stem) or zip_path.stem
        label = f"{zip_path.parent.name}/{snapshot_name}"
        if zip_path.stem.endswith("_core") or "_core_" in zip_path.stem:
            _, file_count = unpack_snapshot_bundle(
                zip_path.parent,
                snapshot_name,
                label=label,
                step=i,
                total=count,
            )
        else:
            _, file_count = unpack_archive(zip_path, label, i, count)
        total_files += file_count

    print(f"\n  {layer} summary: {total_files} files restored")
    return 0


# Executa --pack para a gold (estrutura direta, sem certificadora/data).
def run_pack_gold() -> int:
    targets = find_gold_targets()
    if not targets:
        print("no gold directories found to pack")
        return 0

    print_plan("pack", targets, "gold")
    total_original = 0
    total_compressed = 0
    count = len(targets)

    for i, target_dir in enumerate(targets, start=1):
        label = f"gold/{target_dir.name}"
        _, original_size, zip_size = pack_directory(target_dir, label, i, count)
        total_original += original_size
        total_compressed += zip_size

    ratio = (1 - total_compressed / total_original) * 100 if total_original > 0 else 0
    print(f"\n  gold summary: {format_size(total_original)} -> {format_size(total_compressed)} ({ratio:.0f}% reduction)")
    return 0


# Executa --unpack para a gold.
def run_unpack_gold() -> int:
    archives = find_gold_archives()
    if not archives:
        print("no gold archives found")
        return 0

    print_plan("unpack", archives, "gold")
    total_files = 0
    count = len(archives)

    for i, zip_path in enumerate(archives, start=1):
        label = f"gold/{zip_path.stem}"
        _, file_count = unpack_archive(zip_path, label, i, count)
        total_files += file_count

    print(f"\n  gold summary: {total_files} files restored")
    return 0


# Monta o parser de argumentos CLI.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compacta ou descompacta snapshots de dados (bronze, silver, gold) para o repositorio Git."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pack", action="store_true", help="Compactar snapshots em ZIP e remover originais.")
    group.add_argument("--unpack", action="store_true", help="Descompactar ZIPs e remover arquivos ZIP.")
    parser.add_argument(
        "--layer",
        type=str,
        choices=["bronze", "silver", "gold", "all"],
        default="all",
        help="Camada a processar (default: all).",
    )
    parser.add_argument("--standard", type=str, default=None, help="Filtrar por certificadora (ex: verra). Ignorado para gold.")
    parser.add_argument("--date", type=str, default=None, help="Filtrar por snapshot YYYYMMDD (ex: 20260325). Ignorado para gold.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    layers = ["bronze", "silver", "gold"] if args.layer == "all" else [args.layer]

    for layer in layers:
        print(f"=== {layer.upper()} ===")
        if layer == "gold":
            if args.pack:
                run_pack_gold()
            else:
                run_unpack_gold()
        else:
            if args.pack:
                run_pack_standard_layer(layer, args.standard, args.date)
            else:
                run_unpack_standard_layer(layer, args.standard, args.date)
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
