"""
Data Extraction Module
Parse OCR text → Structured vaccine data
"""

import re
from typing import Dict, Optional
from datetime import datetime


def clean_text(text: str) -> str:
    """Clean and normalize text"""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special chars except letters, numbers, spaces, /()-
    text = re.sub(r'[^\w\s/()-]', '', text)
    return text.strip()


def normalize_ocr_text(text: str) -> str:
    """
    Normalize common OCR mistakes to improve extraction accuracy.

    Fixes included (case-insensitive):
    - common misreads of 'MFG' (e.g., 'HLFG', 'HIFG') -> 'MFG'
    - month typos like 'JAM' -> 'JAN'
    - stray characters in years like '&' -> '4'
    - 'SCR' -> 'SER' when used before numbers
    - collapses multiple spaces and uppercases text for downstream regex
    """
    if not text:
        return text

    t = text.upper()

    # Simple replacements for common OCR errors
    replacements = {
        'HLFG': 'MFG',
        'HIFG': 'MFG',
        'MIFG': 'MFG',
        'MIFG:': 'MFG:',
        'JAM': 'JAN',
        'J A M': 'JAN',
        'J A N': 'JAN',
        'J U N': 'JUN',
        'J U L': 'JUL',
        '\\&': '4',
        '&': '4',
        'SCR ': 'SER ',
        'SET ': 'SER ',
        'RAY': 'MAY',
        'R O V': 'NOV',
        'ROV': 'NOV',
        'R0V': 'NOV',
        'AO': 'APR',
        'A0': 'APR',
    }

    # Additional domain-specific fixes (brands, registration typos)
    domain_replacements = {
        'DEFERUSOR': 'DEFENSOR',
        'DEFERUSO': 'DEFENSOR',
        'DEFERUSOR 3': 'DEFENSOR 3',
        'DEFERRUSOR': 'DEFENSOR',
        'ZORTS': 'ZOETIS',
        'ZORTS INC': 'ZOETIS INC',
        'CEFENSOR': 'DEFENSOR',
        'DEFENSOR 3  ': 'DEFENSOR 3 ',
        'DEFENSOR3': 'DEFENSOR 3',
        'FEUOCELL': 'FELOCELL',
        'FEUOKCELL': 'FELOCELL',
        'RSG': 'REG',
        'RGS': 'REG',
        'RS G': 'REG',
        ' REG NO IF ': ' REG NO 1F ',
        ' REG NO IF': ' REG NO 1F',
        ' IF ': ' 1F ',
        ' I F ': ' 1F ',
    }

    for k, v in domain_replacements.items():
        t = t.replace(k, v)

    for k, v in replacements.items():
        t = t.replace(k, v)

    # More tolerant month / common OCR mistakes
    t = t.replace('OOT', 'OCT')
    t = t.replace('0CT', 'OCT')
    t = t.replace('O0T', 'OCT')
    t = t.replace('O0CT', 'OCT')
    t = t.replace('FEUOCELL', 'FELOCELL')
    t = t.replace('FEUOKCELL', 'FELOCELL')
    t = t.replace('RAY', 'MAY')
    t = t.replace('ROV', 'NOV')
    t = t.replace('R0V', 'NOV')
    t = t.replace('AO', 'APR')
    t = t.replace('A0', 'APR')

    # Remove weird punctuation that may have survived
    t = re.sub(r"[^A-Z0-9\s/():-]", '', t)

    # Collapse spaces
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def normalize_serial(raw: str) -> str:
    """Normalize serial-like strings using quick heuristics.

    - Removes non-alphanumeric chars
    - If majority are digits, convert common letter misreads (S->5, O->0, I/L->1)
    - If majority are letters, keep letters but strip ambiguous digits
    """
    if not raw:
        return raw
    s = re.sub(r'[^A-Z0-9]', '', raw.upper())
    if not s:
        return raw

    digits = sum(c.isdigit() for c in s)
    letters = sum(c.isalpha() for c in s)

    # If mixed or mostly digits, convert likely OCR letter misreads to digits
    if digits >= letters or (digits > 0 and letters > 0):
        s = s.replace('S', '5').replace('O', '0').replace('I', '1').replace('L', '1')
    else:
        # If mostly letters, avoid turning letters into digits accidentally
        s = s.replace('0', 'O')

    return s


