import re
from typing import Dict, Optional
from datetime import datetime


def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s/()-]', '', text)
    return text.strip()


def normalize_ocr_text(text: str) -> str:
    if not text:
        return text

    t = text.upper()

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

    t = re.sub(r"[^A-Z0-9\s/():-]", '', t)

    t = re.sub(r'\s+', ' ', t).strip()
    return t


def normalize_serial(raw: str) -> str:
    if not raw:
        return raw
    s = re.sub(r'[^A-Z0-9]', '', raw.upper())
    if not s:
        return raw

    serial_pattern = re.match(r'^(\d{5,7})([A-Z]{0,2})$', s)
    if serial_pattern:

        return s

    digits = sum(c.isdigit() for c in s)
    letters = sum(c.isalpha() for c in s)

    if digits >= letters or (digits > 0 and letters > 0):
        s = s.replace('S', '5').replace('O', '0').replace('I', '1').replace('L', '1')
    else:
        s = s.replace('0', 'O')

    return s


def extract_vaccine_name(text: str) -> Optional[str]:
    t = text.upper()

    components = []
    if 'RABIES VACCINE' in t or 'RABIES' in t:
        components.append('Rabies Vaccine')
    if 'FELINE' in t and ('RHINOTRACH' in t or 'RHINOTRACHC' in t):
        components.append('Feline Rhinotracheitis')
    elif 'RHINOTRACHEITIS' in t or 'RHINOTRACH' in t or 'RHINOTRACHC' in t:
        components.append('Feline Rhinotracheitis')
    if 'CALICI' in t or 'PANLEUKOPENIA' in t or 'PANLCUKOPENIA' in t or 'PANLEUCOPENIA' in t:
        components.append('Calici-Panleukopenia')
    if 'CHLAMYDIA' in t or 'PSITTACI' in t or 'PSITTACH' in t or 'SHTCINDIS' in t:
        components.append('Chlamydia psittaci')

    if components:
        return '; '.join(components)

    match = re.search(r'(NOBIVAC|DEFENSOR|FELOCELL|FEUOCELL|FEUOKCELL|CEFENSOR)\s*\d*', t)
    if match:
        prod = match.group(0).strip()
        prod = prod.replace('FEUOCELL', 'FELOCELL').replace('FEUOKCELL', 'FELOCELL').replace('CEFENSOR', 'DEFENSOR')
        return prod

    return None


def extract_product_name(text: str) -> Optional[str]:
    t = text.upper()

    match = re.search(r'(DEFENSOR|DEFERUSOR|DEFERUSO|CEFENSOR|NOBIVAC|FELOCELL|FEUOCELL|FEUOKCELL|FEU?\s*O\s*K\s*C?\s*CELL|FE\s*O\s*K\s*C?\s*CELL|FE\s*OKC\s*ELL|ELOKCELL|ELCELL|RABISIN)\s*[TM]*\s*\d*', t)
    if match:
        prod = match.group(0).strip()
        prod = prod.replace('DEFERUSOR', 'DEFENSOR').replace('DEFERUSO', 'DEFENSOR').replace('CEFENSOR', 'DEFENSOR')
        prod = prod.replace('FEUOCELL', 'FELOCELL').replace('FEUOKCELL', 'FELOCELL')
        prod = re.sub(r'FEU?\s*O\s*K\s*C?\s*CELL', 'FELOCELL', prod)
        prod = re.sub(r'FE\s*O\s*K\s*C?\s*CELL', 'FELOCELL', prod)
        prod = re.sub(r'FE\s*OKC\s*ELL', 'FELOCELL', prod)
        prod = prod.replace('ELOKCELL', 'FELOCELL').replace('ELCELL', 'FELOCELL')
        return prod

    return None


def extract_manufacturer(text: str) -> Optional[str]:
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
    
    match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Inc\.?', text)
    if match:
        return match.group(0)
    
    return None


