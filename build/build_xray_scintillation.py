#!/usr/bin/env python3
"""
Построение рентгеновского изображения по оптическим фотонам сцинтилляции.
Рентгеновские фотоны проходят через золотые полоски, поглощаются в сцинтилляторе,
генерируют оптические фотоны, которые регистрируются на Si-детекторе.

Запуск из папки build:
    python build_xray_scintillation.py
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
import pandas as pd
import re
import os
import sys

# ==================== Чтение параметров из global_parameters.cc ====================
def read_global_parameters():
    """Читает pixelSize, gridSize, slitWidth из global_parameters.cc"""
    params = {'pixelSize': 10.0, 'gridSize': 100, 'slitWidth': 50.0}
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cc_file = os.path.join(script_dir, '..', 'src', 'global_parameters.cc')
    
    if not os.path.exists(cc_file):
        print(f"⚠ global_parameters.cc не найден: {cc_file}")
        return params
    
    with open(cc_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    match = re.search(r'pixelSize\s*=\s*([\d.]+)', content)
    if match: params['pixelSize'] = float(match.group(1))
    
    match = re.search(r'gridSize\s*=\s*(\d+)', content)
    if match: params['gridSize'] = int(match.group(1))
    
    match = re.search(r'slitWidth\s*=\s*([\d.]+)', content)
    if match: params['slitWidth'] = float(match.group(1))
    
    return params


# ==================== Чтение данных ====================
def read_hits_data(filename='hits_data.csv', E_MIN=1.5, E_MAX=3.5):
    """Читает hits_data.csv, возвращает DataFrame с оптическими фотонами.
    Обрабатывает файл по частям (chunked), чтобы не забивать память."""
    required_cols = ['Energy_eV', 'PosX_um', 'PosY_um']
    chunks = []
    
    for encoding in ['utf-8', 'utf-8-sig', 'latin1', 'cp1251']:
        try:
            print(f"  Пробуем кодировку: {encoding}...")
            total_rows = 0
            loaded_rows = 0
            for chunk in pd.read_csv(filename, sep='	', comment='#', encoding=encoding, 
                                     usecols=required_cols, chunksize=500000, low_memory=False):
                total_rows += len(chunk)
                chunk['Energy_eV'] = pd.to_numeric(chunk['Energy_eV'], errors='coerce')
                chunk['PosX_um'] = pd.to_numeric(chunk['PosX_um'], errors='coerce')
                chunk['PosY_um'] = pd.to_numeric(chunk['PosY_um'], errors='coerce')
                chunk.dropna(subset=required_cols, inplace=True)
                # Фильтруем по энергии оптических фотонов (1.5 - 3.5 эВ)
                mask = (chunk['Energy_eV'] >= E_MIN) & (chunk['Energy_eV'] <= E_MAX)
                filtered = chunk[mask]
                chunks.append(filtered)
                loaded_rows += len(filtered)
                del chunk, filtered, mask
                
            print(f"  ✅ Прочитано {total_rows:,} строк. Отфильтровано {loaded_rows:,} оптических фотонов.")
            break 
        except Exception as e:
            print(f"  Кодировка {encoding}: {e}")
            continue
            
    if not chunks:
        print("  ❌ Не удалось прочитать данные!")
        return pd.DataFrame()
        
    df = pd.concat(chunks, ignore_index=True)
    del chunks
    return df


# ==================== Построение геометрии ====================
def build_geometry_mask(params, grid_size, x_edges, y_edges):
    """Создаёт бинарную маску золотых полосок.
    
    Полоски в C++ идут ВДОЛЬ оси Y (длина по Y = leadSize, ширина по X = slitWidth).
    counts[i, j] соответствует y_edges[i] и x_edges[j].
    geometry[i, j] = 1.0 если пиксель попадает под полоску.
    """
    pixel_size = params['pixelSize']
    slit_width = params['slitWidth']
    lead_size = pixel_size * grid_size
    slit_period = slit_width * 2  # ширина + зазор (равные)
    num_slits = int(lead_size / slit_period)
    total_width = num_slits * slit_period
    start_x = -total_width / 2.0 + slit_width / 2.0
    
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2.0
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2.0
    
    geometry = np.zeros((grid_size, grid_size), dtype=float)
    
    # Полоски идут ВДОЛЬ Y, поэтому проверяем только X
    for i in range(num_slits):
        strip_center = start_x + i * slit_period
        x_min = strip_center - slit_width / 2.0
        x_max = strip_center + slit_width / 2.0
        is_in_strip = (x_centers >= x_min) & (x_centers < x_max)
        
        # Помечаем строку (все Y) для этого X (полоски вдоль Y)
        for j, in_strip in enumerate(is_in_strip):
            if in_strip:
                geometry[j, :] = 1.0  # золото
    
    return geometry, num_slits, slit_width, slit_period, start_x


# ==================== Построение изображений ====================
def build_images(df, params):
    """Строит все изображения и сохраняет"""
    
    pixel_size = params['pixelSize']
    grid_size = params['gridSize']
    lead_size = pixel_size * grid_size
    
    # --- Фильтрация оптических фотонов (2-3 эВ) ---
    E_OPTICAL_MIN = 1.5  # эВ
    E_OPTICAL_MAX = 3.5  # эВ
    
    mask_optical = (df['Energy_eV'] >= E_OPTICAL_MIN) & (df['Energy_eV'] <= E_OPTICAL_MAX)
    df_optical = df[mask_optical].copy()
    
    print(f"\nВсего частиц: {len(df):,}")
    print(f"Оптических фотонов (E={E_OPTICAL_MIN}-{E_OPTICAL_MAX} эВ): {len(df_optical):,}")
    
    if len(df_optical) == 0:
        print("❌ Нет оптических фотонов в диапазоне!")
        print(f"   Диапазон: {E_OPTICAL_MIN}-{E_OPTICAL_MAX} эВ")
        print(f"   Доступный диапазон энергий: {df['Energy_eV'].min():.2f}-{df['Energy_eV'].max():.2f} эВ")
        return
    
    # --- Диапазон координат ---
    x_range = (-lead_size / 2, lead_size / 2)
    y_range = (-lead_size / 2, lead_size / 2)
    
    # --- 2D гистограмма (количество) ---
    print("\nБинирование...")
    counts, x_edges, y_edges = np.histogram2d(
        df_optical['PosX_um'].values,
        df_optical['PosY_um'].values,
        bins=grid_size,
        range=[x_range, y_range]
    )
    
    # counts[i, j] соответствует x_centers[i] и y_centers[j]
    # imshow отображает первую ось по вертикали, вторую по горизонтали
    # Чтобы X был горизонтален, а Y вертикален — транспонируем
    counts_T = counts.T
    
    print(f"  Ненулевых пикселей: {np.sum(counts_T > 0):,} / {grid_size*grid_size:,}")
    print(f"  Максимум фотонов/пиксель: {int(np.max(counts_T))}")
    print(f"  Средняя энергия оптических фотонов: {np.mean(df_optical['Energy_eV']):.2f} эВ")
    
    # --- Маска геометрии ---
    geometry, num_slits, slit_width, slit_period, start_x = build_geometry_mask(
        params, grid_size, x_edges, y_edges
    )
    geometry_T = geometry.T
    
    # --- Вычисление ослабления ---
    # Находим фоновые пиксели (без золота) для референса
    bg_mask = geometry_T == 0
    if np.sum(bg_mask) > 0:
        mean_bg_counts = np.mean(counts_T[bg_mask])
    else:
        mean_bg_counts = np.max(counts_T)
    
    # Аттенюация: I/I0 = counts / mean_bg_counts
    # A = -ln(I/I0)
    signal = np.where(counts_T > 0, counts_T / mean_bg_counts, 0)
    attenuation = -np.log(np.clip(signal, 1e-10, None))
    
    # --- Сглаживание ---
    counts_T_smooth = gaussian_filter(counts_T.astype(float), sigma=0.8)
    # Аттенюация не требует сглаживания — она уже показывает чёткие границы золота
    
    # ==================== Визуализация ====================
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2.0
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2.0
    extent = [x_range[0], x_range[1], y_range[0], y_range[1]]
    
    fig, axes = plt.subplots(1, 4, figsize=(24, 6))
    
    # 1) Карта количества оптических фотонов
    im1 = axes[0].imshow(
        counts_T_smooth, origin='lower', extent=extent,
        cmap='hot', interpolation='bilinear'
    )
    axes[0].set_xlabel('X, мкм', fontsize=12)
    axes[0].set_ylabel('Y, мкм', fontsize=12)
    axes[0].set_title('Карта количества оптических фотонов', fontsize=13)
    plt.colorbar(im1, ax=axes[0], label='Фотонов/пиксель')
    
    # 2) Аттенюация (рентгеновское изображение)
    att_finite = attenuation[~np.isinf(attenuation)]
    if len(att_finite) > 0:
        att_vmin = np.percentile(att_finite, 2)
        att_vmax = np.percentile(att_finite, 98)
    else:
        att_vmin, att_vmax = 0, 1
    
    im2 = axes[1].imshow(
        attenuation, origin='lower', extent=extent,
        cmap='gray_r', interpolation='nearest',
        vmin=att_vmin, vmax=att_vmax
    )
    axes[1].set_xlabel('X, мкм', fontsize=12)
    axes[1].set_ylabel('Y, мкм', fontsize=12)
    axes[1].set_title(f'Рентгеновское изображение (аттенюация)\nσ=0.8, E={E_OPTICAL_MIN}-{E_OPTICAL_MAX} эВ', fontsize=13)
    plt.colorbar(im2, ax=axes[1], label='A = -ln(I/I₀)')
    
    # 3) Отношение сигнал/фон
    ratio = np.where(bg_mask, counts_T_smooth / mean_bg_counts, np.nan)
    im3 = axes[2].imshow(
        ratio, origin='lower', extent=extent,
        cmap='viridis', interpolation='bilinear',
        vmin=0, vmax=1.2
    )
    axes[2].set_xlabel('X, мкм', fontsize=12)
    axes[2].set_ylabel('Y, мкм', fontsize=12)
    axes[2].set_title('Отношение I/I₀\n(золото = тёмное)', fontsize=13)
    plt.colorbar(im3, ax=axes[2], label='I/I₀')
    
    # 4) Геометрия (золотые полоски)
    im4 = axes[3].imshow(
        geometry_T, origin='lower', extent=extent,
        cmap='Greys', interpolation='nearest',
        vmin=0, vmax=1
    )
    axes[3].set_xlabel('X, мкм', fontsize=12)
    axes[3].set_ylabel('Y, мкм', fontsize=12)
    axes[3].set_title(f'Геометрия: {num_slits} золотых полосок\nширина={slit_width} мкм, шаг={slit_period} мкм', fontsize=13)
    plt.colorbar(im4, ax=axes[3], label='Золото / Пустота')
    
    plt.tight_layout()
    plt.savefig('xray_scint_full.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("\n✅ Сохранено: xray_scint_full.png")
    
    # ==================== Отдельные крупные изображения ====================
    
    # Аттенюация (крупно)
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    im = ax.imshow(
        attenuation, origin='lower', extent=extent,
        cmap='gray_r', interpolation='nearest',
        vmin=att_vmin, vmax=att_vmax
    )
    ax.set_xlabel('X, мкм', fontsize=14)
    ax.set_ylabel('Y, мкм', fontsize=14)
    ax.set_title(f'Рентгеновское изображение (сцинтилляция)\nE={E_OPTICAL_MIN}-{E_OPTICAL_MAX} эВ', fontsize=16)
    cbar = plt.colorbar(im, ax=ax, label='A = -ln(I/I₀)')
    plt.tight_layout()
    plt.savefig('xray_scint_attenuation.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("✅ Сохранено: xray_scint_attenuation.png")
    
    # Карта количества (крупно)
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    im = ax.imshow(
        counts_T_smooth, origin='lower', extent=extent,
        cmap='hot', interpolation='bilinear'
    )
    ax.set_xlabel('X, мкм', fontsize=14)
    ax.set_ylabel('Y, мкм', fontsize=14)
    ax.set_title(f'Количество оптических фотонов\nE={E_OPTICAL_MIN}-{E_OPTICAL_MAX} эВ, σ=0.8', fontsize=16)
    cbar = plt.colorbar(im, ax=ax, label='Фотонов/пиксель')
    plt.tight_layout()
    plt.savefig('xray_scint_counts.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("✅ Сохранено: xray_scint_counts.png")
    
    # ==================== Геометрия золотых полосок ====================
    fig_geo, ax_geo = plt.subplots(1, 1, figsize=(10, 10))
    
    # Создаём изображение геометрии
    ax_geo.imshow(
        geometry_T, origin='lower', extent=extent,
        cmap='Greys', interpolation='nearest',
        vmin=0, vmax=1
    )
    
    ax_geo.set_xlabel('X, мкм', fontsize=14)
    ax_geo.set_ylabel('Y, мкм', fontsize=14)
    ax_geo.set_title(
        f'Геометрия золотой маски\n'
        f'{num_slits} полосок | ширина={slit_width} мкм | шаг={slit_period} мкм | '
        f'общая ширина={num_slits*slit_period:.0f} мкм',
        fontsize=16
    )
    
    # Легенда вместо цветовой шкалы
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='black', edgecolor='black', label='Золото (1.0)'),
        Patch(facecolor='white', edgecolor='black', label='Пустота (0.0)')
    ]
    ax_geo.legend(handles=legend_elements, loc='best', framealpha=0.9, fontsize=12)
    
    plt.tight_layout()
    plt.savefig('xray_scint_geometry.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("✅ Сохранено: xray_scint_geometry.png")
    
    # ==================== Статистика ====================
    print(f"\n{'='*55}")
    print("СТАТИСТИКА:")
    print(f"  Пикселей: {grid_size}x{grid_size} = {grid_size*grid_size:,}")
    print(f"  Ненулевых: {np.sum(counts_T > 0):,} ({100*np.sum(counts_T>0)/(grid_size*grid_size):.1f}%)")
    print(f"  Всего оптических фотонов: {len(df_optical):,}")
    print(f"  Максимум/пиксель: {int(np.max(counts_T))}")
    print(f"  Среднее/пиксель (ненулевые): {np.mean(counts_T[counts_T>0]):.1f}")
    print(f"  Среднее (фон, без золота): {mean_bg_counts:.1f}")
    print(f"  Аттенюация макс: {np.max(attenuation[~np.isinf(attenuation)]):.3f}")
    
    # Статистика по золоту и фону
    gold_mask = geometry_T == 1
    if np.sum(gold_mask) > 0 and np.sum(bg_mask) > 0:
        mean_gold_counts = np.mean(counts_T[gold_mask])
        mean_bg_counts_val = np.mean(counts_T[bg_mask])
        contrast = 1 - mean_gold_counts / mean_bg_counts_val
        print(f"\n  Среднее (золото): {mean_gold_counts:.1f}")
        print(f"  Среднее (фон): {mean_bg_counts_val:.1f}")
        print(f"  Контраст: {contrast*100:.1f}%")
        print(f"  Отношение I_gold/I_bg: {mean_gold_counts/mean_bg_counts_val:.3f}")
    print(f"{'='*55}")
    
    # ==================== Сохранение данных ====================
    np.savez('xray_scint_data.npz',
             counts=counts_T,
             counts_smooth=counts_T_smooth,
             attenuation=attenuation,
             geometry=geometry_T,
             x_edges=x_edges,
             y_edges=y_edges,
             mean_bg_counts=mean_bg_counts,
             num_slits=num_slits,
             slit_width=slit_width,
             slit_period=slit_period,
             start_x=start_x)
    print("✅ Сохранено: xray_scint_data.npz")


# ==================== Основная функция ====================
def main():
    print("="*55)
    print("РЕНТГЕНОВСКОЕ ИЗОБРАЖЕНИЕ (сцинтилляция)")
    print("="*55)
    
    # Параметры
    print("\nЧтение параметров...")
    params = read_global_parameters()
    print(f"  pixelSize = {params['pixelSize']} мкм")
    print(f"  gridSize  = {params['gridSize']}")
    print(f"  slitWidth = {params['slitWidth']} мкм")
    
    # Данные
    print("\nЧтение hits_data.csv...")
    df = read_hits_data('hits_data.csv')
    print(f"  Загружено записей: {len(df):,}")
    
    if len(df) == 0:
        print("❌ Не удалось прочитать данные!")
        sys.exit(1)
    
    # Построение
    print("\n" + "="*55)
    build_images(df, params)
    print("\n✅ Готово!")


if __name__ == '__main__':
    main()
