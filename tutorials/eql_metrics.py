"""
Readability and complexity metrics comparing EQL queries to their SQL equivalents.

SINGLE SOURCE OF TRUTH: this module used to be duplicated between a pytest
file (test_eql_readability.py) and a notebook-safe extract (this file). That
meant every fix had to be made twice and the two versions drifted apart. This
file is now the only place the metric functions live; the notebook (eql_demo.ipynb) imports directly from
here and IS the place where results are produced, shown and discussed. There
is no test_eql_readability.py anymore — retire/delete it if it still exists
in the repo.

IMPORTANT: This module does NOT test the correctness of the EQL-to-SQL
translation. Translation correctness is verified in test_eql.py. This module
only measures the readability and complexity properties of the query
expressions themselves — both the EQL source and the SQL it maps to.

Scientific foundations:
- Halstead (1977): Software Science — information-theoretic complexity measures
- McCabe (1976): A Complexity Measure — cyclomatic complexity
- Campbell (2018): Cognitive Complexity (SonarSource) — human-oriented complexity
- Sweller (1988): Cognitive Load Theory — intrinsic vs extrinsic cognitive load
- Baddeley (1974): Working Memory Model — capacity limits of working memory
- Miller (1956): The Magical Number Seven — chunking in short-term memory
- Lawrie et al. (2006): Identifier quality and cognitive load
- Eichberg et al. (2008): Error-prone constructs in software
- Fowler (2010): Domain-Specific Languages

Methodological notes:

1. Comparison basis. The translator-generated SQL is not the SQL a human
   would write by hand — it currently joins the entire inheritance chain of
   a query's base variable(s), including tables whose columns are never
   selected and whose existence is already guaranteed by the foreign-key
   constraint. `HANDWRITTEN_SQL` gives a realistic hand-written equivalent
   for each of the five evaluation queries (plus the introductory
   PickUpAction/GraspDescription example), and `translator_overhead_ratio` /
   `analyze(..., handwritten_sql=...)`
   measure the honest EQL-vs-human gap and the translator's own avoidable
   overhead separately.

2. Metrics EQL wins "by definition". `domain_transparency` and
   `technical_noise` previously excluded SQL infrastructure tokens (DAO, _id,
   JOIN, AS, ...) but not EQL's own DSL machinery (`variable`, `domain=[]`,
   `an`, `set_of`, `.where(`, ...). Both vocabularies are now excluded
   symmetrically. The old (asymmetric) computation is kept as
   `domain_transparency_naive` purely so the difference can be shown and
   cited directly.

3. Overly strong formulations. Growth-rate claims should be measured at
   several points, not two (see `build_container_chain` /
   `eql_source_for_chain`, used in the notebook's scaling section) and
   phrased as evidence of a trend, not a proven asymptotic law. Miller (1956)
   is a claim about chunks, not raw tokens — a JOIN clause is one chunk to
   someone fluent in SQL.

4. The 75% expressiveness number. Replaced by an explicit, enumerable
   feature table (`FEATURE_TABLE`) with a supported/unsupported/partial
   status per feature (`feature_coverage_counts()`), so the resulting
   percentage is traceable rather than asserted. The list is a selection of
   constructs relevant to the evaluated queries, not the full SQL standard,
   so the percentage is an orientation, not an objective coverage figure.
"""

import math
import re


# =============================================================================
# Metric 1: Character Length
# =============================================================================

def character_length(source: str) -> int:
    """
    Count non-whitespace characters in the source.

    Rationale: shorter queries contain less information to process and are
    faster to read at a glance. Based on the Lines of Code (LOC) family of
    metrics (Halstead, 1977).

    Note: length alone does not capture readability — a short but cryptic
    expression can be harder to understand than a longer clear one.

    :param source: Query source string
    :return: Non-whitespace character count
    """
    return len(re.sub(r'\s+', '', source))


# =============================================================================
# Symmetric infrastructure vocabularies
# =============================================================================
#
# Both languages carry tokens that are pure "how do I express this at all"
# machinery, not domain vocabulary. Counting only one side's machinery
# guarantees that side a near-perfect score before any query is measured.
# Both vocabularies below are applied the same way in `technical_noise` and
# `domain_transparency`.

_SQL_INFRA_WORDS = {
    'SELECT', 'FROM', 'WHERE', 'JOIN', 'ON', 'AS', 'AND', 'OR', 'WITH',
    'IN', 'IS', 'NOT', 'NULL', 'ORDER', 'BY', 'LIMIT', 'DISTINCT',
    'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
}
_SQL_INFRA_SUFFIXES = ('_id', 'DAO')
_SQL_INFRA_EXACT = {'database_id', 'polymorphic_type'}

