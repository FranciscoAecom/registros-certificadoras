# Objetivo do script:
# Analisar os arquivos bronze da Gold Standard e gerar um mapeamento inicial entre o bruto e o schema canonico da camada silver.
# Processo:
# 1. Ler argumentos CLI (--date, --output, --sample-fraction, --limit).
# 2. Carregar amostra hibrida de arquivos bronze do snapshot (maiores + aleatorios).
# 3. Inspecionar campos presentes em list_data e detail_data de cada arquivo.
# 4. Mapear campos bronze para o schema canonico silver com regras de extracao.
# 5. Calcular cobertura percentual de cada campo candidato na amostra.
# 6. Gerar relatorio de mapeamento em JSON ou Markdown.


import argparse
import json
import math
import random
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


ROOT_DIR = Path(__file__).resolve().parents[4]
GUIDE_PATH = ROOT_DIR / "docs" / "agentes" / "guia_silver.md"
DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent / "docs" / "silver_field_mapping.md"
DEFAULT_SAMPLE_FRACTION = 0.10
DEFAULT_SAMPLE_MIN_FILES = 10
DEFAULT_SAMPLE_LARGEST_RATIO = 0.50


@dataclass(frozen=True)
class FieldSpec:
    section: str
    name: str


@dataclass(frozen=True)
class CandidateSource:
    source_section: str
    source_path: str
    rule_type: str
    notes: str
    extractor: Callable[[dict[str, Any], Path], Any]


# Define e retorna os argumentos de linha de comando do script.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analisa os arquivos bronze da Gold Standard e gera um mapeamento inicial para a camada silver."
    )
    parser.add_argument("--date", required=True, help="Data de referencia no formato YYYYMMDD.")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help=f"Arquivo Markdown de saida. Padrao: {DEFAULT_OUTPUT_PATH}",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limita a quantidade de arquivos de detalhe para testes.")
    parser.add_argument(
        "--sample-fraction",
        type=float,
        default=DEFAULT_SAMPLE_FRACTION,
        help=f"Fracao minima de arquivos de detalhe usada na amostra aleatoria do mapeamento. Padrao: {DEFAULT_SAMPLE_FRACTION}.",
    )
    parser.add_argument(
        "--sample-min-files",
        type=int,
        default=DEFAULT_SAMPLE_MIN_FILES,
        help=f"Quantidade minima de arquivos na amostra do mapeamento. Padrao: {DEFAULT_SAMPLE_MIN_FILES}.",
    )
    parser.add_argument(
        "--sample-seed",
        type=int,
        default=None,
        help="Seed opcional para a amostra aleatoria. Padrao: usa a data do snapshot.",
    )
    parser.add_argument(
        "--sample-largest-ratio",
        type=float,
        default=DEFAULT_SAMPLE_LARGEST_RATIO,
        help=(
            "Fracao da amostra reservada para os maiores arquivos do snapshot. "
            f"Padrao: {DEFAULT_SAMPLE_LARGEST_RATIO}."
        ),
    )
    return parser.parse_args()


# Valida a data informada e garante o formato YYYYMMDD.
def validate_date(value: str) -> str:
    if not re.fullmatch(r"\d{8}", value):
        raise SystemExit(f"--date invalida: {value}. Use YYYYMMDD.")
    return value


# Le o guia da camada silver e extrai a ordem canonica dos campos.
def parse_guide_fields(guide_path: Path) -> list[FieldSpec]:
    lines = guide_path.read_text(encoding="utf-8").splitlines()
    in_structure = False
    current_section = ""
    fields: list[FieldSpec] = []

    for line in lines:
        if line.startswith("## "):
            if line.strip() == "## Estrutura Canonica Recomendada":
                in_structure = True
                continue
            if in_structure:
                break

        if not in_structure:
            continue

        if line.startswith("### "):
            current_section = re.sub(r"^\d+\.\s*", "", line[4:].strip())
            continue

        match = re.match(r"- `([^`]+)`", line.strip())
        if match and current_section:
            fields.append(FieldSpec(section=current_section, name=match.group(1)))

    if not fields:
        raise SystemExit(f"Nenhum campo encontrado em {guide_path}")
    return fields


