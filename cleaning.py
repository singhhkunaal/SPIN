"""
V9 vendor name cleaning pipeline.
Extracted verbatim from the original script — logic unchanged.
"""

import re
import unicodedata
from collections import Counter
from rapidfuzz import process, fuzz

# ---------------------------------------------------------------------------
# Cleaning config
# ---------------------------------------------------------------------------
URL_PREFIXES = re.compile(r'^(https?://|www\.)', re.IGNORECASE)
PAYMENT_PREFIXES = re.compile(
    r'^(APLPAY|APL|TST|SQ|SP|PP|PAYPAL|STRIPE|SQSP|CLOVER|TOAST)\s*\*\s*',
    re.IGNORECASE
)
DOMAIN_SUFFIXES = ['.co.in', '.com', '.in', '.net', '.org', '.io', '.co', '.ca', '.us']

LEGAL_SUFFIXES = [
    'PVT LTD', 'PVT. LTD.', 'PRIVATE LIMITED', 'PUBLIC LIMITED',
    'LIMITED', 'LTD', 'LLC', 'INC', 'CORP', 'CORPORATION',
    'GMBH', 'LLP', 'PLC', 'INCORPORATED', 'OPC', 'PROPRIETORSHIP',
    'LP', 'LTD CO', 'CO LTD', 'PLLC', 'PC', 'DBA', 'TA',
]

ABBREVIATION_MAP = {
    # Tech
    'AMZN': 'AMAZON', 'MSFT': 'MICROSOFT', 'GOOG': 'GOOGLE',
    'GOOGL': 'GOOGLE', 'AAPL': 'APPLE', 'META': 'META',
    'NFLX': 'NETFLIX', 'UBER': 'UBER', 'LYFT': 'LYFT',
    'TWTR': 'TWITTER', 'SNAP': 'SNAPCHAT', 'ADBE': 'ADOBE',
    'CRM': 'SALESFORCE', 'ORCL': 'ORACLE', 'IBM': 'IBM',
    'INTC': 'INTEL', 'NVDA': 'NVIDIA', 'AMD': 'AMD',
    'CSCO': 'CISCO', 'ZOOM': 'ZOOM', 'DOCU': 'DOCUSIGN',
    'NOW': 'SERVICENOW', 'WDAY': 'WORKDAY', 'SHOP': 'SHOPIFY',
    # Retail
    'WMT': 'WALMART', 'TGT': 'TARGET', 'COST': 'COSTCO',
    'HD': 'HOME DEPOT', 'LOW': 'LOWES', 'EBAY': 'EBAY',
    'BBY': 'BEST BUY', 'KR': 'KROGER', 'WBA': 'WALGREENS',
    'CVS': 'CVS', 'DLTR': 'DOLLAR TREE', 'DG': 'DOLLAR GENERAL',
    # Food & Beverage
    'MCD': 'MCDONALDS', 'SBUX': 'STARBUCKS', 'YUM': 'YUM BRANDS',
    'CMG': 'CHIPOTLE', 'DPZ': 'DOMINOS', 'QSR': 'RESTAURANT BRANDS',
    'DNUT': 'DUNKIN', 'KO': 'COCA COLA', 'PEP': 'PEPSICO',
    'MDLZ': 'MONDELEZ', 'GIS': 'GENERAL MILLS', 'CPB': 'CAMPBELL SOUP',
    'HSY': 'HERSHEY', 'SYY': 'SYSCO',
    # Logistics
    'UPS': 'UPS', 'FDX': 'FEDEX', 'USPS': 'USPS',
    'XPO': 'XPO LOGISTICS', 'ODFL': 'OLD DOMINION', 'CHRW': 'CH ROBINSON',
    # Financial
    'JPM': 'JP MORGAN', 'BAC': 'BANK OF AMERICA', 'WFC': 'WELLS FARGO',
    'GS': 'GOLDMAN SACHS', 'MS': 'MORGAN STANLEY',
    'AXP': 'AMERICAN EXPRESS', 'V': 'VISA', 'MA': 'MASTERCARD',
    'PYPL': 'PAYPAL', 'SQ': 'SQUARE',
    # Healthcare
    'JNJ': 'JOHNSON AND JOHNSON', 'PFE': 'PFIZER', 'MRK': 'MERCK',
    'ABT': 'ABBOTT', 'UNH': 'UNITEDHEALTH', 'MCK': 'MCKESSON',
    'CAH': 'CARDINAL HEALTH',
    # Energy & Industrial
    'XOM': 'EXXON MOBIL', 'CVX': 'CHEVRON', 'GE': 'GENERAL ELECTRIC',
    'HON': 'HONEYWELL', 'MMM': '3M', 'CAT': 'CATERPILLAR',
    'DE': 'JOHN DEERE', 'EMR': 'EMERSON',
    # Telecom
    'T': 'AT AND T', 'VZ': 'VERIZON', 'TMUS': 'T MOBILE',
    'CMCSA': 'COMCAST', 'CHTR': 'CHARTER',
    # Travel & Hospitality
    'MAR': 'MARRIOTT', 'HLT': 'HILTON', 'H': 'HYATT',
    'DAL': 'DELTA', 'UAL': 'UNITED AIRLINES', 'AAL': 'AMERICAN AIRLINES',
    'LUV': 'SOUTHWEST', 'ABNB': 'AIRBNB',
}

