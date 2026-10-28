#!/usr/bin/env python3
"""
Построение гистограммы z-координат рождения оптических фотонов,
зарегистрированных детектором.

Использование:
    python3 plot_vertex_z.py results/z_test/hits_data.csv
    python3 plot_vertex_z.py results/focus_0600um/hits_data.csv --out z_hist_0600.png
"""

import argparse
import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def load_optical_photon_z(csv_path):
    """Читает CSV, оставляет только opticalphoton, возвращает массив VertexZ_um."""
    z_values = []
    with open(csv_path, 'r') as f:
        # Пропускаем заголовок
        header = f.readline()
        cols = header.strip().split('\t')
        if 'VertexZ_um' not in cols:
            print(f'ERROR: в {csv_path} нет столбца VertexZ_um.')
            print(f'  Найденные столбцы: {cols}')
            print(f'  Пересоберите проект с новой версией PMSensitiveDetector.cc')
            sys.exit(1)
        z_idx = cols.index('VertexZ_um')
        type_idx = cols.index('Type')

        for line in f:
            parts = line.rstrip('\n').split('\t')
            if len(parts) <= z_idx:
                continue
            if parts[type_idx] != 'opticalphoton':
                continue
            try:
                z_values.append(float(parts[z_idx]))
            except ValueError:
                continue
    return np.array(z_values)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_file', help='hits_data.csv с новым столбцом VertexZ_um')
    parser.add_argument('--out', default=None, help='Имя выходного PNG')
    parser.add_argument('--bins', type=int, default=60, help='Число бинов')
    args = parser.parse_args()

    if not os.path.isfile(args.csv_file):
        print(f'ERROR: файл {args.csv_file} не найден')
        sys.exit(1)

    print(f'Читаю: {args.csv_file}')
    z = load_optical_photon_z(args.csv_file)

    if len(z) == 0:
        print('ERROR: не найдено ни одного оптического фотона.')
        sys.exit(1)

    print(f'Оптических фотонов: {len(z)}')
    print(f'Диапазон z: [{z.min():.1f}, {z.max():.1f}] мкм')
    print(f'Средний z:  {z.mean():.1f} мкм')
    print(f'Медиана z:  {np.median(z):.1f} мкм')

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(z, bins=args.bins, color='C0', edgecolor='black', alpha=0.8)
    ax.axvline(z.mean(),   color='red',   linestyle='--', label=f'среднее = {z.mean():.1f} мкм')
    ax.axvline(np.median(z), color='green', linestyle='--', label=f'медиана = {np.median(z):.1f} мкм')
    ax.set_xlabel('z-координата рождения фотона, мкм')
    ax.set_ylabel('Число фотонов в бине')
    ax.set_title(f'Распределение фотонов по глубине сцинтиллятора\n'
                 f'({os.path.basename(os.path.dirname(args.csv_file))})')
    ax.grid(True, alpha=0.3)
    ax.legend()

    plt.tight_layout()
    out_png = args.out or os.path.join(
        os.path.dirname(args.csv_file), 'vertex_z_hist.png')
    plt.savefig(out_png, dpi=150)
    plt.close()
    print(f'Гистограмма сохранена: {out_png}')


if __name__ == '__main__':
    main()