# Monta os caminhos de entrada e saida usados pelo script.
def build_paths(snapshot_date: str) -> tuple[Path, Path]:
    bronze_dir = ROOT_DIR / "data" / "project_standards" / "01_bronze" / "gold_standard" / snapshot_date
    list_path = bronze_dir / "list" / "projects.json"
    projects_dir = bronze_dir / "projects"
    return list_path, projects_dir


# Calcula o tamanho minimo da amostra aleatoria do mapeamento.
def calculate_sample_size(total_files: int, sample_fraction: float, sample_min_files: int) -> int:
    if total_files <= 0:
        return 0
    if total_files <= sample_min_files:
        return total_files
    return min(total_files, max(sample_min_files, math.ceil(total_files * sample_fraction)))


# Seleciona uma amostra aleatoria deterministica dos arquivos disponiveis para o mapeamento.
def select_sample_files(
    detail_files: list[Path],
    snapshot_date: str,
    sample_fraction: float,
    sample_min_files: int,
    sample_seed: int | None,
    sample_largest_ratio: float,
) -> tuple[list[Path], int, int, int]:
    sample_size = calculate_sample_size(
        total_files=len(detail_files),
        sample_fraction=sample_fraction,
        sample_min_files=sample_min_files,
    )
    largest_count = min(sample_size, math.ceil(sample_size * sample_largest_ratio))
    random_count = max(0, sample_size - largest_count)
    effective_seed = sample_seed if sample_seed is not None else int(snapshot_date)

    if sample_size >= len(detail_files):
        return detail_files, effective_seed, len(detail_files), 0

    files_by_size = sorted(
        detail_files,
        key=lambda path: (-path.stat().st_size, int(path.stem)),
    )
    largest_files = files_by_size[:largest_count]
    remaining_files = [path for path in detail_files if path not in set(largest_files)]
    rng = random.Random(effective_seed)
    random_files: list[Path] = []
    if random_count > 0 and remaining_files:
        random_files = rng.sample(remaining_files, min(random_count, len(remaining_files)))

    sampled = sorted({*largest_files, *random_files}, key=lambda path: int(path.stem))
    return sampled, effective_seed, len(largest_files), len(random_files)


# Carrega um arquivo JSON e valida a estrutura esperada.
def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"JSON invalido em {path}")
    return payload


# Percorre um caminho com notacao por ponto dentro do payload.
def get_path(payload: dict[str, Any], dotted_path: str) -> Any:
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


# Deriva o nome do arquivo de detalhe a partir do caminho no filesystem.
def derive_file_name(_: dict[str, Any], file_path: Path) -> str:
    return file_path.name


# Deriva o caminho relativo do arquivo de detalhe no filesystem.
def derive_file_path(_: dict[str, Any], file_path: Path) -> str:
    return str(file_path.relative_to(ROOT_DIR)).replace("\\", "/")


# Remove valores vazios e duplicados preservando a ordem original.
def unique_non_empty(values: list[Any]) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for value in values:
        if value in (None, "", [], {}):
            continue
        key = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


# Garante que o valor seja tratado como lista para regras com multiplicidade.
def ensure_list(value: Any) -> list[Any]:
    if value in (None, "", [], {}):
        return []
    if isinstance(value, list):
        return unique_non_empty(value)
    return [value]


# Retorna um valor unico ou uma lista, conforme a quantidade encontrada.
def scalar_or_list(values: list[Any]) -> Any:
    clean_values = unique_non_empty(values)
    if not clean_values:
        return None
    if len(clean_values) == 1:
        return clean_values[0]
    return clean_values


# Extrai o prefixo de codigo da metodologia quando ele estiver presente no texto.
def extract_methodology_code(value: Any) -> Any:
    if value in (None, ""):
        return None
    values = ensure_list(value)
    codes: list[str] = []
    for item in values:
        text = str(item).strip()
        match = re.match(r"^([A-Z]{2,}(?:[-_.][A-Z0-9]+)+|[A-Z]{2,}\d{3,})\b", text)
        if match:
            codes.append(match.group(1))
    return scalar_or_list(codes)