GEOGRAPHIC_IDENTIFIERS = {
    # US States
    'ALABAMA', 'ALASKA', 'ARIZONA', 'ARKANSAS', 'CALIFORNIA',
    'COLORADO', 'CONNECTICUT', 'DELAWARE', 'FLORIDA', 'GEORGIA',
    'HAWAII', 'IDAHO', 'ILLINOIS', 'INDIANA', 'IOWA',
    'KANSAS', 'KENTUCKY', 'LOUISIANA', 'MAINE', 'MARYLAND',
    'MASSACHUSETTS', 'MICHIGAN', 'MINNESOTA', 'MISSISSIPPI', 'MISSOURI',
    'MONTANA', 'NEBRASKA', 'NEVADA', 'NEW HAMPSHIRE', 'NEW JERSEY',
    'NEW MEXICO', 'NEW YORK', 'NORTH CAROLINA', 'NORTH DAKOTA', 'OHIO',
    'OKLAHOMA', 'OREGON', 'PENNSYLVANIA', 'RHODE ISLAND', 'SOUTH CAROLINA',
    'SOUTH DAKOTA', 'TENNESSEE', 'TEXAS', 'UTAH', 'VERMONT',
    'VIRGINIA', 'WASHINGTON', 'WEST VIRGINIA', 'WISCONSIN', 'WYOMING',
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
    'ALBERTA', 'BRITISH COLUMBIA', 'MANITOBA', 'NEW BRUNSWICK',
    'NEWFOUNDLAND', 'NOVA SCOTIA', 'ONTARIO', 'PRINCE EDWARD ISLAND',
    'QUEBEC', 'SASKATCHEWAN', 'NORTHWEST TERRITORIES', 'NUNAVUT', 'YUKON',
    'TORONTO', 'VANCOUVER', 'MONTREAL', 'CALGARY', 'EDMONTON',
    'NEW YORK', 'LOS ANGELES', 'CHICAGO', 'HOUSTON', 'PHOENIX',
    'PHILADELPHIA', 'SAN ANTONIO', 'SAN DIEGO', 'DALLAS', 'SAN JOSE',
    'AUSTIN', 'JACKSONVILLE', 'SEATTLE', 'DENVER', 'BOSTON',
    'NASHVILLE', 'PORTLAND', 'MIAMI', 'ATLANTA', 'MINNEAPOLIS',
}

PROTECTED_SHORT_TOKENS = {'CO', 'OF', 'AT', 'BY', 'IN', 'ON', 'UP', 'US', 'GO'}
MIN_LENGTH = 5
MAX_PASSES = 2
FUZZY_THRESHOLD = 95


