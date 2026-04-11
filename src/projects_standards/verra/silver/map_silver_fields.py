# Objetivo do script:
# Analisar os arquivos bronze da Verra e gerar um mapeamento inicial entre o bruto e o schema canonico da camada silver.
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
        description="Analisa os arquivos bronze da Verra e gera um mapeamento inicial para a camada silver."
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
        help=f"Fracao minima de arquivos usada na amostra do mapeamento. Padrao: {DEFAULT_SAMPLE_FRACTION}.",
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
        help="Seed opcional para a parte aleatoria da amostra. Padrao: usa a data do snapshot.",
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
    bronze_dir = ROOT_DIR / "data" / "project_standards" / "01_bronze" / "verra" / snapshot_date
    list_path = bronze_dir / "list" / "projects.json"
    projects_dir = bronze_dir / "projects"
    return list_path, projects_dir


# Calcula o tamanho minimo da amostra usada no mapeamento.
def calculate_sample_size(total_files: int, sample_fraction: float, sample_min_files: int) -> int:
    if total_files <= 0:
        return 0
    if total_files <= sample_min_files:
        return total_files
    return min(total_files, max(sample_min_files, math.ceil(total_files * sample_fraction)))


# Seleciona uma amostra hibrida com maiores arquivos e parte aleatoria.
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
    largest_set = set(largest_files)
    remaining_files = [path for path in detail_files if path not in largest_set]

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


# Retorna o primeiro valor util encontrado para um atributo estruturado.
def get_first_attribute_value(attributes: Any, code: str) -> Any:
    if not isinstance(attributes, list):
        return None
    for item in attributes:
        if not isinstance(item, dict) or item.get("code") != code:
            continue
        values = item.get("values")
        if not isinstance(values, list):
            return None
        for value_item in values:
            if isinstance(value_item, dict) and value_item.get("value") not in (None, ""):
                return value_item.get("value")
    return None


# Coleta todos os valores uteis associados a um atributo estruturado.
def get_attribute_values(attributes: Any, code: str) -> list[Any]:
    if not isinstance(attributes, list):
        return []
    results: list[Any] = []
    for item in attributes:
        if not isinstance(item, dict) or item.get("code") != code:
            continue
        values = item.get("values")
        if not isinstance(values, list):
            continue
        for value_item in values:
            if isinstance(value_item, dict) and value_item.get("value") not in (None, ""):
                results.append(value_item.get("value"))
    return results


# Retorna o primeiro valor util de um atributo presente nos participationSummaries.
def get_participation_attribute_value(payload: dict[str, Any], code: str) -> Any:
    summaries = get_path(payload, "detail_data.participationSummaries")
    if not isinstance(summaries, list):
        return None
    for summary in summaries:
        if not isinstance(summary, dict):
            continue
        value = get_first_attribute_value(summary.get("attributes"), code)
        if value not in (None, ""):
            return value
    return None


# Coleta todos os valores uteis de um atributo presente nos participationSummaries.
def get_participation_attribute_values(payload: dict[str, Any], code: str) -> list[Any]:
    summaries = get_path(payload, "detail_data.participationSummaries")
    if not isinstance(summaries, list):
        return []
    results: list[Any] = []
    for summary in summaries:
        if not isinstance(summary, dict):
            continue
        results.extend(get_attribute_values(summary.get("attributes"), code))
    return results


# Retorna o primeiro valor util de um atributo presente no detalhe.
def get_detail_attribute_value(payload: dict[str, Any], code: str) -> Any:
    return get_first_attribute_value(get_path(payload, "detail_data.attributes"), code)


# Deriva o nome do arquivo de detalhe a partir do caminho no filesystem.
def derive_file_name(_: dict[str, Any], file_path: Path) -> str:
    return file_path.name


# Deriva o caminho relativo do arquivo de detalhe no filesystem.
def derive_file_path(_: dict[str, Any], file_path: Path) -> str:
    return str(file_path.relative_to(ROOT_DIR)).replace("\\", "/")


# Converte um valor escalar em lista quando a regra do campo exigir multiplicidade.
def as_list_from_scalar(value: Any) -> Any:
    if value in (None, ""):
        return None
    if isinstance(value, list):
        return value
    return [value]


# Normaliza o campo canonico de metodologia preservando um ou mais valores textuais.
def normalize_project_methodology(value: Any, split_pattern: str | None = None) -> Any:
    items: list[str] = []

    def visit(current: Any) -> None:
        if isinstance(current, list):
            for item in current:
                visit(item)
            return
        if current in (None, ""):
            return
        text = str(current).strip()
        if not text:
            return
        if split_pattern:
            parts = [part.strip() for part in re.split(split_pattern, text) if part.strip()]
            if parts:
                items.extend(parts)
                return
        items.append(text)

    visit(value)
    unique_items: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            unique_items.append(item)
    if not unique_items:
        return None
    if len(unique_items) == 1:
        return unique_items[0]
    return unique_items