# Extrai os nomes dos ODS a partir do payload bruto da Gold Standard.
def extract_sdg_targets(value: Any) -> Any:
    if not isinstance(value, list):
        return None
    names = [item.get("name") for item in value if isinstance(item, dict) and item.get("name")]
    return scalar_or_list(names)


# Combina programa e labels para construir um conjunto de subcategorias uteis.
def extract_project_subcategories(programme_of_activities: Any, labels: Any) -> Any:
    combined: list[Any] = []
    combined.extend(ensure_list(programme_of_activities))
    combined.extend(ensure_list(labels))
    return scalar_or_list(combined)


# Soma os totais do credits_summary para um status especifico do projeto.
def extract_credits_summary_total(value: Any, target_status: str) -> Any:
    if not isinstance(value, list):
        return None

    total = 0
    found = False
    for product_summary in value:
        if not isinstance(product_summary, dict):
            continue
        summary_items = product_summary.get("summary")
        if not isinstance(summary_items, list):
            continue
        for summary_item in summary_items:
            if not isinstance(summary_item, dict):
                continue
            if str(summary_item.get("status") or "").upper() != target_status.upper():
                continue
            current_total = summary_item.get("total")
            if current_total in (None, ""):
                continue
            total += int(str(current_total).replace(",", ""))
            found = True
    return total if found else None


# Trata todos os status da Gold Standard como voluntarios ate nova definicao canonica.
def extract_voluntary_status(status: Any) -> Any:
    if status in (None, ""):
        return None
    return status