# EQL's own DSL machinery: the words/calls needed to express *any* query in
# this notation, regardless of domain content.
_EQL_INFRA_WORDS = {
    'an', 'the', 'set_of', 'entity', 'variable', 'domain', 'type_',
    'where', 'ordered_by', 'limit', 'distinct', 'count_all', 'case_when',
    'and_', 'or_', 'not_', 'in_',
}


def _is_infrastructure_word(word: str, is_eql: bool) -> bool:
    """
    Symmetric infrastructure check used by both technical_noise and
    domain_transparency, so the two languages are judged by the same rule.
    """
    if is_eql:
        return word in _EQL_INFRA_WORDS
    return (
        word in _SQL_INFRA_WORDS
        or word in _SQL_INFRA_EXACT
        or any(word.endswith(suf) for suf in _SQL_INFRA_SUFFIXES)
    )


# =============================================================================
# Metric 2: Technical Noise
# =============================================================================

def technical_noise(source: str, is_eql: bool) -> int:
    """
    Count tokens that carry no domain meaning, using the *same* infrastructure
    vocabulary as domain_transparency so the two languages are counted
    symmetrically.

    Rationale: infrastructure tokens must be mentally filtered by the reader
    to extract the domain intent. Based on identifier-quality research
    (Lawrie et al., 2006).

    :param source: Query source string
    :param is_eql: True if EQL, False if SQL
    :return: Count of technical tokens
    """
    words = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', source)
    return sum(1 for w in words if _is_infrastructure_word(w, is_eql))


# =============================================================================
# Metric 3: Domain Transparency
# =============================================================================

def domain_transparency(source: str, is_eql: bool) -> float:
    """
    Ratio of domain-meaningful words to all words, counted symmetrically.

    Rationale: a query with high domain transparency can be understood
    purely from domain knowledge. Based on Fowler (2010) — applied with the
    same yardstick to both languages.

    :param source: Query source string
    :param is_eql: True if EQL, False if SQL
    :return: Ratio between 0.0 and 1.0
    """
    words = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', source)
    if not words:
        return 0.0
    domain_words = [w for w in words if not _is_infrastructure_word(w, is_eql)]
    return round(len(domain_words) / len(words), 3)


def domain_transparency_naive(source: str) -> float:
    """
    The ORIGINAL (asymmetric) computation, kept only for direct comparison.

    Excludes only SQL-style infrastructure tokens and never excludes EQL's
    own DSL words, so EQL sources score close to 1.0 regardless of content.
    Do not use this for reporting — it exists so the notebook can show, side
    by side, the number that comes out of counting both sides the same way
    versus not (see the domain-transparency section of the notebook).

    :param source: Query source string
    :return: Ratio between 0.0 and 1.0
    """
    old_infrastructure_tokens = {
        'DAO', 'AS', 'ON', 'JOIN', 'SELECT', 'FROM', 'WHERE',
        'AND', 'OR', 'WITH', 'IN', 'IS', 'NOT', 'NULL',
        'database_id', 'polymorphic_type',
    }
    words = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', source)
    if not words:
        return 0.0
    domain_words = [
        w for w in words
        if not any(t in w for t in old_infrastructure_tokens)
        and not w.endswith('_id')
        and not w.endswith('DAO')
    ]
    return round(len(domain_words) / len(words), 3)


# =============================================================================
# Metric 4: Nesting Depth
# =============================================================================

def nesting_depth(source: str) -> int:
    """
    Maximum depth of nested brackets and parentheses.

    Rationale: deep nesting forces the reader to track multiple open
    contexts simultaneously. Based on McCabe (1976) and Campbell (2018).

    Note: SQL is a flat language by design — SQL will consistently win this
    metric. This is a syntactic style difference, not a quality one.

    :param source: Query source string
    :return: Maximum nesting depth
    """
    max_depth = depth = 0
    for char in source:
        if char in '([':
            depth += 1
            max_depth = max(max_depth, depth)
        elif char in ')]':
            depth -= 1
    return max_depth


# =============================================================================
# Metric 5: Halstead Volume
# =============================================================================

SQL_OPERATORS = [
    'SELECT', 'FROM', 'WHERE', 'JOIN', 'ON', 'AND', 'OR',
    'GROUP BY', 'HAVING', 'ORDER BY', 'CASE WHEN', 'THEN', 'END',
    'WITH', 'AS',
]

EQL_OPERATORS = [
    '.where(', 'and_(', 'or_(', 'case_when(', '==', '!=',
    '>', '<', '>=', '<=', 'not_(', 'in_(',
]