def extract_vaccine_name(text: str) -> Optional[str]:
    """
    Extract vaccine name from left region text
    
    Patterns:
    - "Rabies Vaccine"
    - "Nobivac Rabies"
    - "Felocell"
    """
    t = text.upper()

    # Look for common vaccine components (tolerant)
    components = []
    # Rabies is common and should be detected explicitly
    if 'RABIES VACCINE' in t or 'RABIES' in t:
        components.append('Rabies Vaccine')
    if 'FELINE RHINOTRACHEITIS' in t or 'RHINOTRACHEITIS' in t:
        components.append('Feline Rhinotracheitis')
    if 'CALICI' in t or 'PANLEUKOPENIA' in t or 'PANLCUKOPENIA' in t:
        components.append('Calici-Panleukopenia')
    if 'CHLAMYDIA' in t or 'PSITTACI' in t or 'PSITTACH' in t:
        components.append('Chlamydia psittaci')

    if components:
        return '; '.join(components)

    # Fallback: brand/keywords (include common OCR variants)
    match = re.search(r'(NOBIVAC|DEFENSOR|FELOCELL|FEUOCELL|FEUOKCELL|CEFENSOR)\s*\d*', t)
    if match:
        prod = match.group(0).strip()
        # normalize obvious OCR brand typos
        prod = prod.replace('FEUOCELL', 'FELOCELL').replace('FEUOKCELL', 'FELOCELL').replace('CEFENSOR', 'DEFENSOR')
        return prod

    return None


def extract_product_name(text: str) -> Optional[str]:
    """
    Extract product/brand name
    
    Examples:
    - DEFENSOR 3
    - NOBIVAC RABIES
    - FELOCELL 4
    """
    t = text.upper()

    # include common OCR variants of FELOCELL/FEUOCELL/FEUOKCELL and DEFERUSOR/DEFERUSO/CEFENSOR
    match = re.search(r'(DEFENSOR|DEFERUSOR|DEFERUSO|CEFENSOR|NOBIVAC|FELOCELL|FEUOCELL|FEUOKCELL|FEUOKCELL|FEU O K|RABISIN)\s*[TM]*\s*\d*', t)
    if match:
        prod = match.group(0).strip()
        # normalize common typos
        prod = prod.replace('DEFERUSOR', 'DEFENSOR').replace('DEFERUSO', 'DEFENSOR').replace('CEFENSOR', 'DEFENSOR')
        prod = prod.replace('FEUOCELL', 'FELOCELL').replace('FEUOKCELL', 'FELOCELL').replace('FEU O K', 'FELOCELL')
        return prod

    return None


def extract_manufacturer(text: str) -> Optional[str]:
    """
    Extract manufacturer
    
    Examples:
    - Zoetis Inc.
    - Boehringer Ingelheim
    - Intervet
    """
    text_upper = text.upper()
    
    manufacturers = [
        ('ZOETIS', 'Zoetis Inc.'),
        ('BOEHRINGER', 'Boehringer Ingelheim'),
        ('INTERVET', 'Intervet'),
        ('MERIAL', 'Merial'),
    ]
    
    for keyword, full_name in manufacturers:
        if keyword in text_upper:
            return full_name
    
    # Try to find "Inc." pattern
    match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Inc\.?', text)
    if match:
        return match.group(0)
    
    return None


