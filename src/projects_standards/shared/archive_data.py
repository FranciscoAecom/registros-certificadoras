# Objetivo do script:
# Compactar e descompactar snapshots de dados (bronze, silver, gold) para reduzir o tamanho no repositório Git.
# Processo:
# 1. Ler argumentos CLI (--pack ou --unpack, --layer, --standard opcional, --date opcional).
# 2. Resolver o diretório base da camada selecionada.
# 3. Localizar snapshots ou ZIPs que atendam aos filtros.
# 4. --pack: compactar cada snapshot YYYYMMDD em um ZIP e remover a pasta original.
# 5. --unpack: descompactar cada ZIP no diretório correto e remover o ZIP.
# 6. Para gold, compactar/descompactar a pasta projects/ diretamente.
# 7. Exibir relatório de progresso no terminal.

from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parents[2]
DATA_BASE_DIR = ROOT_DIR / 'data' / 'project_standards'

LAYER_DIRS = {
    'bronze': DATA_BASE_DIR / '01_bronze',
    'silver': DATA_BASE_DIR / '02_silver',
    'gold': DATA_BASE_DIR / '03_gold',
}


# Formata tamanho em bytes para exibição legível.
def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f'{size_bytes} B'
    if size_bytes < 1024 * 1024:
        return f'{size_bytes / 1024:.1f} KB'
    return f'{size_bytes / (1024 * 1024):.1f} MB'


# Coleta snapshots (pastas YYYYMMDD) dentro de cada certificadora da camada.
# Ignora pastas que ja possuem ZIP correspondente.
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
            zip_path = snapshot_dir.parent / f'{snapshot_dir.name}.zip'
            if zip_path.exists():
                continue
            snapshots.append(snapshot_dir)
    return snapshots


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
        for zip_path in sorted(standard_dir.glob('*.zip')):
            snapshot_name = zip_path.stem
            if date and snapshot_name != date:
                continue
            folder_path = zip_path.parent / snapshot_name
            if folder_path.exists():
                continue
            archives.append(zip_path)
    return archives


# Coleta pastas compactáveis dentro da gold (ex: projects/).
# Ignora pastas que ja possuem ZIP correspondente.
def find_gold_targets() -> list[Path]:
    targets: list[Path] = []
    gold_dir = LAYER_DIRS['gold']
    if not gold_dir.exists():
        return targets
    for subdir in sorted(gold_dir.iterdir()):
        if not subdir.is_dir():
            continue
        # Ignora pasta de backup
        if subdir.name == 'backup':
            continue
        zip_path = gold_dir / f'{subdir.name}.zip'
        if zip_path.exists():
            continue
        targets.append(subdir)
    return targets


# Coleta ZIPs dentro da gold.
# Ignora ZIPs que ja possuem pasta correspondente descompactada.
def find_gold_archives() -> list[Path]:
    gold_dir = LAYER_DIRS['gold']
    if not gold_dir.exists():
        return []
    archives = []
    for zip_path in sorted(gold_dir.glob('*.zip')):
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


# Compacta uma pasta inteira em ZIP e remove a pasta original.
def pack_directory(target_dir: Path, label: str, step: int, total: int) -> tuple[Path, int, int]:
    zip_path = target_dir.parent / f'{target_dir.name}.zip'

    all_files = sorted(f for f in target_dir.rglob('*') if f.is_file())
    original_size = sum(f.stat().st_size for f in all_files)

    print(f'  [{step}/{total}] packing: {rel(target_dir)}')
    print(f'         {len(all_files)} files, {format_size(original_size)}')

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for file_path in all_files:
            arcname = file_path.relative_to(target_dir).as_posix()
            zf.write(file_path, arcname)

    zip_size = zip_path.stat().st_size
    ratio = (1 - zip_size / original_size) * 100 if original_size > 0 else 0
    print(f'         -> {rel(zip_path)}: {format_size(zip_size)} ({ratio:.0f}% reduction)')
    print(f'         done.')

    shutil.rmtree(target_dir)
    return zip_path, original_size, zip_size


# Descompacta um ZIP no diretório correto e remove o ZIP.
def unpack_archive(zip_path: Path, label: str, step: int, total: int) -> tuple[Path, int]:
    target_dir = zip_path.parent / zip_path.stem

    zip_size = zip_path.stat().st_size
    print(f'  [{step}/{total}] unpacking: {rel(zip_path)}')
    print(f'         zip size: {format_size(zip_size)}')

    if target_dir.exists():
        print(f'         WARNING: {rel(target_dir)} already exists, skipping')
        return target_dir, 0

    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(target_dir)

    file_count = sum(1 for f in target_dir.rglob('*') if f.is_file())
    restored_size = sum(f.stat().st_size for f in target_dir.rglob('*') if f.is_file())
    print(f'         -> {rel(target_dir)}: {file_count} files restored, {format_size(restored_size)}')
    print(f'         done.')

    zip_path.unlink()
    return target_dir, file_count