def _count_operator(source: str, operator: str) -> int:
    """
    Count occurrences of one operator in a source string.

    Keyword-like operators (letters and spaces only, e.g. ``ON`` or
    ``GROUP BY``) are matched as whole words, case-insensitively, and an
    internal space matches any whitespace run. Plain substring matching would
    count ``ON`` inside ``ConnectionDAO`` or ``AS`` inside ``BASE`` and
    inflate the SQL side. Operators containing punctuation (``.where(``,
    ``==``) are matched literally.

    :param source: Query source string
    :param operator: Operator token
    :return: Number of occurrences
    """
    if re.fullmatch(r'[A-Za-z ]+', operator):
        pattern = r'\b' + re.escape(operator).replace(r'\ ', r'\s+') + r'\b'
    else:
        pattern = re.escape(operator)
    return len(re.findall(pattern, source, flags=re.IGNORECASE))


def halstead_volume(source: str, operators: list) -> float:
    """
    Halstead volume: N * log2(n).

    From Halstead (1977): measures information density in working memory.
    Note: designed for imperative code, adapted here for declarative queries.
    Operands are all identifiers (words of letters, digits, underscore);
    keywords that are also operators are thus counted as operands as well,
    a simplification applied identically to both languages.

    :param source: Query source string
    :param operators: Operator tokens for this language
    :return: Halstead volume
    """
    unique_operators = 0
    total_operators = 0
    for op in operators:
        count = _count_operator(source, op)
        total_operators += count
        unique_operators += 1 if count else 0
    operands = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', source)
    unique_operands = len(set(operands))
    total_operands = len(operands)
    vocabulary = unique_operators + unique_operands
    length = total_operators + total_operands
    if vocabulary <= 1:
        return 0.0
    return round(length * math.log2(vocabulary), 2)


# =============================================================================
# Metric 6: Abstraction Ratio / Translator Overhead
# =============================================================================

def abstraction_ratio(eql_source: str, sql_source: str) -> float:
    """
    Characters generated per EQL character.

    Measures how much infrastructure complexity EQL hides from the user.
    Applied to either the translator SQL or the handwritten SQL, depending
    on which is passed in — see `analyze()`.

    :param eql_source: EQL query source
    :param sql_source: Equivalent SQL
    :return: SQL length / EQL length
    """
    eql_len = character_length(eql_source)
    sql_len = character_length(sql_source)
    if eql_len == 0:
        return 0.0
    return round(sql_len / eql_len, 1)


def translator_overhead_ratio(handwritten_sql: str, translator_sql: str) -> float:
    """
    How much longer the translator's SQL is than a human's, for the same query.

    A ratio of 1.0 means the translator produces exactly what a human would
    write. Anything above 1.0 quantifies avoidable translator overhead
    (currently: joining the full inheritance chain of the base variable even
    when the selected columns don't require it) rather than schema-inherent
    (JTI) complexity that a human would have to write too.

    :param handwritten_sql: Realistic hand-written SQL for the same query
    :param translator_sql: SQL produced by the current EQL-to-SQL translator
    :return: translator length / handwritten length
    """
    hw_len = character_length(handwritten_sql)
    tr_len = character_length(translator_sql)
    if hw_len == 0:
        return 0.0
    return round(tr_len / hw_len, 2)


# =============================================================================
# Metric 7: Foreign Key Error Opportunities
# =============================================================================

def fk_error_opportunities(source: str, is_eql: bool) -> int:
    """
    Number of places where a foreign key mistake could be introduced.

    In SQL every ON clause can have the wrong column name. EQL never exposes
    foreign keys, so this one is legitimately asymmetric by construction of
    the language, not by a counting choice. Based on Eichberg et al. (2008).

    :param source: Query source string
    :param is_eql: True if EQL, False if SQL
    :return: Number of potential FK error locations
    """
    if is_eql:
        return 0
    return source.upper().count(' ON ')


# =============================================================================
# Metric 8: Extrinsic Cognitive Load (Sweller, 1988)
# =============================================================================

_EXTRINSIC_SQL_TOKENS = re.compile(
    r'(_id\b|DAO\b|database_id|polymorphic_type|'
    r'SymbolDAO|WorldEntityDAO|ConnectionDAO)'
)

_EXTRINSIC_EQL_TOKENS = re.compile(
    r'(type_=|domain=)'
)


def extrinsic_cognitive_load(source: str, is_eql: bool) -> int:
    """
    Count tokens that represent extrinsic cognitive load: knowledge about the
    *representation* (schema/FK/table names on the SQL side; type/domain
    plumbing on the EQL side) rather than the domain problem itself.

    Based on Sweller (1988) Cognitive Load Theory. Baddeley (1974) and
    Miller (1956) describe short-term memory capacity as ~7±2 *chunks* — not
    raw tokens. A JOIN clause is one chunk to a reader fluent in SQL, and
    on-screen source does not have to be held in memory. The counts below are
    a proxy for load, not a literal chunk count.

    :param source: Query source string
    :param is_eql: True if EQL, False if SQL
    :return: Count of extrinsic cognitive load tokens
    """
    pattern = _EXTRINSIC_EQL_TOKENS if is_eql else _EXTRINSIC_SQL_TOKENS
    return len(pattern.findall(source))