def extract_registration_number(text: str) -> Optional[str]:
    t = text.upper()
    t = t.replace('RSG', 'REG').replace('RGS', 'REG').replace('R S G', 'REG')
    t = t.replace('GEG', 'REG')
    t = t.replace('FEG', 'REG')
    t = t.replace('RO.', 'NO.').replace('R O', 'NO')

    m_frac = re.search(r'([0-9]{1,3}/[0-9]{1,3})', t)

    if not m_frac:
        
        no_slash_match = re.search(r'\bREG\s*(?:NO\.?)?\s*([A-Z0-9]{1,3})\s*([0-9]{4,5})', t)
        if no_slash_match:
            prefix = no_slash_match.group(1)
            number = no_slash_match.group(2)

            after_number = t[no_slash_match.end():no_slash_match.end()+10]
            suffix_match = re.search(r'\s*\(([A-Z0-9\- ]+)\)', after_number)

            val = f"{prefix} {number}"
            if suffix_match:
                val = f"{val} ({suffix_match.group(1).strip()})"

            formatted = format_registration_number(val)
            return formatted

        return None

    frac = m_frac.group(1)

    start_pos = max(0, m_frac.start() - 100)
    before_slash = t[start_pos:m_frac.start()]

    prefix_candidates = []

    reg_patterns = [
        r'\bREG\s+NO\s+([A-Z0-9]{1,3})\s*$',
        r'\bREGNO\s*([A-Z0-9]{1,3})\s*$',     
    ]

    for pattern in reg_patterns:
        reg_match = re.search(pattern, before_slash)
        if reg_match:
            prefix_candidates = [reg_match.group(1)]
            break

    if not prefix_candidates:
        regstuck_match = re.search(r'REGNO([A-Z0-9]{2,10})\s*$', before_slash)
        if regstuck_match:
            stuck_part = regstuck_match.group(1)
            if len(stuck_part) >= 2:
                prefix_candidates = [stuck_part[-2:]]

    if not prefix_candidates:
        prefix_candidates = re.findall(r'([A-Z0-9]{1,3})\s*$', before_slash)

    if not prefix_candidates:
        window = before_slash[-15:] if len(before_slash) > 15 else before_slash
        tokens = re.findall(r'[A-Z0-9]+', window)
        if tokens:
            prefix_raw = tokens[-1]
            if 1 <= len(prefix_raw) <= 3:
                prefix_candidates = [prefix_raw]
            elif len(prefix_raw) >= 2:
                last_2 = prefix_raw[-2:]
                if re.match(r'^[A-Z0-9]{2}$', last_2):
                    prefix_candidates = [last_2]

    if prefix_candidates:
        prefix = prefix_candidates[0]

        if len(prefix) > 3:
            return None

        val = f"{prefix} {frac}"

        after_slash = t[m_frac.end():m_frac.end()+20]
        paren_match = re.search(r'\s*\(([A-Z0-9\- ]+)\)', after_slash)
        if paren_match:
            suffix = paren_match.group(1).strip()
            val = f"{val} ({suffix})"

        formatted = format_registration_number(val)
        return formatted

    return None


