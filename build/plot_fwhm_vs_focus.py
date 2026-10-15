#!/usr/bin/env python3
"""
Построение графиков контраста Михельсона и FWHM от ГЛУБИНЫ ФОКУСА
(для развёртки focus_XXXXum в results/).

Читает:
    results/focus_0000um/michelson_results.txt
    results/focus_0000um/fwhm_results.txt
    ...

Строит:
    contrast_fwhm_vs_focus.png
"""

import os
import re
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(SCRIPT_DIR, 'results')
OUTPUT_PNG = os.path.join(SCRIPT_DIR, 'contrast_fwhm_vs_focus.png')


def parse_kv(path):
    d = {}
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                d[parts[0]] = float(parts[1])
            except ValueError:
                continue
    return d


def depth_from_dirname(name):
    """'focus_0600um' -> 600.0"""
    m = re.match(r'^focus_(\d+)um$', name)
    return float(m.group(1)) if m else None


def collect_records(results_dir):
    if not os.path.isdir(results_dir):
        print(f'ERROR: папка {results_dir} не найдена')
        return []

    records = []
    for entry in sorted(os.listdir(results_dir)):
        full = os.path.join(results_dir, entry)
        if not os.path.isdir(full):
            continue

        depth = depth_from_dirname(entry)
        if depth is None:
            continue

        m_path = os.path.join(full, 'michelson_results.txt')
        f_path = os.path.join(full, 'fwhm_results.txt')
        if not (os.path.isfile(m_path) and os.path.isfile(f_path)):
            print(f'  Пропускаю {entry}: нет результатов')
            continue

        md = parse_kv(m_path)
        fd = parse_kv(f_path)

        rec = {
            'dir': entry,
            'depth': depth,
            'contrast': md.get('overall_mean'),
            'contrast_x': md.get('direction_X_mean'),
            'contrast_x_std': md.get('direction_X_std'),
            'contrast_y': md.get('direction_Y_mean'),
            'contrast_y_std': md.get('direction_Y_std'),
            'fwhm': fd.get('overall_mean_um'),
            'fwhm_x': fd.get('direction_X_mean_um'),
            'fwhm_x_std': fd.get('direction_X_std_um'),
            'fwhm_y': fd.get('direction_Y_mean_um'),
            'fwhm_y_std': fd.get('direction_Y_std_um'),
        }
        stds = [v for v in (rec['contrast_x_std'], rec['contrast_y_std']) if v is not None]
        rec['contrast_std'] = float(np.mean(stds)) if stds else 0.0
        stds = [v for v in (rec['fwhm_x_std'], rec['fwhm_y_std']) if v is not None]
        rec['fwhm_std'] = float(np.mean(stds)) if stds else 0.0
        records.append(rec)

    records.sort(key=lambda r: r['depth'])
    return records


def main():
    print(f'Читаю данные из: {RESULTS_DIR}')
    records = collect_records(RESULTS_DIR)

    if not records:
        print('ERROR: не найдено ни одной папки focus_*um с результатами.')
        sys.exit(1)

    depth = np.array([r['depth'] for r in records])
    contrast = np.array([r['contrast'] if r['contrast'] is not None else np.nan for r in records])
    contrast_std = np.array([r['contrast_std'] for r in records])
    fwhm = np.array([r['fwhm'] if r['fwhm'] is not None else np.nan for r in records])
    fwhm_std = np.array([r['fwhm_std'] for r in records])

    print('\nНайдено глубин:')
    for r in records:
        c_str = f"{r['contrast']:.4f}" if r['contrast'] is not None else '  —   '
        f_str = f"{r['fwhm']:.2f}"   if r['fwhm'] is not None else '  —  '
        print(f"  {r['dir']:>16s}  (depth = {r['depth']:6.1f} мкм)  "
              f"C = {c_str}   FWHM = {f_str} мкм")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    ax = axes[0]
    ax.errorbar(depth, contrast, yerr=contrast_std,
                fmt='o-', color='C0', ecolor='C0',
                elinewidth=1, capsize=4, markersize=7, linewidth=1.5,
                label='Контраст Михельсона')
    ax.set_xlabel('Глубина фокуса от задней поверхности, мкм')
    ax.set_ylabel('Контраст Михельсона C')
    ax.set_title('Контраст Михельсона vs глубина фокуса')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')

    ax = axes[1]
    ax.errorbar(depth, fwhm, yerr=fwhm_std,
                fmt='s-', color='C3', ecolor='C3',
                elinewidth=1, capsize=4, markersize=7, linewidth=1.5,
                label='FWHM')
    ax.set_xlabel('Глубина фокуса от задней поверхности, мкм')
    ax.set_ylabel('FWHM, мкм')
    ax.set_title('FWHM vs глубина фокуса')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')

    plt.tight_layout()
    plt.savefig(OUTPUT_PNG, dpi=150)
    plt.close()
    print(f'\nГрафик сохранён: {OUTPUT_PNG}')


if __name__ == '__main__':
    main()