# =============================================================================
# Metric 9: Cognitive Complexity (Campbell, 2018)
# =============================================================================

def cognitive_complexity_sql(sql: str) -> dict:
    """
    Cognitive complexity for SQL, adapted from Campbell (2018).

    Scoring:
    - Baseline: 1
    - +1 per JOIN, AND/OR, CASE WHEN
    - +depth per nested JOIN (nesting penalty)
    - +2 per subquery

    :param sql: SQL query string
    :return: Dict with score breakdown and total

    Note: the ' JOIN ' / ' ON ' substring counts
    below require a literal space on both sides of the keyword. The
    hand-written SQL in ``HANDWRITTEN_SQL`` is formatted with a newline
    before each ``JOIN`` (for readability in the thesis listings), which
    used to make this count silently see 0 joins for every multi-line query
    — an artifact of formatting, not a real difference in complexity. All
    whitespace (including newlines) is now collapsed to single spaces
    before counting, so the score no longer depends on how the SQL was
    line-wrapped.
    """
    sql_normalized = re.sub(r'\s+', ' ', sql.strip())
    sql_upper = sql_normalized.upper()
    breakdown = {
        'baseline': 1,
        'joins': sql_upper.count(' JOIN '),
        'conditions': sql_upper.count(' AND ') + sql_upper.count(' OR '),
        'case_when': sql_upper.count('CASE WHEN'),
        'subqueries': max(0, sql_upper.count('SELECT') - 1) * 2,
        'nesting_penalty': 0,
    }
    depth = 0
    i = 0
    while i < len(sql_normalized):
        if sql_normalized[i] == '(':
            depth += 1
        elif sql_normalized[i] == ')':
            depth -= 1
        elif sql_normalized[i:i+5].upper() == ' JOIN' and depth > 0:
            breakdown['nesting_penalty'] += depth
        i += 1
    breakdown['total'] = sum(v for k, v in breakdown.items() if k != 'total')
    return breakdown


def cognitive_complexity_eql(eql_source: str) -> dict:
    """
    Cognitive complexity for EQL, adapted from Campbell (2018).

    Scoring:
    - Baseline: 1
    - +1 per .where(), comparison, and_(), or_(), case_when()
    - +max_depth - 2 nesting penalty (threshold 2 = expected base level)

    :param eql_source: EQL query source string
    :return: Dict with score breakdown and total
    """
    breakdown = {
        'baseline': 1,
        'where_clauses': eql_source.count('.where('),
        'comparisons': sum(
            eql_source.count(op)
            for op in ['==', '!=', ' > ', ' < ', ' >= ', ' <= ']
        ),
        'logical': eql_source.count('and_(') + eql_source.count('or_('),
        'case_when': eql_source.count('case_when('),
        'nesting_penalty': 0,
    }
    max_depth = depth = 0
    for char in eql_source:
        if char == '(':
            depth += 1
            max_depth = max(max_depth, depth)
        elif char == ')':
            depth -= 1
    breakdown['nesting_penalty'] = max(0, max_depth - 2)
    breakdown['total'] = sum(v for k, v in breakdown.items() if k != 'total')
    return breakdown


# =============================================================================
# Expressiveness coverage — explicit feature table (replaces the bare "75%")
# =============================================================================
#
# An earlier draft quoted a bare "75%" that was not traceable to a concrete
# list. This table makes every counted feature explicit, with its own
# supported / partial / unsupported status, so the percentage can be
# recomputed line by line. The list is a selection of constructs relevant to
# the evaluated queries, not the full SQL standard (e.g. outer joins or LIKE
# are not listed and were not systematically checked).