def extract_registration_number(text: str) -> Optional[str]:
    """
    Extract registration number
    
    Patterns:
    - Reg No 1F 2/56 (B)
    - Reg No. IF 2/56
    - 1F 2/56 (B)
    """
    t = text.upper()

    # Prefer Pattern 1: explicit 'REG' / 'REG NO' nearby (highest confidence)
    match = re.search(r'(?:REG(?:ISTER|ISTRATION)?\s*(?:NO|NO\.?|NO:?)?)\s*[:\-]?\s*([A-Z0-9\s/()\-]{2,30})', t, re.IGNORECASE)
    if match:
        val = clean_text(match.group(1))
        # truncate at common following labels (avoid swallowing extra lines)
        val = re.split(r'\b(?:SERIAL|SER|S/N|MFG|EXP|MANU|MANUFACT|DATE)\b', val)[0].strip()
        # strip trailing noisy tokens like 'SER', 'SET', 'S/N', 'SERIAL'
        val = re.sub(r'\b(SER|SET|S/N|SERIAL)\b\s*$', '', val).strip()
        formatted = format_registration_number(val)
        return formatted

    # If there's an explicit 'REG' token, try to capture a registration in the nearby window after it
    reg_token = re.search(r'(REG(?:ISTER|ISTRATION)?\s*(?:NO|NO\.?|NO:?)?)', t)
    if reg_token:
        start = reg_token.end()
        window = t[start:start+80]
        match = re.search(r'([A-Z0-9]{1,3})[\s/\-]?(\d{1,6}(?:/\d{1,4})?)(?:\s*\([A-Z0-9 ]+\))?', window)
        if match:
            parts = [p for p in match.groups() if p]
            val = clean_text(' '.join(parts))
            val = re.sub(r'\b(SER|SET|S/N|SERIAL)\b\s*$', '', val).strip()
            formatted = format_registration_number(val)
            return formatted

    # Last-resort fallback (lower confidence): capture letter+digits pairs anywhere
    # Try to capture slash-style registrations anywhere (e.g., 2F18/59)
    m_frac = re.search(r'([0-9]{1,3}/[0-9]{1,3})', t)
    if m_frac:
        frac = m_frac.group(1)
        prefix_raw = t[:m_frac.start()].strip()
        prefix = re.sub(r'[^A-Z0-9]', '', prefix_raw)
        if not prefix:
            toks = re.split(r'\s+', prefix_raw)
            prefix = re.sub(r'[^A-Z0-9]', '', toks[-1]) if toks else ''
        val = (f"{prefix} {frac}" if prefix else frac).strip()
        val = re.sub(r'\b(SER|SET|S/N|SERIAL)\b\s*$', '', val).strip()
        formatted = format_registration_number(val)
        return formatted

    # Last-resort fallback (lower confidence): capture letter+digits pairs anywhere
    match = re.search(r'\b([A-Z]{1,4})\s*(\d{2,6})(?:\s*\([A-Z0-9 ]+\))?', t)
    if match:
        prefix = match.group(1)
        # Ignore common serial-like prefixes that OCR may misread as registration
        if prefix in ('SCR', 'SER', 'SN', 'S/N', 'SERIAL'):
            return None
        parts = [p for p in match.groups() if p]
        val = clean_text(' '.join(parts))
        val = re.sub(r'\b(SER|SET|S/N|SERIAL)\b\s*$', '', val).strip()
        formatted = format_registration_number(val)
        return formatted

    return None