def format_registration_number(raw: str) -> Optional[str]:
    if not raw:
        return None
    s = raw.upper().strip()
    s = re.sub(r'[^A-Z0-9/()\s]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()

    paren = None
    m_paren = re.search(r'\(([A-Z0-9\- ]+)\)\s*$', s)
    if m_paren:
        paren = m_paren.group(1).strip()
        paren = paren.replace('0', 'B')
        s = s[:m_paren.start()].strip()

    m_frac = re.search(r'([0-9]{1,3}/[0-9]{1,3})', s)
    if m_frac:
        frac = m_frac.group(1)
        prefix_raw = s[:m_frac.start()].strip()
        prefix = re.sub(r'[^A-Z0-9]', '', prefix_raw)

        if not prefix:
            toks = re.split(r'\s+', prefix_raw)
            prefix = re.sub(r'[^A-Z0-9]', '', toks[-1]) if toks else ''

        if prefix:
            prefix = prefix.replace('IF', '1F').replace('I F', '1F')
            prefix = prefix.replace('ZF', '2F').replace('Z F', '2F')

            if len(prefix) > 3:
                return None
            out = f"{prefix} {frac}"
            if paren:
                out = f"{out} ({paren})"
            return out
        else:
            return None

    m2 = re.search(r'^([A-Z0-9]{1,3})\s*([0-9]{2,6})$', s)
    if m2:
        prefix = m2.group(1)
        number = m2.group(2)

        prefix = prefix.replace('IF', '1F').replace('ZF', '2F')

        if len(prefix) == 2 and len(number) >= 4:
            conv = str.maketrans({'O': '0', 'Q': '0', 'D': '0', 'S': '5', 'Z': '2', 'I': '1', 'L': '1', 'B': '8', 'G': '6'})
            num_norm = number.translate(conv)

            p0 = prefix[0]
            p1 = prefix[1]
            if not p0.isdigit():
                p0_conv_map = {'Z': '2', 'O': '0', 'Q': '0', 'S': '5', 'I': '1', 'L': '1', 'B': '8', 'G': '6'}
                if p0 in p0_conv_map:
                    prefix = p0_conv_map[p0] + p1

            if len(num_norm) < 4 or not num_norm.isdigit():
                return None
            n1 = num_norm[:2]
            n2 = num_norm[-2:]

            if n1.isdigit() and n2.isdigit() and len(n1) == 2 and len(n2) == 2:
                out = f"{prefix} {n1}/{n2}"
                if paren:
                    out = f"{out} ({paren})"
                return out
    return None


def extract_mfg_date(text: str) -> Optional[str]:
    t = normalize_ocr_text(text)

    lab = re.search(r'\bMFG\b', t)
    if lab:
        tail = t[lab.end():lab.end()+120]
        m = re.search(r'\b(\d{1,2})\s+([A-Z]{2,4})\s+(\d{2,4})\b', tail)
        if m:
            day, month, year = m.groups()
            return format_date(day, month, year)
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
        m = re.search(r'\b([A-Z]{2,4})\s+(\d{2,4})\b', tail)
        if m:
            month, year = m.groups()
            return format_date('01', month, year)

    matches = re.findall(r'\b(\d{1,2})\s+([A-Z]{2,4})\s+(\d{2,4})\b', t)
    if matches:
        day, month, year = matches[0]
        return format_date(day, month, year)

    matches = re.findall(r'\b([A-Z]{2,4})\s+(\d{2,4})\b', t)
    if matches:
        month, year = matches[0]
        return format_date('01', month, year)

    return None


def extract_exp_date(text: str) -> Optional[str]:
    t = normalize_ocr_text(text)

    lab_e = re.search(r'\bEXP\b', t)
    if lab_e:
        tail = t[lab_e.end():lab_e.end()+120]
        m = re.search(r'\b(\d{1,2})\s+([A-Z]{2,4})\s+(\d{2,4})\b', tail)
        if m:
            day, month, year = m.groups()
            return format_date(day, month, year)
        matches = re.findall(r'\b([A-Z]{2,4})\s+(\d{2,4})\b', tail)
        if matches:
            month, year = matches[-1]
            return format_date('01', month, year)

    matches = re.findall(r'\b(\d{1,2})\s+([A-Z]{2,4})\s+([0-9]{2,4})\b', t)
    if len(matches) >= 2:
        day, month, year = matches[1]
        return format_date(day, month, year)

    matches = re.findall(r'\b([A-Z]{2,4})\s+([0-9]{2,4})\b', t)
    if matches:
        month, year = matches[-1]
        return format_date('01', month, year)

    return None


def format_date(day: str, month: str, year: str) -> str:
    if not month:
        month = ''
    m_raw = re.sub(r'[^A-Z]', '', month.upper())
    month_map = {
        'JAN': 'Jan', 'FEB': 'Feb', 'MAR': 'Mar', 'APR': 'Apr', 'MAY': 'May',
        'JUN': 'Jun', 'JUL': 'Jul', 'AUG': 'Aug', 'SEP': 'Sep', 'OCT': 'Oct',
        'NOV': 'Nov', 'DEC': 'Dec'
    }

    fixes = {
        'JN': 'JAN', 'JA': 'JAN', 'JAIN': 'JAN',
        'JV': 'JUN', 'JU': 'JUN', 'JUIV': 'JUN',
        'OOT': 'OCT', '0OT': 'OCT', '0CT': 'OCT', 'O0T': 'OCT', 'OCTT': 'OCT', 'OC': 'OCT',
        'OEC': 'DEC',
        'BUC': 'MAY',
        'APRIL': 'APR', 'AP R': 'APR', 'AO': 'APR', 'A0': 'APR',
        'RAY': 'MAY',
    }

    noise_months = {'WS', 'CO'}
    if m_raw in noise_months:
        month_name = m_raw.capitalize()
    else:
        key = fixes.get(m_raw, m_raw[:3])
        key = key[:3]
        month_name = month_map.get(key, key.capitalize())
    
    months = {
        'JAN': 'Jan', 'FEB': 'Feb', 'MAR': 'Mar', 'APR': 'Apr',
        'MAY': 'May', 'JUN': 'Jun', 'JUL': 'Jul', 'AUG': 'Aug',
        'SEP': 'Sep', 'OCT': 'Oct', 'NOV': 'Nov', 'DEC': 'Dec'
    }
    
    month_name = months.get(month_name.upper()[:3], month_name)
    
    if len(year) == 2:
        year_int = int(year)
        if year_int >= 20 and year_int <= 30:
            year = f'20{year}'
        else:
            year = f'20{year}'
    
    day = day.zfill(2)
    
    return f'{day} {month_name} {year}'


def parse_standard_date(date_str: str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%d %b %Y').date()
    except Exception:
        return None


def extract_serial_number(text: str) -> Optional[str]:
    t = normalize_ocr_text(text)

    strict_pattern = r'\b(\d{5,7}[A-Z]{0,2})\b'

    ser_match = re.search(r'(?:SER|SERIAL)\s*[:\-\s]?\s*(?:[A-Z]{1,5}\s+)?(\d{5,7}[A-Z]{0,2})\b', t)
    if ser_match:
        raw = ser_match.group(1)
        if re.fullmatch(r'\d{5,7}[A-Z]{0,2}', raw):
            reg_patterns = re.findall(r'(\d{1,3})/(\d{1,3})', t)

            is_derived_from_reg = False
            if raw.isdigit():
                for n1, n2 in reg_patterns:
                    combined = n1 + n2  # e.g., "18" + "59" = "1859"
                    if raw == combined or (raw.startswith(n1) and raw.endswith(n2)):
                        is_derived_from_reg = True
                        break

            if not is_derived_from_reg:
                return normalize_serial(raw)

    matches = re.findall(strict_pattern, t)

    reg_patterns = re.findall(r'(\d{1,3})/(\d{1,3})', t)

    for match in matches:
        if re.fullmatch(r'\d{5,7}[A-Z]{0,2}', match):
            match_pos = t.find(match)
            if match_pos >= 0:
                context_start = max(0, match_pos - 30)
                context_end = min(len(t), match_pos + len(match) + 30)
                context = t[context_start:context_end]

                if re.search(r'\b(REG|REGNO|FEG|GEG|RSG|RGS)\b', context[:match_pos - context_start + 10]):
                    continue

            is_derived_from_reg = False
            if match.isdigit():
                for n1, n2 in reg_patterns:
                    combined = n1 + n2
                    if match == combined or (match.startswith(n1) and match.endswith(n2)):
                        is_derived_from_reg = True
                        break

            if is_derived_from_reg:
                continue

            if len(match) >= 5 and match.isdigit() and len(match) == 6:
                continue

            return normalize_serial(match)

    return None


def extract_vaccine_data(left_text: str, right_text: str) -> Dict[str, Optional[str]]:
    print('\n กำลังดึงข้อมูลวัคซีน...')
    
    data = {
        'vaccine_name': extract_vaccine_name(left_text),
        'product_name': extract_product_name(left_text),
        'manufacturer': extract_manufacturer(left_text),
        'registration_number': extract_registration_number(left_text),
        'serial_number': None,
        'mfg_date': extract_mfg_date(right_text),
        'exp_date': extract_exp_date(right_text),
    }

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
        data['serial_number'] = serial_right or serial_left

    mfg = data.get('mfg_date')
    exp = data.get('exp_date')

    mfg_dt = parse_standard_date(mfg) if mfg else None
    exp_dt = parse_standard_date(exp) if exp else None

    def find_later_date_candidates(text: str):
        t_search = re.sub(r'[^A-Z0-9\s]', ' ', (text or '').upper())
        t_search = re.sub(r'\s+', ' ', t_search).strip()

        candidates = []

        for mobj in re.finditer(r'\b(\d{1,2})\s+([A-Z]{2,6})\s+([0-9\s]{1,8})\b', t_search):
            d, m, y_raw = mobj.groups()
            digit_runs = re.findall(r'\d{1,4}', y_raw)
            runs_to_process = list(digit_runs)
            for i in range(len(digit_runs)):
                for j in range(i+1, min(i+4, len(digit_runs))):
                    concat = ''.join(digit_runs[i:j+1])
                    if concat and concat not in runs_to_process and len(concat) <= 4:
                        runs_to_process.append(concat)
            for dr in runs_to_process:
                if len(dr) == 4:
                    y_try = dr
                    fmt = format_date(d, m, y_try)
                    dt = parse_standard_date(fmt)
                    if dt:
                        candidates.append((dt, fmt))
                if len(dr) >= 2:
                    subs = set()
                    subs.add(dr[:2])
                    subs.add(dr[-2:])
                    if len(dr) >= 3:
                        subs.add(dr[1:3])

                    sub_map = {'6': '4', '8': '3'}

                    for s in subs:
                        fmt = format_date(d, m, s)
                        dt = parse_standard_date(fmt)
                        if dt:
                            candidates.append((dt, fmt))

                        s_chars = list(s)
                        s_sub = ''.join(sub_map.get(ch, ch) for ch in s_chars)
                        if s_sub != s:
                            fmt2 = format_date(d, m, s_sub)
                            dt2 = parse_standard_date(fmt2)
                            if dt2:
                                candidates.append((dt2, fmt2))

        for d, m, y in re.findall(r'\b(\d{1,2})\s+([A-Z]{2,6})\s+(\d{2,4})\b', t_search):
            fmt = format_date(d, m, y)
            dt = parse_standard_date(fmt)
            if dt:
                candidates.append((dt, fmt))

        seen = set()
        uniq = []
        for dt, fmt in sorted(candidates, key=lambda x: x[0]):
            if dt not in seen:
                uniq.append((dt, fmt))
                seen.add(dt)
        return uniq

    if mfg_dt:
        need_fix = False
        if exp_dt is None:
            need_fix = True
        elif exp_dt <= mfg_dt:
            need_fix = True

        if need_fix:
            candidates = find_later_date_candidates(right_text)
            if not candidates:
                candidates = find_later_date_candidates(left_text)

            pick = None
            for dt, fmt in sorted(candidates, key=lambda x: x[0]):
                if dt > mfg_dt:
                    pick = fmt
                    break

            if pick:
                data['exp_date'] = pick

    if not data.get('product_name'):
        vn = (data.get('vaccine_name') or '').upper()
        left_up = (left_text or '').upper()
        if 'FELINE' in vn or 'FELOCELL' in left_up or 'FELOCELL' in vn or 'FEUOCELL' in left_up:
            data['product_name'] = 'FELOCELL'
        elif 'RABIES' in vn or 'RABIES VACCINE' in vn or 'DEFENSOR' in left_up or 'DEFERUSOR' in left_up:
            data['product_name'] = 'DEFENSOR'

    reg = data.get('registration_number')
    if not reg or len(reg) < 4 or re.fullmatch(r'\d{1,6}', (reg or '').replace(' ', '')):
        reg_right = extract_registration_number(right_text)
        if reg_right:
            data['registration_number'] = reg_right
    
    for key, value in data.items():
        status = '[OK]' if value else '[MISSING]'
        print(f'   {status} {key}: {value or "ไม่พบ"}')
    
    return data


def validate_vaccine_data(data: Dict[str, Optional[str]]) -> Dict[str, bool]:
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
    lines = []
    for key, thai_name in THAI_FIELDS.items():
        value = data.get(key, 'ไม่พบ') or 'ไม่พบ'
        lines.append(f'{thai_name}: {value}')
    return '\n'.join(lines)