FEATURE_TABLE = [
    # (feature, status: True / False / "partial")
    ("SELECT specific columns (set_of)",         True),
    ("SELECT full entity (entity)",              True),
    ("WHERE / filter conditions",                True),
    ("Equality joins across variables",          True),
    ("Transitive attribute access (a.b.c)",      True),
    ("ORDER BY (ordered_by)",                    True),
    ("LIMIT",                                    True),
    ("DISTINCT",                                 True),
    ("AND / OR (and_, or_)",                     True),
    ("NOT / IN (not_, in_)",                     True),
    ("GROUP BY (grouped_by)",                    True),
    ("HAVING (having)",                          True),
    ("CASE WHEN (case_when)",                    True),
    ("Aggregation: COUNT (count_all)",           True),
    ("Aggregation: MIN",                         True),
    ("Aggregation: MAX",                         True),
    ("Aggregation: SUM",                         True),
    ("Aggregation: AVG (average)",               True),
    ("Common Table Expressions (CTE)",           "partial"),  # see Listing 5.5
    ("Polymorphic type filtering",               True),
    ("Subquery in SELECT clause",                False),
    ("UNION",                                    False),
    ("INTERSECT",                                False),
    ("EXCEPT",                                   False),
    ("Window functions (ROW_NUMBER, RANK, ...)", False),
    ("INSERT / UPDATE / DELETE",                 False),
    ("Multiple aggregations w/ different FILTER conditions", False),
]

def feature_coverage_counts() -> dict:
    """
    Compute the expressiveness percentage from the explicit feature list
    rather than asserting a bare "75%".

    :return: dict with the counting and the resulting percentages
    """
    fine_supported = sum(1 for _, status in FEATURE_TABLE if status is True)
    fine_partial = sum(1 for _, status in FEATURE_TABLE if status == "partial")
    fine_total = len(FEATURE_TABLE)

    return {
        'fine_grained': {
            'supported': fine_supported,
            'partial': fine_partial,
            'total': fine_total,
            'percent_supported_only': round(100 * fine_supported / fine_total, 1),
            'percent_supported_or_partial': round(
                100 * (fine_supported + fine_partial) / fine_total, 1
            ),
        },
    }


def expressiveness_coverage() -> float:
    """
    Kept for backward compatibility with earlier call sites. Derived from the
    explicit FEATURE_TABLE instead of a bare constant.

    :return: Supported fraction (0.0 to 1.0), fine-grained, "partial" counted
        as not-yet-supported.
    """
    counts = feature_coverage_counts()['fine_grained']
    return round(counts['supported'] / counts['total'], 2)


def print_feature_table() -> None:
    """Print the explicit feature table and both ways of counting it."""
    counts = feature_coverage_counts()
    print('EQL feature coverage (explicit, traceable):')
    print(f'{"Feature":<55} {"Status":>10}')
    print('-' * 66)
    for feature, status in FEATURE_TABLE:
        label = {'True': 'yes', 'False': 'no'}.get(str(status), str(status))
        print(f'{feature:<55} {label:>10}')
    print(
        f'\nFine-grained ({counts["fine_grained"]["total"]} items above): '
        f'{counts["fine_grained"]["supported"]}/{counts["fine_grained"]["total"]} '
        f'supported ({counts["fine_grained"]["percent_supported_only"]}%), '
        f'{counts["fine_grained"]["partial"]} partial'
    )



# =============================================================================
# Handwritten SQL for the five evaluation queries
# =============================================================================
#
# Realistic SQL a competent developer would write by hand for each query,
# joining only what is needed to reach the selected columns and relying on
# foreign-key constraints for existence rather than joining parent tables
# whose columns are never read. Where the underlying entity uses Joined
# Table Inheritance (JTI — e.g. Body -> WorldEntityDAO -> SymbolDAO), the
# inheritance-chain joins ARE included, because they are schema-inherent: a
# human selecting full-entity columns spread across the inheritance chain
# cannot avoid them either. The distinction this module cares about is
# between that unavoidable schema cost and the translator's *additional*,
# avoidable joins (e.g. DesignatorDAO/ActionDescriptionDAO in the
# PickUpAction/GraspDescription example below, which contribute no columns
# to the result and are not required for correctness given the foreign-key
# constraint).

