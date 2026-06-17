from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_FLOAT_RE = re.compile(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?')


def _extract_floats(text: str) -> List[float]:
    values: List[float] = []
    for match in _FLOAT_RE.findall(text):
        try:
            values.append(float(match))
        except ValueError:
            continue
    return values


def parse_frequency_response(line: Optional[str]) -> float:
    if not line:
        return 0.0
    values = _extract_floats(line.strip())
    return float(values[0]) if values else 0.0


def parse_measure_response(line: Optional[str]) -> Dict[str, Any]:
    if not line:
        return {}

    text = line.strip()
    values = _extract_floats(text)
    firstvalue = 0.0
    secondvalue = 0.0
    if len(values) >= 2:
        firstvalue, secondvalue = values[-2], values[-1]
    elif len(values) == 1:
        firstvalue = values[0]

    imparam = ''
    secparam = ''
    for token in re.split(r'[,;\s]+', text):
        cleaned = token.strip()
        if not cleaned or _FLOAT_RE.fullmatch(cleaned):
            continue
        if not imparam:
            imparam = cleaned
        elif not secparam:
            secparam = cleaned

    return {
        'ImParam': imparam,
        'SecParam': secparam,
        'FirstValue': firstvalue,
        'SecondValue': secondvalue,
        'Frequency': 0.0,
    }