# Monta as fontes candidatas usadas no mapeamento inicial da silver.
def build_candidate_sources() -> dict[str, list[CandidateSource]]:
    def path(source_section: str, source_path: str, rule_type: str = "direct", notes: str = "") -> CandidateSource:
        return CandidateSource(
            source_section=source_section,
            source_path=source_path,
            rule_type=rule_type,
            notes=notes,
            extractor=lambda payload, _file_path, p=f"{source_section}.{source_path}" if source_section != "file_system" else source_path: (
                derive_file_name(payload, _file_path)
                if p == "source_file_name"
                else derive_file_path(payload, _file_path)
                if p == "bronze_file_path"
                else get_path(payload, p)
            ),
        )

    def transformed(
        source_section: str,
        source_path: str,
        transform: Callable[[Any], Any],
        notes: str,
        rule_type: str,
    ) -> CandidateSource:
        return CandidateSource(
            source_section=source_section,
            source_path=source_path,
            rule_type=rule_type,
            notes=notes,
            extractor=lambda payload, _file_path, p=f"{source_section}.{source_path}", fn=transform: fn(get_path(payload, p)),
        )

    return {
        "standard_name": [path("source", "carbon_standard", rule_type="rename")],
        "standard_acronym": [
            CandidateSource(
                source_section="reference",
                source_path="data/project_standards/00_reference/reference_dataset.xlsx (standards_catalog)",
                rule_type="lookup",
                notes="Deve ser obtido na referencia Certificadoras, a partir da certificadora do registro.",
                extractor=lambda payload, _file_path: "GS",
            )
        ],
        "project_public_id": [path("source", "project_public_id"), path("list_data", "id")],
        "project_internal_id": [path("source", "project_internal_id"), path("detail_data", "id")],
        "project_url": [path("source", "project_url")],
        "bronze_file_path": [
            CandidateSource(
                source_section="file_system",
                source_path="bronze_file_path",
                rule_type="derived",
                notes="Derivado do caminho do arquivo de detalhe no filesystem.",
                extractor=derive_file_path,
            )
        ],
        "source_file_name": [
            CandidateSource(
                source_section="file_system",
                source_path="source_file_name",
                rule_type="derived",
                notes="Derivado do nome do arquivo de detalhe no filesystem.",
                extractor=derive_file_name,
            )
        ],
        "project_name": [path("detail_data", "name"), path("list_data", "name")],
        "project_voluntary_status": [
            CandidateSource(
                source_section="list_data",
                source_path="status",
                rule_type="direct",
                notes="Regra canonica atual: ate segunda ordem, todo status bruto da Gold Standard deve ser tratado como voluntario, com fallback para detail_data.status.",
                extractor=lambda payload, _file_path: extract_voluntary_status(
                    get_path(payload, "list_data.status") or get_path(payload, "detail_data.status")
                ),
            )
        ],
        "project_regulatory_status": [
            CandidateSource(
                source_section="",
                source_path="",
                rule_type="unmapped",
                notes="Regra canonica atual: project_regulatory_status deve permanecer nulo para a Gold Standard ate revisao futura.",
                extractor=lambda payload, _file_path: None,
            )
        ],
        "standard_program": [path("list_data", "gsf_standards_version", rule_type="rename")],
        "project_description": [path("detail_data", "description", rule_type="rename")],
        "project_methodology": [path("detail_data", "methodology"), path("list_data", "methodology")],
        "project_type": [path("list_data", "type")],
        "sector": [],
        "project_category": [path("list_data", "size")],
        "project_subcategories": [
            CandidateSource(
                source_section="list_data",
                source_path="programme_of_activities + labels",
                rule_type="normalized",
                notes="Combina o enquadramento do projeto e labels expostos pela Gold Standard como subcategorias.",
                extractor=lambda payload, _file_path: extract_project_subcategories(
                    get_path(payload, "list_data.programme_of_activities"),
                    get_path(payload, "list_data.labels"),
                ),
            )
        ],
        "sdg_targets": [
            transformed(
                "list_data",
                "sustainable_development_goals",
                extract_sdg_targets,
                "Converte a lista de ODS da Gold Standard para uma lista canonica de nomes brutos.",
                "normalized",
            )
        ],
        "project_developer": [path("list_data", "project_developer")],
        "project_owner": [],
        "project_operator": [],
        "validator_name": [],
        "verifier_name": [],
        "country": [path("list_data", "country")],
        "state_or_region": [path("list_data", "state")],
        "city_or_locality": [],
        "location_latitude": [path("detail_data", "latitude"), path("list_data", "latitude")],
        "location_longitude": [path("detail_data", "longitude"), path("list_data", "longitude")],
        "snapshot_date": [path("source", "snapshot_date")],
        "reference_month": [path("source", "reference_month")],
        "registration_date": [],
        "status_date": [],
        "crediting_start_date": [path("list_data", "crediting_period_start_date")],
        "crediting_end_date": [path("list_data", "crediting_period_end_date")],
        "first_issuance_date": [],
        "last_issuance_date": [],
        "credits_issued_total": [
            transformed(
                "detail_data",
                "credits_summary",
                lambda value: extract_credits_summary_total(value, "ISSUED"),
                "Soma os totais com status ISSUED dentro de detail_data.credits_summary.",
                "aggregate",
            )
        ],
        "credits_retired_total": [
            transformed(
                "detail_data",
                "credits_summary",
                lambda value: extract_credits_summary_total(value, "RETIRED"),
                "Soma os totais com status RETIRED dentro de detail_data.credits_summary.",
                "aggregate",
            )
        ],
        "credits_cancelled_total": [],
        "credits_buffer_total": [],
        "estimated_annual_emission_reductions": [path("list_data", "estimated_annual_credits")],
        "estimated_total_emission_reductions": [],
        "area_hectares": [],
    }


# Escolhe a melhor fonte candidata para um campo com base na cobertura observada.
def find_best_candidate(
    records: list[tuple[Path, dict[str, Any]]], candidates: list[CandidateSource]
) -> tuple[CandidateSource | None, int, Any]:
    best_candidate: CandidateSource | None = None
    best_hits = -1
    best_example: Any = None

    for candidate in candidates:
        hits = 0
        example = None
        for file_path, payload in records:
            value = candidate.extractor(payload, file_path)
            if value not in (None, "", [], {}):
                hits += 1
                if example is None:
                    example = value
        if hits > best_hits:
            best_candidate = candidate
            best_hits = hits
            best_example = example

    return best_candidate, max(best_hits, 0), best_example


# Escapa valores para exibicao segura na tabela Markdown.
def markdown_escape(value: Any) -> str:
    if value is None:
        return ""
    text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 120:
        text = text[:117] + "..."
    return text.replace("|", "\\|")