HANDWRITTEN_SQL = {
    'Simple filter': (
        "SELECT b.database_id, b.name, b.size\n"
        "FROM BodyDAO b\n"
        "JOIN WorldEntityDAO w ON w.database_id = b.database_id\n"
        "JOIN SymbolDAO s ON s.database_id = w.database_id\n"
        "WHERE b.size > 5;"
    ),
    # Matches the 4-column query used in eql_demo.ipynb (robot_x, robot_y,
    # rotate_gripper, approach_direction) — keep this in sync with the EQL
    # source built in both eql_demo.ipynb and eql_test.ipynb for this case.
    'Transitive attrs': (
        "SELECT m.robot_x, m.robot_y, g.rotate_gripper, g.approach_direction\n"
        "FROM MoveActionDAO m\n"
        "JOIN GraspConfigDAO g ON g.database_id = m.grasp_config_id;"
    ),
    # Container and Handle are both Body subtypes (JTI: SymbolDAO ->
    # WorldEntityDAO -> BodyDAO -> Container/HandleDAO); FixedConnection and
    # PrismaticConnection are both Connection subtypes (JTI: SymbolDAO ->
    # WorldEntityDAO -> ConnectionDAO -> Fixed/PrismaticConnectionDAO), with
    # the parent/child FK columns (_parent_id/_child_id) living on
    # ConnectionDAO itself, not on the leaf table. Verified against the
    # translator's own generated SQL for these two queries. A human selecting
    # full entities here cannot avoid these joins any more than the
    # translator can (see the module docstring) — written out in full
    # instead of hand-waved away in a comment, for a fair length comparison.
    'Multi-join (3 vars)': (
        "SELECT c.database_id, c_b.name, c_b.size,\n"
        "       h.database_id, h_b.name, h_b.size,\n"
        "       fc.database_id, fcc._parent_id, fcc._child_id\n"
        "FROM ContainerDAO c\n"
        "JOIN BodyDAO c_b ON c_b.database_id = c.database_id\n"
        "JOIN WorldEntityDAO c_w ON c_w.database_id = c_b.database_id\n"
        "JOIN SymbolDAO c_s ON c_s.database_id = c_w.database_id\n"
        "JOIN ConnectionDAO fcc ON fcc._parent_id = c.database_id\n"
        "JOIN FixedConnectionDAO fc ON fc.database_id = fcc.database_id\n"
        "JOIN WorldEntityDAO fc_w ON fc_w.database_id = fcc.database_id\n"
        "JOIN SymbolDAO fc_s ON fc_s.database_id = fc_w.database_id\n"
        "JOIN HandleDAO h ON h.database_id = fcc._child_id\n"
        "JOIN BodyDAO h_b ON h_b.database_id = h.database_id\n"
        "JOIN WorldEntityDAO h_w ON h_w.database_id = h_b.database_id\n"
        "JOIN SymbolDAO h_s ON h_s.database_id = h_w.database_id;"
    ),
    'Multi-join (4 vars)': (
        "SELECT c.database_id, c_b.name, c_b.size,\n"
        "       h.database_id, h_b.name, h_b.size,\n"
        "       fc.database_id, fcc._parent_id, fcc._child_id,\n"
        "       pc.database_id, pcc._parent_id, pcc._child_id\n"
        "FROM ContainerDAO c\n"
        "JOIN BodyDAO c_b ON c_b.database_id = c.database_id\n"
        "JOIN WorldEntityDAO c_w ON c_w.database_id = c_b.database_id\n"
        "JOIN SymbolDAO c_s ON c_s.database_id = c_w.database_id\n"
        "JOIN ConnectionDAO fcc ON fcc._parent_id = c.database_id\n"
        "JOIN FixedConnectionDAO fc ON fc.database_id = fcc.database_id\n"
        "JOIN WorldEntityDAO fc_w ON fc_w.database_id = fcc.database_id\n"
        "JOIN SymbolDAO fc_s ON fc_s.database_id = fc_w.database_id\n"
        "JOIN HandleDAO h ON h.database_id = fcc._child_id\n"
        "JOIN BodyDAO h_b ON h_b.database_id = h.database_id\n"
        "JOIN WorldEntityDAO h_w ON h_w.database_id = h_b.database_id\n"
        "JOIN SymbolDAO h_s ON h_s.database_id = h_w.database_id\n"
        "JOIN ConnectionDAO pcc ON pcc._child_id = c.database_id\n"
        "JOIN PrismaticConnectionDAO pc ON pc.database_id = pcc.database_id\n"
        "JOIN WorldEntityDAO pc_w ON pc_w.database_id = pcc.database_id\n"
        "JOIN SymbolDAO pc_s ON pc_s.database_id = pc_w.database_id;"
    ),
    'Complex combined': (
        "SELECT b.*, w.*, s.*\n"
        "FROM BodyDAO b\n"
        "JOIN WorldEntityDAO w ON w.database_id = b.database_id\n"
        "JOIN SymbolDAO s ON s.database_id = w.database_id\n"
        "WHERE b.size > 5\n"
        "ORDER BY b.size\n"
        "LIMIT 10;"
    ),
}

# The introductory PickUpAction/GraspDescription example used to motivate
# EQL at the start of the thesis. Reproduced verbatim so the notebook's
# demo operates on exactly the numbers quoted in the thesis, not a
# paraphrase of them.
PICKUP_EXAMPLE_EQL = (
    "action = variable(type_=PickUpAction, domain=[])\n"
    "query = an(set_of(\n"
    "    action.arm,\n"
    "    action.grasp_description.rotate_gripper,\n"
    "    action.grasp_description.approach_direction,\n"
    "))"
)

