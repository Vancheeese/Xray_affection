#!/usr/bin/env python3
"""
Чтение параметров геометрии из src/global_parameters.cc.

Разбирает определения вида:
    G4double pixelSize = 3.5 * um;
    G4int    gridSize  = 100;
Значения с единицами длины GEANT4 (nm, um, mm, cm, m) переводятся в микрометры.
"""

import os
import re

# Путь к global_parameters.cc относительно этого файла
DEFAULT_PATH = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    os.pardir, 'src', 'global_parameters.cc'
))

# Множители единиц длины GEANT4 в микрометры
_LENGTH_TO_UM = {
    'nm': 1e-3,
    'um': 1.0,
    'mm': 1000.0,
    'cm': 10000.0,
    'm': 1e6,
}

# G4double/G4int name = <число> [* единица];
_PATTERN = re.compile(
    r'G4(?:double|int)\s+(\w+)\s*=\s*([0-9.eE+-]+)\s*(?:\*\s*(\w+))?\s*;'
)


def read_params(path=DEFAULT_PATH):
    """Возвращает dict {имя параметра: значение}.

    Длины приводятся к микрометрам; безразмерные параметры (gridSize и т.п.)
    возвращаются как есть. Параметры с прочими единицами (keV и т.п.) пропускаются.
    """
    params = {}
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    for name, value, unit in _PATTERN.findall(text):
        val = float(value)
        if unit:
            factor = _LENGTH_TO_UM.get(unit)
            if factor is None:
                continue  # не единицы длины — пропускаем
            val *= factor
        params[name] = val
    return params


def get_param(name, default=None, path=DEFAULT_PATH):
    """Возвращает параметр (длины в мкм), либо default, если он не найден."""
    try:
        return read_params(path).get(name, default)
    except OSError:
        return default


if __name__ == '__main__':
    for name, value in sorted(read_params().items()):
        print(f"{name} = {value:g}")
