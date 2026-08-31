"""
Readability and complexity analysis comparing EQL queries to their SQL equivalents.

This is a notebook-safe extract of test_eql_readability.py: it contains only
the pure metric functions and the analyze() helper. All pytest-dependent
test_* functions (which require the `session` fixture from conftest.py) have
been removed, since they cannot run outside the pytest test suite.

IMPORTANT: This module does NOT test the correctness of the EQL-to-SQL translation.
Translation correctness is verified in test_eql.py. This module only measures the
readability and complexity properties of the query expressions themselves.

Scientific foundations:
- Halstead (1977): Software Science — information-theoretic complexity measures
- McCabe (1976): A Complexity Measure — cyclomatic complexity
- Campbell (2018): Cognitive Complexity (SonarSource) — human-oriented complexity
- Sweller (1988): Cognitive Load Theory — intrinsic vs extrinsic cognitive load
- Baddeley (1974): Working Memory Model — capacity limits of working memory
- Miller (1956): The Magical Number Seven — information chunking in memory
- Lawrie et al. (2006): Identifier quality and cognitive load
- Eichberg et al. (2008): Error-prone constructs in software
- Fowler (2010): Domain-Specific Languages
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

    :param source: Query source string
    :return: Non-whitespace character count
    """
    return len(re.sub(r'\s+', '', source))


# =============================================================================
# Metric 2: Technical Noise
# =============================================================================

SQL_TECHNICAL_PATTERNS = re.compile(
    r'(_id\b|DAO\b|AS\s+\w+|database_id|polymorphic_type)'
)

EQL_TECHNICAL_PATTERNS = re.compile(
    r'(domain=\[\]|type_=|domain=world\.|variable\()'
)


def technical_noise(source: str, is_eql: bool) -> int:
    """
    Count tokens that carry no domain meaning.

    Rationale: infrastructure tokens like _id, DAO suffixes, and AS aliases
    must be mentally filtered by the reader to extract the domain intent.
    Based on Identifier Quality research (Lawrie et al., 2006).

    :param source: Query source string
    :param is_eql: True if EQL, False if SQL
    :return: Count of technical tokens
    """
    pattern = EQL_TECHNICAL_PATTERNS if is_eql else SQL_TECHNICAL_PATTERNS
    return len(pattern.findall(source))


# =============================================================================
# Metric 3: Domain Transparency
# =============================================================================

_INFRASTRUCTURE_TOKENS = {
    'DAO', 'AS', 'ON', 'JOIN', 'SELECT', 'FROM', 'WHERE',
    'AND', 'OR', 'WITH', 'IN', 'IS', 'NOT', 'NULL',
    'database_id', 'polymorphic_type',
}


def domain_transparency(source: str) -> float:
    """
    Ratio of domain-meaningful words to all words.

    Rationale: a query with high domain transparency can be understood
    purely from domain knowledge. Based on Fowler (2010).

    :param source: Query source string
    :return: Ratio between 0.0 and 1.0
    """
    words = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', source)
    if not words:
        return 0.0
    domain_words = [
        w for w in words
        if not any(t in w for t in _INFRASTRUCTURE_TOKENS)
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


def halstead_volume(source: str, operators: list) -> float:
    """
    Halstead volume: N * log2(n).

    From Halstead (1977): measures information density in working memory.

    :param source: Query source string
    :param operators: Operator tokens for this language
    :return: Halstead volume
    """
    source_upper = source.upper()
    unique_operators = sum(1 for op in operators if op.upper() in source_upper)
    total_operators = sum(source_upper.count(op.upper()) for op in operators)
    operands = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', source)
    unique_operands = len(set(operands))
    total_operands = len(operands)
    vocabulary = unique_operators + unique_operands
    length = total_operators + total_operands
    if vocabulary <= 1:
        return 0.0
    return round(length * math.log2(vocabulary), 2)


# =============================================================================
# Metric 6: Abstraction Ratio
# =============================================================================

def abstraction_ratio(eql_source: str, sql_source: str) -> float:
    """
    SQL characters generated per EQL character.

    Measures how much infrastructure complexity EQL hides from the user.

    :param eql_source: EQL query source
    :param sql_source: Generated SQL
    :return: SQL length / EQL length
    """
    eql_len = character_length(eql_source)
    sql_len = character_length(sql_source)
    if eql_len == 0:
        return 0.0
    return round(sql_len / eql_len, 1)


# =============================================================================
# Metric 7: Foreign Key Error Opportunities
# =============================================================================

def fk_error_opportunities(source: str, is_eql: bool) -> int:
    """
    Number of places where a foreign key mistake could be introduced.

    In SQL every ON clause can have the wrong column name.
    EQL never exposes foreign keys. Based on Eichberg et al. (2008).

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
    Count tokens that represent extrinsic cognitive load.

    Based on Sweller (1988) Cognitive Load Theory. Baddeley (1974) and
    Miller (1956): working memory capacity is ~7±2 chunks.

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
    """
    sql_upper = sql.upper()
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
    while i < len(sql):
        if sql[i] == '(':
            depth += 1
        elif sql[i] == ')':
            depth -= 1
        elif sql[i:i+5].upper() == ' JOIN' and depth > 0:
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
# Expressiveness coverage
# =============================================================================

_EQL_UNSUPPORTED = [
    "Subquery in SELECT clause",
    "UNION / INTERSECT / EXCEPT",
    "Window functions (ROW_NUMBER, RANK)",
    "INSERT / UPDATE / DELETE",
    "Multiple aggregations with different FILTER conditions",
]

_TOTAL_SQL_FEATURES = 20


def expressiveness_coverage() -> float:
    """
    Fraction of common SQL features EQL can currently express.

    :return: Supported fraction (0.0 to 1.0)
    """
    return round((_TOTAL_SQL_FEATURES - len(_EQL_UNSUPPORTED)) / _TOTAL_SQL_FEATURES, 2)


# =============================================================================
# Combined analysis
# =============================================================================

def analyze(name: str, eql_source: str, sql_source: str) -> dict:
    """
    Run all metrics for an EQL/SQL query pair.

    :param name: Human-readable query name
    :param eql_source: EQL query as source string
    :param sql_source: Equivalent SQL string
    :return: Full analysis result dict
    """
    eql_cc = cognitive_complexity_eql(eql_source)
    sql_cc = cognitive_complexity_sql(sql_source)
    return {
        'name': name,
        'eql_source': eql_source,
        'sql_source': sql_source,
        'eql': {
            'char_length': character_length(eql_source),
            'technical_noise': technical_noise(eql_source, True),
            'domain_transparency': domain_transparency(eql_source),
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
            'domain_transparency': domain_transparency(sql_source),
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