PICKUP_EXAMPLE_TRANSLATOR_SQL = (
    'SELECT "PickUpActionDAO".arm, "GraspDescriptionDAO_1".rotate_gripper, '
    '"GraspDescriptionDAO_1".approach_direction\n'
    'FROM "DesignatorDAO"\n'
    'JOIN "ActionDescriptionDAO" ON "ActionDescriptionDAO".database_id = "DesignatorDAO".database_id\n'
    'JOIN "PickUpActionDAO" ON "PickUpActionDAO".database_id = "ActionDescriptionDAO".database_id\n'
    'JOIN "GraspDescriptionDAO" AS "GraspDescriptionDAO_1" ON '
    '"GraspDescriptionDAO_1".database_id = "PickUpActionDAO".grasp_description_id'
)

# The reviewer's own example of what a human would actually write: only the
# two tables whose columns are selected, joined directly via the FK that
# already exists on PickUpActionDAO.
PICKUP_EXAMPLE_HANDWRITTEN_SQL = (
    "SELECT p.arm, g.rotate_gripper, g.approach_direction\n"
    "FROM PickUpActionDAO p\n"
    "JOIN GraspDescriptionDAO g ON g.database_id = p.grasp_description_id;"
)


# =============================================================================
# Measured EQL sources (single source of truth for all six queries)
# =============================================================================
#
# Fairness rule: every EQL source is measured INCLUDING the `variable(...)`
# declarations it needs. The SQL counterparts name their tables in FROM/JOIN,
# so leaving the declarations out would credit EQL with a shorter source than
# the code a user actually has to write. `world.bodies` / `world.connections`
# stand for the user's own data source; the notebooks use differently named
# local variables for the same expression.

EQL_SOURCES = {
    'Simple filter': (
        "b = variable(type_=Body, domain=[])\n"
        "an(entity(b).where(b.size > 5))"
    ),
    'Transitive attrs': (
        "move = variable(type_=MoveAction, domain=[])\n"
        "an(set_of(move.robot_x, move.robot_y, "
        "move.grasp_config.rotate_gripper, move.grasp_config.approach_direction))"
    ),
    'Multi-join (3 vars)': (
        "C = variable(Container, domain=world.bodies)\n"
        "H = variable(Handle, domain=world.bodies)\n"
        "FC = variable(FixedConnection, domain=world.connections)\n"
        "an(set_of(C, H, FC).where(C == FC.parent, H == FC.child))"
    ),
    'Multi-join (4 vars)': (
        "C = variable(Container, domain=world.bodies)\n"
        "H = variable(Handle, domain=world.bodies)\n"
        "FC = variable(FixedConnection, domain=world.connections)\n"
        "PC = variable(PrismaticConnection, domain=world.connections)\n"
        "an(set_of(C, H, FC, PC).where("
        "C == FC.parent, H == FC.child, C == PC.child))"
    ),
    'Complex combined': (
        "b = variable(type_=Body, domain=[])\n"
        "an(entity(b).where(b.size > 5).ordered_by(b.size).limit(10))"
    ),
    'PickUpAction-Beispiel': PICKUP_EXAMPLE_EQL,
}


# =============================================================================
# Combined analysis
# =============================================================================

def analyze(name: str, eql_source: str, sql_source: str,
            handwritten_sql: str = None) -> dict:
    """
    Run all metrics for an EQL/SQL query pair, and optionally a handwritten-SQL
    variant of the same query for a three-way comparison.

    :param name: Human-readable query name
    :param eql_source: EQL query as source string
    :param sql_source: SQL generated by the current translator
    :param handwritten_sql: Optional realistic hand-written SQL for the same
        query (see HANDWRITTEN_SQL)
    :return: Full analysis result dict
    """
    eql_cc = cognitive_complexity_eql(eql_source)
    sql_cc = cognitive_complexity_sql(sql_source)

    result = {
        'name': name,
        'eql_source': eql_source,
        'sql_source': sql_source,
        'eql': {
            'char_length': character_length(eql_source),
            'technical_noise': technical_noise(eql_source, True),
            'domain_transparency': domain_transparency(eql_source, True),
            'nesting_depth': nesting_depth(eql_source),
            'halstead_volume': halstead_volume(eql_source, EQL_OPERATORS),
            'fk_error_opportunities': fk_error_opportunities(eql_source, True),
            'extrinsic_load': extrinsic_cognitive_load(eql_source, True),
            'cognitive_complexity': eql_cc['total'],
            'cognitive_breakdown': eql_cc,
        },
        'sql': {
            'char_length': character_length(sql_source),
            'technical_noise': technical_noise(sql_source, False),
            'domain_transparency': domain_transparency(sql_source, False),
            'nesting_depth': nesting_depth(sql_source),
            'halstead_volume': halstead_volume(sql_source, SQL_OPERATORS),
            'fk_error_opportunities': fk_error_opportunities(sql_source, False),
            'extrinsic_load': extrinsic_cognitive_load(sql_source, False),
            'cognitive_complexity': sql_cc['total'],
            'cognitive_breakdown': sql_cc,
        },
        'shared': {
            'abstraction_ratio': abstraction_ratio(eql_source, sql_source),
            'expressiveness_coverage': expressiveness_coverage(),
        },
    }

    if handwritten_sql is not None:
        hw_cc = cognitive_complexity_sql(handwritten_sql)
        result['handwritten_source'] = handwritten_sql
        result['handwritten'] = {
            'char_length': character_length(handwritten_sql),
            'technical_noise': technical_noise(handwritten_sql, False),
            'domain_transparency': domain_transparency(handwritten_sql, False),
            'nesting_depth': nesting_depth(handwritten_sql),
            'halstead_volume': halstead_volume(handwritten_sql, SQL_OPERATORS),
            'fk_error_opportunities': fk_error_opportunities(handwritten_sql, False),
            'extrinsic_load': extrinsic_cognitive_load(handwritten_sql, False),
            'cognitive_complexity': hw_cc['total'],
            'cognitive_breakdown': hw_cc,
        }
        result['shared']['abstraction_ratio_handwritten'] = abstraction_ratio(
            eql_source, handwritten_sql
        )
        result['shared']['translator_overhead_ratio'] = translator_overhead_ratio(
            handwritten_sql, sql_source
        )

    return result