def format_registration_number(raw: str) -> Optional[str]:
    """
    Normalize registration numbers to a canonical form like:
      - '2F18/59 (B)' -> '2F 18/59 (B)'
      - '2F 18/59' -> '2F 18/59'
      - 'L 5321' -> 'L 5321'
      - 'NE 190' -> 'NE 190'

    The function uppercases, strips noise, and tries to place a space
    between alpha-prefix and numeric part and preserves any trailing
    parenthetical suffix.
    """
    if not raw:
        return None
    s = raw.upper().strip()
    # Remove common noise
    s = re.sub(r'[^A-Z0-9/()\s]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()

    # Extract trailing parenthetical, e.g., (B)
    paren = None
    m_paren = re.search(r'\(([A-Z0-9\- ]+)\)\s*$', s)
    if m_paren:
        paren = m_paren.group(1).strip()
        s = s[:m_paren.start()].strip()

    # If there is a fraction-like part (NN/NN) somewhere, isolate it and
    # treat everything before it as the prefix (cleaned).
    m_frac = re.search(r'([0-9]{1,3}/[0-9]{1,3})', s)
    if m_frac:
        frac = m_frac.group(1)
        prefix_raw = s[:m_frac.start()].strip()
        prefix = re.sub(r'[^A-Z0-9]', '', prefix_raw)
        if not prefix:
            # fallback to first token before frac
            toks = re.split(r'\s+', s[:m_frac.start()].strip())
            prefix = re.sub(r'[^A-Z0-9]', '', toks[-1]) if toks else ''
        out = f"{prefix} {frac}" if prefix else frac
        if paren:
            out = f"{out} ({paren})"
        return out

    # Try pattern: prefix + number (no slash)
    m2 = re.search(r'^([A-Z]{1,3})\s*([0-9]{2,6})$', s)
    if m2:
        # We may see patterns like: 'ZF 18159' (no slash) where OCR missed '/'.
        # Apply reconstruction for 2-letter prefixes by inserting a slash
        # at the 3rd digit (i.e., split after 2 digits): '18159' -> '18/159'
        prefix = m2.group(1)
        number = m2.group(2)

        # If prefix is 2 letters and numeric run is length 3..5, reconstruct
        if len(prefix) == 2 and len(number) >= 4:
            # New rule: N1 = first 2 digits, N2 = last 2 digits. Drop middle digits as noise.
            # Normalize numeric run: correct common letter→digit OCR errors
            conv = str.maketrans({'O': '0', 'Q': '0', 'D': '0', 'S': '5', 'Z': '2', 'I': '1', 'L': '1', 'B': '8', 'G': '6'})
            num_norm = number.translate(conv)

            # Also attempt to fix prefix first-char if it's a letter but likely a digit
            p0 = prefix[0]
            p1 = prefix[1]
            prefix_conv = prefix
            if not p0.isdigit():
                p0_conv_map = {'Z': '2', 'O': '0', 'Q': '0', 'S': '5', 'I': '1', 'L': '1', 'B': '8', 'G': '6'}
                if p0 in p0_conv_map:
                    prefix_conv = p0_conv_map[p0] + p1

            # Ensure numeric normalization yielded digits long enough
            if len(num_norm) < 4 or not num_norm.isdigit():
                return None

            n1 = num_norm[:2]
            n2 = num_norm[-2:]

            # Safety: require both parts to be digits and length == 2
            if n1.isdigit() and n2.isdigit() and len(n1) == 2 and len(n2) == 2:
                out = f"{prefix_conv} {n1}/{n2}"
                if paren:
                    out = f"{out} ({paren})"
                return out

        # Otherwise, do not attempt reconstruction here — keep strict canonical rules
        return None


def extract_mfg_date(text: str) -> Optional[str]:
    """
    Extract manufacturing date

    Patterns:
    - MFG 22 JAN 23
    - Mfg: 22 Jan 2023
    - 22 JAN 23
    """
    t = normalize_ocr_text(text)

    # Prefer explicit MFG label — look for clear patterns first
    lab = re.search(r'\bMFG\b', t)
    if lab:
        tail = t[lab.end():lab.end()+120]
        # 1) day MONTH YEAR
        m = re.search(r'\b(\d{1,2})\s+([A-Z]{2,4})\s+(\d{2,4})\b', tail)
        if m:
            day, month, year = m.groups()
            return format_date(day, month, year)
        # 2) day only after MFG, then search for month+year after that position
        m = re.search(r'\b(\d{1,2})\b', tail)
        if m:
            day = m.group(1)
            after = tail[m.end():]
            m2 = re.search(r'\b([A-Z]{2,4})\s+(\d{2,4})\b', after)
            if m2:
                month, year = m2.groups()
                return format_date(day, month, year)
            m3 = re.search(r'\b([A-Z]{2,4})\b', after)
            if m3:
                month = m3.group(1)
                return format_date(day, month, '00')
        # 3) month+year after MFG
        m = re.search(r'\b([A-Z]{2,4})\s+(\d{2,4})\b', tail)
        if m:
            month, year = m.groups()
            return format_date('01', month, year)


    # Fallback: first date-like token across text (day month year)
    matches = re.findall(r'\b(\d{1,2})\s+([A-Z]{2,4})\s+(\d{2,4})\b', t)
    if matches:
        day, month, year = matches[0]
        return format_date(day, month, year)

    # Try looser match: month+year only
    matches = re.findall(r'\b([A-Z]{2,4})\s+(\d{2,4})\b', t)
    if matches:
        month, year = matches[0]
        return format_date('01', month, year)

    return None


def extract_exp_date(text: str) -> Optional[str]:
    """
    Extract expiration date
    
    Patterns:
    - EXP 11 JUN 24
    - Exp: 11 Jun 2024
    - Expiration: 11 JUN 24
    """
    t = normalize_ocr_text(text)

    # Prefer explicit EXP label — look for clear patterns first
    lab_e = re.search(r'\bEXP\b', t)
    if lab_e:
        tail = t[lab_e.end():lab_e.end()+120]
        m = re.search(r'\b(\d{1,2})\s+([A-Z]{2,4})\s+(\d{2,4})\b', tail)
        if m:
            day, month, year = m.groups()
            return format_date(day, month, year)
        # month+year after EXP
        matches = re.findall(r'\b([A-Z]{2,4})\s+(\d{2,4})\b', tail)
        if matches:
            month, year = matches[-1]
            return format_date('01', month, year)

    # Fallback: second date-like token in whole text
    matches = re.findall(r'\b(\d{1,2})\s+([A-Z]{2,4})\s+([0-9]{2,4})\b', t)
    if len(matches) >= 2:
        day, month, year = matches[1]
        return format_date(day, month, year)

    # Looser fallback: last month+year pair
    matches = re.findall(r'\b([A-Z]{2,4})\s+([0-9]{2,4})\b', t)
    if matches:
        month, year = matches[-1]
        return format_date('01', month, year)

    return None


def format_date(day: str, month: str, year: str) -> str:
    """
    Format date to standard format: DD MMM YYYY
    
    Examples:
    - 22 JAN 23 → 22 Jan 2023
    - 11 JUN 24 → 11 Jun 2024
    """
    # Normalize month token aggressively (remove punctuation, take letters)
    if not month:
        month = ''
    m_raw = re.sub(r'[^A-Z]', '', month.upper())
    # Common OCR misreads map
    month_map = {
        'JAN': 'Jan', 'FEB': 'Feb', 'MAR': 'Mar', 'APR': 'Apr', 'MAY': 'May',
        'JUN': 'Jun', 'JUL': 'Jul', 'AUG': 'Aug', 'SEP': 'Sep', 'OCT': 'Oct',
        'NOV': 'Nov', 'DEC': 'Dec'
    }

    # map likely misreads to canonical 3-letter keys
    fixes = {
        'JN': 'JAN', 'JA': 'JAN', 'JAIN': 'JAN',
        'JV': 'JUN', 'JU': 'JUN', 'JUIV': 'JUN',
        'OOT': 'OCT', '0OT': 'OCT', '0CT': 'OCT', 'O0T': 'OCT', 'OCTT': 'OCT', 'OC': 'OCT',
        'OEC': 'DEC',
        'APRIL': 'APR', 'AP R': 'APR', 'AO': 'APR', 'A0': 'APR',
        'RAY': 'MAY',
    }

    # If month token is known noise, return it as-is (do not convert)
    noise_months = {'WS', 'CO'}
    if m_raw in noise_months:
        month_name = m_raw.capitalize()
    else:
        key = fixes.get(m_raw, m_raw[:3])
        key = key[:3]
        month_name = month_map.get(key, key.capitalize())
    
    # Convert to proper case
    months = {
        'JAN': 'Jan', 'FEB': 'Feb', 'MAR': 'Mar', 'APR': 'Apr',
        'MAY': 'May', 'JUN': 'Jun', 'JUL': 'Jul', 'AUG': 'Aug',
        'SEP': 'Sep', 'OCT': 'Oct', 'NOV': 'Nov', 'DEC': 'Dec'
    }
    
    # month_name is already proper-cased candidate; fall back to mapping table if needed
    month_name = months.get(month_name.upper()[:3], month_name)
    
    # Fix year (2-digit → 4-digit)
    if len(year) == 2:
        year_int = int(year)
        if year_int >= 20 and year_int <= 30:
            year = f'20{year}'
        else:
            year = f'20{year}'
    
    # Pad day
    day = day.zfill(2)
    
    return f'{day} {month_name} {year}'


def parse_standard_date(date_str: str):
    """Parse a date in the standard output format 'DD Mon YYYY' to datetime.

    Returns datetime.date or None on failure.
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%d %b %Y').date()
    except Exception:
        return None


def extract_serial_number(text: str) -> Optional[str]:
    """
    Extract serial number from right region
    Patterns:
    - SER 643797
    - SERIAL 643797
    - Standalone 4-12 alnum token
    """
    t = normalize_ocr_text(text)

    # Strict pattern: 5-6 digits followed by a letter (required by domain rules)
    strict = re.search(r'\b(\d{5,6}[A-Z])\b', t)
    if strict:
        raw = strict.group(1)
        return normalize_serial(raw)

    # Pattern 1: With "SER" or "SERIAL"
    match = re.search(r'(?:SER|SERIAL)\s*[:\-\s]?\s*([A-Z0-9]{4,12})', t)
    if match:
        raw = match.group(1)
        return normalize_serial(raw)

    # Pattern 2: Standalone 4-12 alnum token
    match = re.search(r'\b([A-Z0-9]{4,12})\b', t)
    if match:
        raw = match.group(1)
        return normalize_serial(raw)

    return None


def extract_vaccine_data(left_text: str, right_text: str) -> Dict[str, Optional[str]]:
    """
    🎯 MAIN FUNCTION: Extract all vaccine data
    
    Args:
        left_text: OCR text from left region
        right_text: OCR text from right region
    
    Returns:
        {
            'vaccine_name': 'Rabies Vaccine',
            'product_name': 'DEFENSOR 3',
            'manufacturer': 'Zoetis Inc.',
            'registration_number': '1F 2/56 (B)',
            'serial_number': '643797',
            'mfg_date': '22 Jan 2023',
            'exp_date': '11 Jun 2024',
        }
    """
    print('\nExtracting vaccine data...')
    
    data = {
        'vaccine_name': extract_vaccine_name(left_text),
        'product_name': extract_product_name(left_text),
        'manufacturer': extract_manufacturer(left_text),
        'registration_number': extract_registration_number(left_text),
        'serial_number': None,
        'mfg_date': extract_mfg_date(right_text),
        'exp_date': extract_exp_date(right_text),
    }

    # Serial extraction: prefer strict domain rule (5-6 digits + trailing letter).
    # Check right side first, then left side. If none match strict rule, fall back to
    # looser extraction on right then left.
    serial_right = extract_serial_number(right_text)
    serial_left = extract_serial_number(left_text)

    def is_strict_serial(s: Optional[str]) -> bool:
        if not s:
            return False
        return bool(re.fullmatch(r"\d{5,6}[A-Z]", s.upper()))

    if is_strict_serial(serial_right):
        data['serial_number'] = serial_right
    elif is_strict_serial(serial_left):
        data['serial_number'] = serial_left
    else:
        # fallback: prefer right extraction if present, else left
        data['serial_number'] = serial_right or serial_left

    # Post-process dates: ensure expiration date is after manufacturing date.
    # If exp == mfg or exp is missing/earlier, try to find an alternate exp
    # candidate in the right_text (then left_text) that is strictly later than mfg.
    mfg = data.get('mfg_date')
    exp = data.get('exp_date')

    mfg_dt = parse_standard_date(mfg) if mfg else None
    exp_dt = parse_standard_date(exp) if exp else None

    def find_later_date_candidates(text: str):
        # find all day MONTH YEAR tokens. Normalize by uppercasing and
        # replacing punctuation with spaces so patterns like 'SEP.23' or 'SEP23'
        # become 'SEP 23' and can be matched.
        t_search = re.sub(r'[^A-Z0-9\s]', ' ', (text or '').upper())
        t_search = re.sub(r'\s+', ' ', t_search).strip()
        matches = re.findall(r'\b(\d{1,2})\s+([A-Z]{2,4})\s+(\d{2,4})\b', t_search)
        candidates = []
        for d, m, y in matches:
            fmt = format_date(d, m, y)
            dt = parse_standard_date(fmt)
            if dt:
                candidates.append((dt, fmt))
        return candidates

    if mfg_dt:
        need_fix = False
        if exp_dt is None:
            need_fix = True
        elif exp_dt <= mfg_dt:
            need_fix = True

        if need_fix:
            # search right then left for candidate dates later than mfg
            candidates = find_later_date_candidates(right_text)
            if not candidates:
                candidates = find_later_date_candidates(left_text)

            # pick the earliest candidate that is strictly after mfg
            pick = None
            for dt, fmt in sorted(candidates, key=lambda x: x[0]):
                if dt > mfg_dt:
                    pick = fmt
                    break

            if pick:
                data['exp_date'] = pick

    # Infer product_name from vaccine_name or left_text when missing
    if not data.get('product_name'):
        vn = (data.get('vaccine_name') or '').upper()
        left_up = (left_text or '').upper()
        if 'FELINE' in vn or 'FELOCELL' in left_up or 'FELOCELL' in vn or 'FEUOCELL' in left_up:
            data['product_name'] = 'FELOCELL'
        elif 'RABIES' in vn or 'RABIES VACCINE' in vn or 'DEFENSOR' in left_up or 'DEFERUSOR' in left_up:
            data['product_name'] = 'DEFENSOR'

    # If registration number looks suspicious (too short or purely numeric), try right_text as fallback
    reg = data.get('registration_number')
    if not reg or len(reg) < 4 or re.fullmatch(r'\d{1,6}', (reg or '').replace(' ', '')):
        reg_right = extract_registration_number(right_text)
        if reg_right:
            data['registration_number'] = reg_right
    
    # Log results
    for key, value in data.items():
        status = '[OK]' if value else '[MISSING]'
        print(f'   {status} {key}: {value or "ไม่พบ"}')
    
    return data


def validate_vaccine_data(data: Dict[str, Optional[str]]) -> Dict[str, bool]:
    """
    Validate extracted data
    
    Returns:
        {
            'has_vaccine_name': True/False,
            'has_serial': True/False,
            'has_dates': True/False,
            'is_complete': True/False,
        }
    """
    validation = {
        'has_vaccine_name': bool(data.get('vaccine_name') or data.get('product_name')),
        'has_serial': bool(data.get('serial_number')),
        'has_dates': bool(data.get('mfg_date') and data.get('exp_date')),
        'has_manufacturer': bool(data.get('manufacturer')),
    }
    
    validation['is_complete'] = all([
        validation['has_vaccine_name'],
        validation['has_serial'],
        validation['has_dates'],
    ])
    
    return validation


# Thai field mappings
THAI_FIELDS = {
    'vaccine_name': 'ชื่อวัคซีน',
    'product_name': 'ชื่อการค้า',
    'manufacturer': 'ผู้ผลิต',
    'registration_number': 'เลขทะเบียน',
    'serial_number': 'Serial Number',
    'mfg_date': 'วันผลิต',
    'exp_date': 'วันหมดอายุ',
}


def format_output_thai(data: Dict[str, Optional[str]]) -> str:
    """Format data for Thai display"""
    lines = []
    for key, thai_name in THAI_FIELDS.items():
        value = data.get(key, 'ไม่พบ') or 'ไม่พบ'
        lines.append(f'{thai_name}: {value}')
    return '\n'.join(lines)