# ---------------------------------------------------------------------------
# Core cleaning primitives
# ---------------------------------------------------------------------------
def normalise_accents(name: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFD', name)
        if unicodedata.category(c) != 'Mn'
    )


def strip_url_and_domains(name: str) -> str:
    name = URL_PREFIXES.sub('', name.strip())
    for suffix in DOMAIN_SUFFIXES:
        name = re.sub(re.escape(suffix), '', name, flags=re.IGNORECASE)
    return name


def strip_payment_prefixes(name: str) -> str:
    return PAYMENT_PREFIXES.sub('', name).strip()


def apply_char_whitelist(name: str) -> str:
    name = name.replace('&', ' AND ')
    name = name.replace("'", '')
    name = name.upper()
    name = name.replace('-', ' ')
    name = re.sub(r'[^A-Z0-9 ]', ' ', name)
    return name


def normalise_ws(name: str) -> str:
    return re.sub(r'\s+', ' ', name).strip()


def split_concat_alphanum(name: str) -> str:
    name = re.sub(r'([A-Z])(\d)', r'\1 \2', name)
    return normalise_ws(name)


def strip_legal_suffixes(name: str) -> str:
    changed = True
    while changed:
        changed = False
        for suffix in sorted(LEGAL_SUFFIXES, key=len, reverse=True):
            pattern = r'\b' + re.escape(suffix) + r'\.?\s*$'
            new_name = re.sub(pattern, '', name, flags=re.IGNORECASE).strip().rstrip(',. ')
            if new_name != name:
                name = new_name
                changed = True
    return name


def apply_min_length(stripped: str, before_strip: str) -> str:
    if len(stripped.replace(' ', '')) < MIN_LENGTH:
        return before_strip
    return stripped


def expand_abbreviation(name: str) -> str:
    name_no_nums = normalise_ws(re.sub(r'\b\d+\b', '', name))
    return ABBREVIATION_MAP.get(name_no_nums, name)


def make_match_key(name: str) -> str:
    key = re.sub(r'^THE\s+', '', name, flags=re.IGNORECASE)
    key = key.replace('-', ' ')
    return normalise_ws(key).upper()


def clean_single(raw: str) -> str:
    if not raw or not str(raw).strip():
        return ''
    name = str(raw).strip()
    name = normalise_accents(name)
    name = strip_url_and_domains(name)
    name = strip_payment_prefixes(name)
    name = apply_char_whitelist(name)
    name = normalise_ws(name.upper())
    name = split_concat_alphanum(name)
    pre_legal = name
    name = strip_legal_suffixes(name)
    name = normalise_ws(name)
    name = apply_min_length(name, pre_legal)
    name = normalise_ws(name)
    name = expand_abbreviation(name)
    return normalise_ws(name)


def _is_trailing_noise_token(token: str) -> bool:
    if token in PROTECTED_SHORT_TOKENS:
        return False
    t = token.replace('-', '')
    if not t:
        return True
    if re.match(r"^\d+$", t):
        return True
    if re.match(r"^[A-Z0-9]+$", t) and re.search(r"[A-Z]", t) and re.search(r"\d", t):
        return True
    if len(t) <= 2 and re.search(r"\d", t):
        return True
    return False


def _is_candidate_short_alpha_token(token: str) -> bool:
    if token in PROTECTED_SHORT_TOKENS:
        return False
    t = token.replace("-", "")
    return bool(t) and len(t) <= 2 and bool(re.match(r"^[A-Z]+$", t))


def _strip_one_trailing_token(name: str) -> str:
    tokens = name.split()
    if len(tokens) > 1 and _is_trailing_noise_token(tokens[-1]):
        return normalise_ws(' '.join(tokens[:-1]))
    return name


def iterative_strip(name: str) -> str:
    current = name
    for _ in range(10):
        prev = current
        current = _strip_one_trailing_token(current)
        current = normalise_ws(current)
        if current == prev:
            break
        if len(current.replace(' ', '')) < MIN_LENGTH:
            return prev
    return current