def print_analysis(result: dict) -> None:
    """
    Pretty-print a single analyze() result — used by the notebook right after
    each query is run, so the metrics for a query sit next to its EQL/SQL
    source instead of only appearing in one big table at the end.
    """
    print(f'--- {result["name"]} ---')
    print('EQL:')
    print('  ' + result['eql_source'].replace('\n', '\n  '))
    print(f'SQL (translator): {result["sql_source"]}')
    if 'handwritten' in result:
        print(f'SQL (handwritten): {result["handwritten_source"]}')
    print()
    header = f'{"":22} {"EQL":>10} {"SQL":>10}'
    if 'handwritten' in result:
        header += f' {"Handwritten":>12}'
    print(header)
    rows = [
        ('char_length', 'Char length'),
        ('technical_noise', 'Technical noise'),
        ('domain_transparency', 'Domain transparency'),
        ('nesting_depth', 'Nesting depth'),
        ('halstead_volume', 'Halstead volume'),
        ('fk_error_opportunities', 'FK error opportunities'),
        ('extrinsic_load', 'Extrinsic load'),
        ('cognitive_complexity', 'Cognitive complexity'),
    ]
    for key, label in rows:
        line = f'{label:<22} {result["eql"][key]:>10} {result["sql"][key]:>10}'
        if 'handwritten' in result:
            line += f' {result["handwritten"][key]:>12}'
        print(line)
    print(f'\nAbstraction ratio (SQL/EQL):        {result["shared"]["abstraction_ratio"]}x')
    if 'handwritten' in result:
        print(
            f'Abstraction ratio (Handwritten/EQL): '
            f'{result["shared"]["abstraction_ratio_handwritten"]}x'
        )
        print(
            f'Translator overhead (SQL/Handwritten): '
            f'{result["shared"]["translator_overhead_ratio"]}x'
        )
    print()


# =============================================================================
# Container-chain builder for multi-point scaling demonstrations
# =============================================================================

def eql_source_for_chain(k: int) -> str:
    """
    Readable EQL source string for a linear chain of k containers connected
    by (k - 1) FixedConnections (C0 -- FC0 -- C1 -- FC1 -- ... -- C(k-1)).
    Total query variables = 2k - 1. Pairs with `build_container_chain` in the
    notebook's dataset-setup module, so the same shape can be measured at
    several chain lengths instead of only two.

    The source includes the `variable(...)` declarations, consistent with
    EQL_SOURCES.

    :param k: Number of containers in the chain (k >= 2)
    :return: EQL source string
    """
    c_names = [f'C{i}' for i in range(k)]
    fc_names = [f'FC{i}' for i in range(k - 1)]
    declarations = [
        f'{name} = variable(Container, domain=world.bodies)' for name in c_names
    ] + [
        f'{name} = variable(FixedConnection, domain=world.connections)'
        for name in fc_names
    ]
    conditions = []
    for i in range(k - 1):
        conditions.append(f'{c_names[i]} == {fc_names[i]}.parent')
        conditions.append(f'{c_names[i + 1]} == {fc_names[i]}.child')
    all_vars = ', '.join(c_names + fc_names)
    where_clause = ', '.join(conditions)
    query = f'an(set_of({all_vars}).where({where_clause}))'
    return '\n'.join(declarations + [query])