# Monta as fontes candidatas usadas no mapeamento inicial da silver.
def build_candidate_sources() -> dict[str, list[CandidateSource]]:
    path = lambda source_section, source_path, rule_type="direct", notes="": CandidateSource(
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

    def participation(code: str, notes: str = "", rule_type: str = "direct") -> CandidateSource:
        return CandidateSource(
            source_section="detail_data",
            source_path=f"participationSummaries[].attributes[{code}]",
            rule_type=rule_type,
            notes=notes,
            extractor=lambda payload, _file_path, c=code: get_participation_attribute_value(payload, c),
        )

    def detail_attr(code: str, notes: str = "", rule_type: str = "direct") -> CandidateSource:
        return CandidateSource(
            source_section="detail_data",
            source_path=f"attributes[{code}]",
            rule_type=rule_type,
            notes=notes,
            extractor=lambda payload, _file_path, c=code: get_detail_attribute_value(payload, c),
        )

    def transformed_list(source_section: str, source_path: str, transform: Callable[[Any], Any], notes: str, rule_type: str) -> CandidateSource:
        return CandidateSource(
            source_section=source_section,
            source_path=source_path,
            rule_type=rule_type,
            notes=notes,
            extractor=lambda payload, _file_path, p=f"{source_section}.{source_path}", fn=transform: fn(get_path(payload, p)),
        )

    return {
        "carbon_standard": [path("source", "carbon_standard")],
        "standard_acronym": [
            CandidateSource(
                source_section="constant",
                source_path="VCS",
                rule_type="constant",
                notes="Nao vem explicitamente no bruto; sigla tecnica do programa VCS para a Verra.",
                extractor=lambda payload, _file_path: "VCS",
            )
        ],
        "project_public_id": [path("source", "project_public_id"), path("list_data", "resourceIdentifier")],
        "project_internal_id": [path("source", "project_internal_id"), path("detail_data", "resourceIdentifier")],
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
        "project_name": [path("detail_data", "resourceName"), path("list_data", "resourceName")],
        "project_status": [participation("PROJECT_STATUS"), path("list_data", "resourceStatus")],
        "program_name": [path("list_data", "program")],
        "project_details": [path("detail_data", "description")],
        "project_methodology": [
            CandidateSource(
                source_section="detail_data",
                source_path="participationSummaries[].attributes[PROTOCOL_NAME]",
                rule_type="normalized",
                notes="Usa os nomes de protocolo da Verra e separa multiplas metodologias quando vierem em texto unico delimitado por virgula ou ponto e virgula.",
                extractor=lambda payload, _file_path: normalize_project_methodology(
                    get_participation_attribute_values(payload, "PROTOCOL_NAME") or get_path(payload, "list_data.protocols"),
                    split_pattern=r"\s*[,;]\s*",
                ),
            )
        ],
        "methodologies": [
            transformed_list(
                "list_data",
                "protocols",
                as_list_from_scalar,
                "A Verra normalmente expõe uma metodologia textual unica em protocols; a lista e derivada desse valor.",
                "normalized",
            )
        ],
        "project_type": [path("list_data", "version")],
        "sector": [participation("PRIMARY_PROJECT_CATEGORY_NAME"), path("list_data", "protocolCategories")],
        "project_category": [path("list_data", "protocolSubCategories"), participation("PROJECT_SUBCATERGORY_NAMES")],
        "sdg_targets": [
            transformed_list(
                "list_data",
                "programObjectives",
                as_list_from_scalar,
                "Campo existe na lista, mas aparece nulo nos exemplos atuais analisados.",
                "normalized",
            )
        ],
        "project_developer": [participation("PROPONENT_NAME"), path("list_data", "proponent")],
        "project_owner": [],
        "project_operator": [path("list_data", "operator")],
        "validation_body": [participation("VALIDATOR_NAME")],
        "verification_body": [],
        "country": [path("list_data", "country")],
        "state_or_region": [detail_attr("STATE_PROVINCE")],
        "city_or_locality": [],
        "site_location_bronze": [detail_attr("STATE_PROVINCE", notes="A Verra nem sempre separa localizacao textual detalhada da unidade administrativa.")],
        "location_latitude": [path("detail_data", "location.latitude")],
        "location_longitude": [path("detail_data", "location.longitude")],
        "snapshot_date": [path("source", "snapshot_date")],
        "reference_month": [path("source", "reference_month")],
        "registration_date": [path("list_data", "projectRegistrationDate"), participation("PROJECT_REGISTRATION_DATE", rule_type="normalized")],
        "status_date": [],
        "crediting_start_date": [path("list_data", "creditingPeriodStartDate")],
        "crediting_end_date": [path("list_data", "creditingPeriodEndDate")],
        "first_issuance_date": [],
        "last_issuance_date": [],
        "credits_issued_total": [],
        "credits_retired_total": [],
        "credits_cancelled_total": [],
        "credits_buffer_total": [],
        "estimated_annual_emission_reductions": [
            path("list_data", "estAnnualEmissionReductions"),
            participation("EST_ANNUAL_EMISSION_REDCT", rule_type="normalized"),
        ],
        "estimated_total_emission_reductions": [],
        "area_hectares": [participation("PROJECT_ACREAGE", rule_type="normalized")],
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
    lines.append("# Mapeamento Inicial Silver da Verra")
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
    lines.append("- Este arquivo e um ponto de partida para refinarmos o mapeamento `bronze -> silver` da Verra.")
    lines.append("- Campos com status `unmapped` ainda nao tiveram uma origem confiavel encontrada no bruto analisado.")
    lines.append("- A coluna `cobertura` mostra quantos arquivos da amostra apresentaram valor util na melhor fonte candidata.")
    lines.append("- Campos derivados de filesystem ou constantes tecnicas continuam documentados porque fazem parte do registro final da `silver`.")
    lines.append("- Este documento deve ser tratado como mapeamento exploratorio ate a estabilizacao do mapeamento canonico da Verra.")
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

    print("Iniciando geracao do mapeamento silver da Verra")
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

        status = "mapped" if hits > 0 or best_candidate.rule_type in {"constant", "derived"} else "unmapped"
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