# Resume a cobertura de mapeamento por secao do guia.
def summarize_sections(fields: list[FieldSpec], mapping_stats: dict[str, dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    section_counter: Counter[str] = Counter(field.section for field in fields)
    mapped_counter: Counter[str] = Counter()

    for field in fields:
        if mapping_stats[field.name]["status"] == "mapped":
            mapped_counter[field.section] += 1

    lines.append("| Secao | Campos | Campos com fonte inicial |")
    lines.append("| --- | ---: | ---: |")
    for section, total in section_counter.items():
        lines.append(f"| {section} | {total} | {mapped_counter.get(section, 0)} |")
    return lines


# Renderiza o relatorio de mapeamento em Markdown.
def render_markdown(
    *,
    snapshot_date: str,
    total_available_files: int,
    records: list[tuple[Path, dict[str, Any]]],
    fields: list[FieldSpec],
    mapping_stats: dict[str, dict[str, Any]],
    sample_fraction: float,
    sample_min_files: int,
    sample_seed: int,
    sample_largest_ratio: float,
    sample_largest_count: int,
    sample_random_count: int,
) -> str:
    lines: list[str] = []
    total = len(records)
    lines.append("# Mapeamento Inicial Silver da Gold Standard")
    lines.append("")
    lines.append(f"- Snapshot analisado: `{snapshot_date}`")
    lines.append(f"- Arquivos de detalhe disponiveis no snapshot: `{total_available_files}`")
    lines.append(f"- Arquivos de detalhe analisados na amostra: `{total}`")
    lines.append(f"- Regra de amostragem: `max({sample_min_files}, ceil({sample_fraction:.0%} do snapshot))`, com limite no total disponivel")
    lines.append(
        f"- Estrategia da amostra: `{sample_largest_count}` maiores arquivos "
        f"+ `{sample_random_count}` arquivos aleatorios "
        f"(proporcao alvo para maiores arquivos: {sample_largest_ratio:.0%})"
    )
    lines.append(f"- Seed da amostra aleatoria: `{sample_seed}`")
    lines.append(f"- Guia base: `{GUIDE_PATH.relative_to(ROOT_DIR).as_posix()}`")
    lines.append("")
    lines.append("## Resumo por Secao")
    lines.append("")
    lines.extend(summarize_sections(fields, mapping_stats))
    lines.append("")
    lines.append("## Tabela de Mapeamento Inicial")
    lines.append("")
    lines.append("| target_field | secao_guia | status | source_section | source_path | rule_type | cobertura | exemplo | notes |")
    lines.append("| --- | --- | --- | --- | --- | --- | ---: | --- | --- |")

    for field in fields:
        stats = mapping_stats[field.name]
        lines.append(
            f"| `{field.name}` | {field.section} | {stats['status']} | "
            f"{stats['source_section']} | `{stats['source_path']}` | {stats['rule_type']} | "
            f"{stats['coverage']} | {markdown_escape(stats['example'])} | {markdown_escape(stats['notes'])} |"
        )

    lines.append("")
    lines.append("## Observacoes")
    lines.append("")
    lines.append("- Este arquivo e um ponto de partida para refinarmos o mapeamento `bronze -> silver` da Gold Standard.")
    lines.append("- Campos com status `unmapped` ainda nao tiveram uma origem confiavel encontrada no bruto analisado.")
    lines.append("- Quando um campo permanecer sem origem confiavel no bruto da Gold Standard, ele deve seguir como `null` na `silver`.")
    lines.append("- Tratamento de completude, qualidade de registro e preenchimentos derivados devem ficar para a camada `gold`.")
    lines.append("- A coluna `cobertura` mostra quantos arquivos da amostra apresentaram valor util na melhor fonte candidata.")
    lines.append("- Campos derivados de filesystem e referencias operacionais continuam documentados porque fazem parte do registro final da `silver`.")
    lines.append("- Este mapeamento foi validado sobre amostra hibrida deterministica, combinando maiores arquivos e selecao aleatoria, e nao por leitura apenas dos primeiros arquivos do snapshot.")
    return "\n".join(lines) + "\n"


# Orquestra o fluxo principal do script e imprime o resumo final da execucao.
def main() -> int:
    args = parse_args()
    snapshot_date = validate_date(args.date)
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit deve ser maior que zero.")
    if not 0 < args.sample_fraction <= 1:
        raise SystemExit("--sample-fraction deve estar entre 0 e 1.")
    if args.sample_min_files <= 0:
        raise SystemExit("--sample-min-files deve ser maior que zero.")
    if not 0 <= args.sample_largest_ratio <= 1:
        raise SystemExit("--sample-largest-ratio deve estar entre 0 e 1.")

    list_path, projects_dir = build_paths(snapshot_date)
    if not list_path.exists():
        raise SystemExit(f"Arquivo da lista nao encontrado: {list_path}")
    if not projects_dir.exists():
        raise SystemExit(f"Diretorio de projetos nao encontrado: {projects_dir}")

    detail_files = sorted(projects_dir.glob("*.json"), key=lambda path: int(path.stem))
    if args.limit is not None:
        detail_files = detail_files[: args.limit]
    if not detail_files:
        raise SystemExit(f"Nenhum arquivo de detalhe encontrado em {projects_dir}")

    sampled_files, effective_seed, sample_largest_count, sample_random_count = select_sample_files(
        detail_files=detail_files,
        snapshot_date=snapshot_date,
        sample_fraction=args.sample_fraction,
        sample_min_files=args.sample_min_files,
        sample_seed=args.sample_seed,
        sample_largest_ratio=args.sample_largest_ratio,
    )

    fields = parse_guide_fields(GUIDE_PATH)
    candidate_sources = build_candidate_sources()
    records = [(path, load_json(path)) for path in sampled_files]
    output_path = Path(args.output)

    print("Iniciando geracao do mapeamento silver da Gold Standard")
    print(f"snapshot analisado: {snapshot_date}")
    print(f"arquivo da lista: {list_path}")
    print(f"diretorio de detalhes: {projects_dir}")
    print(f"arquivos disponiveis no snapshot: {len(detail_files)}")
    print(f"arquivos analisados na amostra: {len(records)}")
    print(f"maiores arquivos na amostra: {sample_largest_count}")
    print(f"arquivos aleatorios na amostra: {sample_random_count}")
    print(f"seed da amostra: {effective_seed}")
    print(f"arquivo de saida: {output_path}")

    mapping_stats: dict[str, dict[str, Any]] = {}
    for field in fields:
        candidates = candidate_sources.get(field.name, [])
        best_candidate, hits, example = find_best_candidate(records, candidates)
        if best_candidate is None:
            mapping_stats[field.name] = {
                "status": "unmapped",
                "source_section": "",
                "source_path": "",
                "rule_type": "unmapped",
                "coverage": 0,
                "example": None,
                "notes": "Nenhuma regra inicial configurada para este campo.",
            }
            continue

        status = "mapped" if hits > 0 or best_candidate.rule_type in {"constant", "derived", "lookup"} else "unmapped"
        if status == "unmapped" and not best_candidate.notes:
            notes = "Fonte candidata configurada, mas sem valores uteis no snapshot analisado."
        else:
            notes = best_candidate.notes

        mapping_stats[field.name] = {
            "status": status,
            "source_section": best_candidate.source_section,
            "source_path": best_candidate.source_path,
            "rule_type": best_candidate.rule_type,
            "coverage": f"{hits}/{len(records)}",
            "example": example,
            "notes": notes,
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_markdown(
            snapshot_date=snapshot_date,
            total_available_files=len(detail_files),
            records=records,
            fields=fields,
            mapping_stats=mapping_stats,
            sample_fraction=args.sample_fraction,
            sample_min_files=args.sample_min_files,
            sample_seed=effective_seed,
            sample_largest_ratio=args.sample_largest_ratio,
            sample_largest_count=sample_largest_count,
            sample_random_count=sample_random_count,
        ),
        encoding="utf-8",
    )

    mapped_count = sum(1 for stats in mapping_stats.values() if stats["status"] == "mapped")
    print(f"campos do guia encontrados: {len(fields)}")
    print(f"campos com mapeamento inicial: {mapped_count}")
    print(f"campos ainda sem mapeamento: {len(fields) - mapped_count}")
    print("geracao concluida")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