# Lista no terminal os itens que serao processados antes de iniciar.
def print_plan(action: str, items: list[Path], layer: str) -> None:
    print(f'\n  {len(items)} item(s) to {action}:')
    for item in items:
        print(f'    - {rel(item)}')
    print()


# Executa --pack para bronze ou silver (estrutura certificadora/YYYYMMDD).
def run_pack_standard_layer(layer: str, standard: str | None, date: str | None) -> int:
    layer_dir = LAYER_DIRS[layer]
    snapshots = find_snapshots(layer_dir, standard, date)
    if not snapshots:
        print(f'no {layer} snapshots found matching filters')
        return 0

    print_plan('pack', snapshots, layer)
    total_original = 0
    total_compressed = 0
    count = len(snapshots)

    for i, snapshot_dir in enumerate(snapshots, start=1):
        label = f'{snapshot_dir.parent.name}/{snapshot_dir.name}'
        _, original_size, zip_size = pack_directory(snapshot_dir, label, i, count)
        total_original += original_size
        total_compressed += zip_size

    ratio = (1 - total_compressed / total_original) * 100 if total_original > 0 else 0
    print(f'\n  {layer} summary: {format_size(total_original)} -> {format_size(total_compressed)} ({ratio:.0f}% reduction)')
    return 0


# Executa --unpack para bronze ou silver (estrutura certificadora/YYYYMMDD).
def run_unpack_standard_layer(layer: str, standard: str | None, date: str | None) -> int:
    layer_dir = LAYER_DIRS[layer]
    archives = find_archives(layer_dir, standard, date)
    if not archives:
        print(f'no {layer} archives found matching filters')
        return 0

    print_plan('unpack', archives, layer)
    total_files = 0
    count = len(archives)

    for i, zip_path in enumerate(archives, start=1):
        label = f'{zip_path.parent.name}/{zip_path.stem}'
        _, file_count = unpack_archive(zip_path, label, i, count)
        total_files += file_count

    print(f'\n  {layer} summary: {total_files} files restored')
    return 0


# Executa --pack para a gold (estrutura direta, sem certificadora/data).
def run_pack_gold() -> int:
    targets = find_gold_targets()
    if not targets:
        print('no gold directories found to pack')
        return 0

    print_plan('pack', targets, 'gold')
    total_original = 0
    total_compressed = 0
    count = len(targets)

    for i, target_dir in enumerate(targets, start=1):
        label = f'gold/{target_dir.name}'
        _, original_size, zip_size = pack_directory(target_dir, label, i, count)
        total_original += original_size
        total_compressed += zip_size

    ratio = (1 - total_compressed / total_original) * 100 if total_original > 0 else 0
    print(f'\n  gold summary: {format_size(total_original)} -> {format_size(total_compressed)} ({ratio:.0f}% reduction)')
    return 0


# Executa --unpack para a gold.
def run_unpack_gold() -> int:
    archives = find_gold_archives()
    if not archives:
        print('no gold archives found')
        return 0

    print_plan('unpack', archives, 'gold')
    total_files = 0
    count = len(archives)

    for i, zip_path in enumerate(archives, start=1):
        label = f'gold/{zip_path.stem}'
        _, file_count = unpack_archive(zip_path, label, i, count)
        total_files += file_count

    print(f'\n  gold summary: {total_files} files restored')
    return 0


# Monta o parser de argumentos CLI.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Compacta ou descompacta snapshots de dados (bronze, silver, gold) para o repositório Git.'
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--pack', action='store_true', help='Compactar snapshots em ZIP e remover originais.')
    group.add_argument('--unpack', action='store_true', help='Descompactar ZIPs e remover arquivos ZIP.')
    parser.add_argument('--layer', type=str, choices=['bronze', 'silver', 'gold', 'all'], default='all',
                        help='Camada a processar (default: all).')
    parser.add_argument('--standard', type=str, default=None,
                        help='Filtrar por certificadora (ex: verra). Ignorado para gold.')
    parser.add_argument('--date', type=str, default=None,
                        help='Filtrar por snapshot YYYYMMDD (ex: 20260325). Ignorado para gold.')
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    layers = ['bronze', 'silver', 'gold'] if args.layer == 'all' else [args.layer]

    for layer in layers:
        print(f'=== {layer.upper()} ===')
        if layer == 'gold':
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


if __name__ == '__main__':
    raise SystemExit(main())
