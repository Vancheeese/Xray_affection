#!/usr/bin/env python3
"""
Вычисление контраста Михельсона для рентгеновского изображения,
полученного скриптом xray_image.py (файл xray_image.npz).

Методика:
1. Загружается 2D-гистограмма H (фотоны/интенсивность).
2. Выбирается центральная область (ROI), чтобы исключить края.
3. Для каждого профиля вдоль X (или Y) в ROI:
   - профиль сглаживается фильтром Гаусса;
   - находятся локальные максимумы (просветы сетки) и минимумы (проволоки);
   - Imax = среднее значение в максимумах, Imin = среднее в минимумах;
   - C = (Imax - Imin) / (Imax + Imin).
4. Результаты усредняются по всем профилям.
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

def michelson_contrast_1d(profile, smooth_sigma=2.0, min_peaks=2):
    """
    Вычисляет контраст Михельсона для одного 1D-профиля.
    Возвращает (C, Imax, Imin) или (None, None, None), если недостаточно экстремумов.
    """
    # Сглаживание для подавления шума
    prof = gaussian_filter1d(profile.astype(float), sigma=smooth_sigma)
    
    # Поиск максимумов (просветы) и минимумов (проволоки)
    peaks, _ = find_peaks(prof, distance=3, prominence=0.1*np.std(prof))
    valleys, _ = find_peaks(-prof, distance=3, prominence=0.1*np.std(prof))
    
    if len(peaks) < min_peaks or len(valleys) < min_peaks:
        return None, None, None
    
    Imax = np.mean(prof[peaks])
    Imin = np.mean(prof[valleys])
    
    if Imax + Imin == 0:
        return None, None, None
    
    C = (Imax - Imin) / (Imax + Imin)
    return C, Imax, Imin

def main():
    parser = argparse.ArgumentParser(description='Расчёт контраста Михельсона по xray_image.npz')
    parser.add_argument('npz_file', nargs='?', default='xray_image.npz',
                        help='Путь к файлу xray_image.npz (по умолчанию xray_image.npz)')
    parser.add_argument('--roi_frac', type=float, default=0.5,
                        help='Доля центральной области по каждой оси (0..1), по умолчанию 0.5')
    parser.add_argument('--smooth_sigma', type=float, default=2.0,
                        help='Сигма гауссова сглаживания профилей (по умолчанию 2.0)')
    parser.add_argument('--direction', choices=['x', 'y', 'both'], default='both',
                        help='Направление профилей: вдоль X, вдоль Y или оба (по умолчанию both)')
    args = parser.parse_args()
    
    if not os.path.isfile(args.npz_file):
        print(f'ERROR: файл {args.npz_file} не найден')
        sys.exit(1)
    
    # Загрузка данных
    data = np.load(args.npz_file)
    H = data['data']               # shape (nx, ny)
    xedges = data['xedges']
    yedges = data['yedges']
    M = data['M']
    pixel_size = data['pixel_size']
    grid_size = data['grid_size']
    
    nx, ny = H.shape
    print(f'Загружено изображение: {nx} x {ny} пикселей')
    print(f'Увеличение M = {M}')
    print(f'Объектный пиксель = {pixel_size} мкм')
    print(f'Размер бина в плоскости объекта = {pixel_size/M:.3f} мкм')
    
    # Определение ROI (центральная часть)
    roi_frac = args.roi_frac
    if not (0 < roi_frac <= 1):
        print('ERROR: roi_frac должен быть в интервале (0, 1]')
        sys.exit(1)
    
    nx_roi = max(1, int(nx * roi_frac))
    ny_roi = max(1, int(ny * roi_frac))
    x_start = (nx - nx_roi) // 2
    y_start = (ny - ny_roi) // 2
    x_end = x_start + nx_roi
    y_end = y_start + ny_roi
    
    print(f'ROI: X [{x_start}:{x_end}], Y [{y_start}:{y_end}]')
    
    results = {}
    
    # --- Профили вдоль X (для каждого y) ---
    if args.direction in ('x', 'both'):
        contrasts = []
        for j in range(y_start, y_end):
            profile = H[:, j]          # профиль вдоль X
            C, Imax, Imin = michelson_contrast_1d(profile, smooth_sigma=args.smooth_sigma)
            if C is not None:
                contrasts.append(C)
        if contrasts:
            mean_C = np.mean(contrasts)
            std_C = np.std(contrasts)
            results['x'] = (mean_C, std_C, len(contrasts))
            print(f'\nПрофили вдоль X:')
            print(f'  Обработано профилей: {len(contrasts)}')
            print(f'  Средний контраст Михельсона: {mean_C:.4f} ± {std_C:.4f}')
        else:
            print('\nПрофили вдоль X: не удалось найти достаточно экстремумов.')
    
    # --- Профили вдоль Y (для каждого x) ---
    if args.direction in ('y', 'both'):
        contrasts = []
        for i in range(x_start, x_end):
            profile = H[i, :]          # профиль вдоль Y
            C, Imax, Imin = michelson_contrast_1d(profile, smooth_sigma=args.smooth_sigma)
            if C is not None:
                contrasts.append(C)
        if contrasts:
            mean_C = np.mean(contrasts)
            std_C = np.std(contrasts)
            results['y'] = (mean_C, std_C, len(contrasts))
            print(f'\nПрофили вдоль Y:')
            print(f'  Обработано профилей: {len(contrasts)}')
            print(f'  Средний контраст Михельсона: {mean_C:.4f} ± {std_C:.4f}')
        else:
            print('\nПрофили вдоль Y: не удалось найти достаточно экстремумов.')
    
    # --- Итоговая оценка ---
    if results:
        all_means = [v[0] for v in results.values()]
        overall = np.mean(all_means)
        print(f'\n=== ИТОГОВЫЙ КОНТРАСТ МИХЕЛЬСОНА ===')
        print(f'Средний по всем направлениям: {overall:.4f}')
        if 'x' in results and 'y' in results:
            print(f'  (X: {results["x"][0]:.4f}, Y: {results["y"][0]:.4f})')
    else:
        print('\nНе удалось вычислить контраст ни для одного направления.')
        sys.exit(1)

if __name__ == '__main__':
    main()