def apply_batch_strip_and_group(cleaned_names: list) -> tuple:
    existing_counts = Counter(n for n in cleaned_names if n)
    pass_a = {}
    for name in cleaned_names:
        if not name:
            continue
        candidate = iterative_strip(name)
        candidate = strip_legal_suffixes(candidate)
        candidate = normalise_ws(candidate)
        candidate = apply_min_length(candidate, name)
        if candidate != name and len(candidate.replace(" ", "")) >= MIN_LENGTH:
            pass_a[name] = candidate

    pass_a_counts = Counter(pass_a.values())
    record_candidates = {}
    candidate_counts = Counter()

    for name in cleaned_names:
        if not name:
            continue
        candidate = pass_a.get(name, name)
        tokens = candidate.split()
        if tokens and _is_candidate_short_alpha_token(tokens[-1]):
            freq_at_candidate = pass_a_counts.get(candidate, 0) + existing_counts.get(candidate, 0)
            if freq_at_candidate < 2:
                further = normalise_ws(" ".join(tokens[:-1]))
                if further and len(further.replace(" ", "")) >= MIN_LENGTH:
                    further = iterative_strip(further)
                    further = strip_legal_suffixes(further)
                    further = normalise_ws(further)
                    ftokens = further.split()
                    if ftokens and _is_candidate_short_alpha_token(ftokens[-1]):
                        further2 = normalise_ws(" ".join(ftokens[:-1]))
                        if further2 and len(further2.replace(" ", "")) >= MIN_LENGTH:
                            further2 = iterative_strip(further2)
                            further = further2 if further2 else further
                    candidate = further if further else candidate

        if candidate != name and len(candidate.replace(" ", "")) >= MIN_LENGTH:
            record_candidates[name] = candidate
            candidate_counts[candidate] += 1

    resolved = {}
    for name, candidate in record_candidates.items():
        total = candidate_counts[candidate] + existing_counts.get(candidate, 0)
        if total >= 2:
            resolved[name] = candidate

    result = [resolved.get(n, n) for n in cleaned_names]
    return result, set()


def apply_match_key_grouping(cleaned_names: list) -> list:
    match_key_map = {}
    for name in cleaned_names:
        if not name:
            continue
        mk = make_match_key(name)
        match_key_map.setdefault(mk, []).append(name)

    canonical_map = {}
    for mk, variants in match_key_map.items():
        if len(variants) >= 2:
            freq = Counter(variants)
            canonical = max(freq.keys(), key=lambda v: (freq[v], v.count('-')))
            canonical_map[mk] = canonical

    return [canonical_map.get(make_match_key(n), n) if n else n for n in cleaned_names]


def clean_batch_v9(raw_names: list) -> list:
    cleaned = [clean_single(n) for n in raw_names]
    for _ in range(MAX_PASSES):
        prev = cleaned[:]
        cleaned, _ = apply_batch_strip_and_group(cleaned)
        cleaned = apply_match_key_grouping(cleaned)
        if cleaned == prev:
            break
    final = []
    for i, name in enumerate(cleaned):
        if name:
            mk = make_match_key(name)
            if mk in GEOGRAPHIC_IDENTIFIERS:
                name = clean_single(raw_names[i])
        final.append(normalise_ws(name) if name else '')
    return final


# ---------------------------------------------------------------------------
# Fuzzy grouping
# ---------------------------------------------------------------------------
def get_best_match(vendor: str, choices: list):
    if not choices:
        return None, 0
    match1, score1, _ = process.extractOne(vendor, choices, scorer=fuzz.token_sort_ratio)
    match2, score2, _ = process.extractOne(vendor, choices, scorer=fuzz.token_set_ratio)
    if max(score1, score2) > FUZZY_THRESHOLD:
        return (match1 if score1 > score2 else match2), max(score1, score2)
    return None, 0


def group_vendors(vendors: list) -> dict:
    grouped = {}
    canonical = []
    for vendor in vendors:
        match, score = get_best_match(vendor, canonical)
        if match:
            grouped[vendor] = match
        else:
            canonical.append(vendor)
            grouped[vendor] = vendor
    return grouped
