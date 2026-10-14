#!/usr/bin/env python3
"""
Оценка FWHM (ширины на полувысоте) по рентгеновскому изображению сетки
+ построение профиля интенсивности (аналог рис. 21 в ВКР).

Методика:
1. Из xray_image.npz загружается 2D-изображение H.
2. Для каждого профиля вдоль X (или Y) в центральной ROI:
   - профиль сглаживается;
   - находятся локальные минимумы (проволоки) и максимумы (просветы);
   - для каждого минимума уровень полувысоты I_half = (I_min + I_neighbor_max)/2;
   - измеряется ширина провала на этом уровне (в пикселях);
   - результат переводится в мкм через эффективный пиксель.
3. Значения усредняются по всем профилям и минимумам.
4. Строится график одного репрезентативного профиля с отмеченными
   экстремумами и уровнями полувысоты. По оси X — расстояние в ПИКСЕЛЯХ.

Дополнительно: результаты сохраняются в текстовый файл fwhm_results.txt
рядом с xray_image.npz (в том же формате, что у fwhm.py).
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
import argparse
import os
import sys
from datetime import datetime


def analyze_profile(profile, smooth_sigma=2.0, min_peaks=2):
    """
    Анализ одного профиля:
    - возвращает сглаженный профиль;
    - список индексов максимумов и минимумов;
    - список FWHM (в пикселях) для каждого минимума;
    - список уровней полувысоты для каждого минимума;
    - список кортежей (left_idx, right_idx, valley_idx) — границы FWHM.
    """
    prof = gaussian_filter1d(profile.astype(float), sigma=smooth_sigma)

    valleys, _ = find_peaks(-prof, distance=3, prominence=0.1*np.std(prof))
    peaks, _ = find_peaks(prof, distance=3, prominence=0.1*np.std(prof))

    fwhms = []
    half_levels = []
    fwhm_bounds = []   # список (left_idx, right_idx, valley_idx)

    for v in valleys:
        peaks_left = peaks[peaks < v]
        peaks_right = peaks[peaks > v]
        if len(peaks_left) == 0 or len(peaks_right) == 0:
            continue
        p_left = peaks_left[-1]
        p_right = peaks_right[0]

        I_min = prof[v]
        I_max_neighbor = 0.5 * (prof[p_left] + prof[p_right])
        I_half = 0.5 * (I_min + I_max_neighbor)

        # левая граница FWHM
        left_idx = None
        for i in range(v - 1, p_left - 1, -1):
            if prof[i] >= I_half:
                x1, y1 = i, prof[i]
                x2, y2 = i + 1, prof[i + 1]
                if y2 != y1:
                    left_idx = x1 + (I_half - y1) / (y2 - y1)
                else:
                    left_idx = i
                break

        # правая граница FWHM
        right_idx = None
        for i in range(v + 1, p_right + 1):
            if prof[i] >= I_half:
                x1, y1 = i - 1, prof[i - 1]
                x2, y2 = i, prof[i]
                if y2 != y1:
                    right_idx = x1 + (I_half - y1) / (y2 - y1)
                else:
                    right_idx = i
                break

        if left_idx is not None and right_idx is not None:
            fwhm_pix = right_idx - left_idx
            if fwhm_pix > 0:
                fwhms.append(fwhm_pix)
                half_levels.append(I_half)
                fwhm_bounds.append((left_idx, right_idx, v))

    return prof, peaks, valleys, fwhms, half_levels, fwhm_bounds


def plot_profile(prof, peaks, valleys, fwhms, half_levels, fwhm_bounds,
                 eff_pixel, out_path, title_suffix=''):
    """
    Строит график профиля с отмеченными максимумами, минимумами,
    уровнями полувысоты и границами FWHM.

    По оси X — расстояние в ПИКСЕЛЯХ (как на рис. 21 в ВКР).
    Значения FWHM подписаны в микрометрах.
    """
    n = len(prof)
    x_pix = np.arange(n)

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(x_pix, prof, color='black', linewidth=1.0, label='Профиль интенсивности')

    if len(peaks) > 0:
        ax.plot(x_pix[peaks], prof[peaks], 'o', color='green',
                markersize=6, label='Максимумы (просветы)')
    if len(valleys) > 0:
        ax.plot(x_pix[valleys], prof[valleys], 'o', color='red',
                markersize=6, label='Минимумы (проволоки)')

    for k, (left_idx, right_idx, v) in enumerate(fwhm_bounds):
        level = half_levels[k]
        ax.hlines(level, np.floor(left_idx), np.ceil(right_idx),
                  colors='blue', linestyles='--', linewidth=1.0,
                  label='Уровень полувысоты (I_half)' if k == 0 else None)
        ax.vlines(np.floor(left_idx), prof.min(), prof.max(),
                  colors='gray', linestyles=':', linewidth=0.8)
        ax.vlines(np.ceil(right_idx), prof.min(), prof.max(),
                  colors='gray', linestyles=':', linewidth=0.8)
        fwhm_um = fwhms[k] * eff_pixel
        ax.text(0.5 * (np.floor(left_idx) + np.ceil(right_idx)),
                level + 0.02 * (prof.max() - prof.min()),
                f'{fwhm_um:.2f} мкм',
                ha='center', va='bottom', fontsize=8, color='blue')

    ax.set_xlabel('Расстояние, пиксели')
    ax.set_ylabel('Интенсивность (усл. ед.)')
    title = 'Профиль интенсивности изображения сетки'
    if title_suffix:
        title += f' — {title_suffix}'
    ax.set_title(title + f'\n(1 пиксель = {eff_pixel:.3f} мкм в плоскости объекта)')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=9)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f'  Профиль сохранён: {out_path}')


def write_results_txt(txt_path, npz_path, M, pixel_size, results,
                      script_name='fwhm_profile.py'):
    """
    Сохраняет результаты FWHM в текстовый файл в том же формате,
    что и fwhm.py — чтобы plot_contrast_fwhm_vs_thickness.py
    читал его без изменений.
    """
    eff_pixel = pixel_size / M
    lines = []
    lines.append("# fwhm_results.txt")
    lines.append(f"# Generated by {script_name}")
    lines.append(f"# Input npz: {os.path.abspath(npz_path)}")
    lines.append(f"# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append(f"M {M}")
    lines.append(f"pixel_size_um {pixel_size}")
    lines.append(f"eff_pixel_um {eff_pixel}")
    lines.append("")

    if 'x' in results:
        mean_um, std_um, n = results['x']
        lines.append(f"direction_X_mean_um {mean_um}")
        lines.append(f"direction_X_std_um {std_um}")
        lines.append(f"direction_X_n {n}")
        lines.append("")

    if 'y' in results:
        mean_um, std_um, n = results['y']
        lines.append(f"direction_Y_mean_um {mean_um}")
        lines.append(f"direction_Y_std_um {std_um}")
        lines.append(f"direction_Y_n {n}")
        lines.append("")

    if results:
        overall = float(np.mean([v[0] for v in results.values()]))
        lines.append(f"overall_mean_um {overall}")

    with open(txt_path, 'w') as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description='Оценка FWHM по xray_image.npz (с построением профиля)')
    parser.add_argument('npz_file', nargs='?', default='xray_image.npz',
                        help='Путь к xray_image.npz')
    parser.add_argument('--roi_frac', type=float, default=0.5,
                        help='Доля центральной области (0..1), по умолчанию 0.5')
    parser.add_argument('--smooth_sigma', type=float, default=2.0,
                        help='Сигма гауссова сглаживания (по умолчанию 2.0)')
    parser.add_argument('--direction', choices=['x', 'y', 'both'], default='both',
                        help='Направление профилей (по умолчанию both)')
    parser.add_argument('--profile_index', type=int, default=None,
                        help='Индекс профиля для построения (по умолчанию — середина ROI)')
    parser.add_argument('--no_plot', action='store_true',
                        help='Не строить графики профилей')
    args = parser.parse_args()

    if not os.path.isfile(args.npz_file):
        print(f'ERROR: файл {args.npz_file} не найден')
        sys.exit(1)

    data = np.load(args.npz_file)
    H = data['data']
    M = float(data['M'])
    pixel_size = float(data['pixel_size'])

    eff_pixel = pixel_size / M
    nx, ny = H.shape

    print(f'Изображение: {nx} x {ny} пикселей')
    print(f'Увеличение M = {M}')
    print(f'Эффективный пиксель = {eff_pixel:.3f} мкм')

    roi_frac = args.roi_frac
    nx_roi = max(1, int(nx * roi_frac))
    ny_roi = max(1, int(ny * roi_frac))
    x_start = (nx - nx_roi) // 2
    y_start = (ny - ny_roi) // 2
    x_end = x_start + nx_roi
    y_end = y_start + ny_roi

    print(f'ROI: X [{x_start}:{x_end}], Y [{y_start}:{y_end}]')

    output_dir = os.path.dirname(os.path.abspath(args.npz_file))

    results = {}

    # ============== Профили вдоль X ==============
    if args.direction in ('x', 'both'):
        all_fwhm_pix = []
        for j in range(y_start, y_end):
            profile = H[:, j]
            _, _, _, fwhms, _, _ = analyze_profile(profile, smooth_sigma=args.smooth_sigma)
            all_fwhm_pix.extend(fwhms)

        if all_fwhm_pix:
            arr = np.array(all_fwhm_pix)
            mean_pix = float(arr.mean())
            std_pix = float(arr.std())
            mean_um = mean_pix * eff_pixel
            std_um = std_pix * eff_pixel
            results['x'] = (mean_um, std_um, len(arr))
            print(f'\nПрофили вдоль X:')
            print(f'  Измерено проволок: {len(arr)}')
            print(f'  FWHM = {mean_pix:.2f} ± {std_pix:.2f} пикс')
            print(f'  FWHM = {mean_um:.2f} ± {std_um:.2f} мкм')
        else:
            print('\nПрофили вдоль X: не удалось измерить FWHM.')

        if not args.no_plot:
            if args.profile_index is not None:
                j_plot = args.profile_index
            else:
                j_plot = (y_start + y_end) // 2
            if not (0 <= j_plot < ny):
                print(f'  WARNING: profile_index={j_plot} вне изображения, беру середину ROI')
                j_plot = (y_start + y_end) // 2

            profile = H[:, j_plot]
            prof, peaks, valleys, fwhms, half_levels, fwhm_bounds = analyze_profile(
                profile, smooth_sigma=args.smooth_sigma)

            out_png = os.path.join(output_dir, 'profile_x.png')
            plot_profile(prof, peaks, valleys, fwhms, half_levels, fwhm_bounds,
                         eff_pixel, out_png, title_suffix=f'вдоль X, профиль j={j_plot}')

    # ============== Профили вдоль Y ==============
    if args.direction in ('y', 'both'):
        all_fwhm_pix = []
        for i in range(x_start, x_end):
            profile = H[i, :]
            _, _, _, fwhms, _, _ = analyze_profile(profile, smooth_sigma=args.smooth_sigma)
            all_fwhm_pix.extend(fwhms)

        if all_fwhm_pix:
            arr = np.array(all_fwhm_pix)
            mean_pix = float(arr.mean())
            std_pix = float(arr.std())
            mean_um = mean_pix * eff_pixel
            std_um = std_pix * eff_pixel
            results['y'] = (mean_um, std_um, len(arr))
            print(f'\nПрофили вдоль Y:')
            print(f'  Измерено проволок: {len(arr)}')
            print(f'  FWHM = {mean_pix:.2f} ± {std_pix:.2f} пикс')
            print(f'  FWHM = {mean_um:.2f} ± {std_um:.2f} мкм')
        else:
            print('\nПрофили вдоль Y: не удалось измерить FWHM.')

        if not args.no_plot:
            if args.profile_index is not None:
                i_plot = args.profile_index
            else:
                i_plot = (x_start + x_end) // 2
            if not (0 <= i_plot < nx):
                print(f'  WARNING: profile_index={i_plot} вне изображения, беру середину ROI')
                i_plot = (x_start + x_end) // 2

            profile = H[i_plot, :]
            prof, peaks, valleys, fwhms, half_levels, fwhm_bounds = analyze_profile(
                profile, smooth_sigma=args.smooth_sigma)

            out_png = os.path.join(output_dir, 'profile_y.png')
            plot_profile(prof, peaks, valleys, fwhms, half_levels, fwhm_bounds,
                         eff_pixel, out_png, title_suffix=f'вдоль Y, профиль i={i_plot}')

    # ============== Итог ==============
    if results:
        all_means = [v[0] for v in results.values()]
        overall = float(np.mean(all_means))
        print(f'\n=== ИТОГОВЫЙ FWHM ===')
        print(f'Средний FWHM: {overall:.2f} мкм')
        if 'x' in results and 'y' in results:
            print(f'  (X: {results["x"][0]:.2f} мкм, Y: {results["y"][0]:.2f} мкм)')

        # --- Сохранение в текстовый файл рядом с npz ---
        txt_path = os.path.join(output_dir, 'fwhm_results.txt')
        try:
            write_results_txt(txt_path, args.npz_file, M, pixel_size, results,
                              script_name='fwhm_profile.py')
            print(f'\nРезультаты сохранены: {txt_path}')
        except OSError as e:
            print(f'ERROR: не удалось записать {txt_path}: {e}')
            sys.exit(1)
    else:
        print('\nНе удалось вычислить FWHM.')
        sys.exit(1)


if __name__ == '__main__':
    main()