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
def read_hits_data(filename='hits_data.csv'):
    """Читает hits_data.csv, возвращает DataFrame"""
    for encoding in ['utf-8', 'utf-8-sig', 'latin1', 'cp1251']:
        try:
            df = pd.read_csv(filename, sep='\t', comment='#', encoding=encoding, low_memory=False)
            required_cols = ['Energy_eV', 'PosX_um', 'PosY_um']
            if all(col in df.columns for col in required_cols):
                df['Energy_eV'] = pd.to_numeric(df['Energy_eV'], errors='coerce')
                df['PosX_um'] = pd.to_numeric(df['PosX_um'], errors='coerce')
                df['PosY_um'] = pd.to_numeric(df['PosY_um'], errors='coerce')
                df.dropna(subset=required_cols, inplace=True)
                return df[required_cols]
        except Exception as e:
            print(f"  Кодировка {encoding}: {e}")
            continue
    
    return pd.DataFrame()


# ==================== Построение геометрии ====================
def build_geometry_mask(params, grid_size, x_edges, y_edges):
    """Создаёт бинарную маску золотых полосок"""
    pixel_size = params['pixelSize']
    slit_width = params['slitWidth']
    lead_size = pixel_size * grid_size
    slit_period = slit_width * 2  # ширина + зазор (равные)
    num_slits = int(lead_size / slit_period)
    total_width = num_slits * slit_period
    start_x = -total_width / 2.0 + slit_width / 2.0
    
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2.0
    
    geometry = np.zeros((grid_size, grid_size), dtype=float)
    is_strip = ((x_centers - start_x) % slit_period) < slit_width
    
    for j in range(grid_size):
        for i in range(grid_size):
            if is_strip[i]:
                geometry[j, i] = 1.0  # золото
    
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
    
    print(f"  Ненулевых пикселей: {np.sum(counts > 0):,} / {grid_size*grid_size:,}")
    print(f"  Максимум фотонов/пиксель: {int(np.max(counts))}")
    print(f"  Средняя энергия оптических фотонов: {np.mean(df_optical['Energy_eV']):.2f} эВ")
    
    # --- Маска геометрии ---
    geometry, num_slits, slit_width, slit_period, start_x = build_geometry_mask(
        params, grid_size, x_edges, y_edges
    )
    
    # --- Вычисление ослабления ---
    # Находим фоновые пиксели (без золота) для референса
    bg_mask = geometry == 0
    if np.sum(bg_mask) > 0:
        mean_bg_counts = np.mean(counts[bg_mask])
    else:
        mean_bg_counts = np.max(counts)
    
    # Аттенюация: I/I0 = counts / mean_bg_counts
    # A = -ln(I/I0)
    signal = np.where(counts > 0, counts / mean_bg_counts, 0)
    attenuation = -np.log(np.clip(signal, 1e-10, None))
    
    # --- Сглаживание ---
    counts_smooth = gaussian_filter(counts.astype(float), sigma=0.8)
    attenuation_smooth = gaussian_filter(attenuation, sigma=0.8)
    
    # ==================== Визуализация ====================
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2.0
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2.0
    extent = [x_range[0], x_range[1], y_range[0], y_range[1]]
    
    fig, axes = plt.subplots(1, 4, figsize=(24, 6))
    
    # 1) Карта количества оптических фотонов
    im1 = axes[0].imshow(
        counts_smooth.T, origin='lower', extent=extent,
        cmap='hot', interpolation='bilinear'
    )
    axes[0].set_xlabel('X, мкм', fontsize=12)
    axes[0].set_ylabel('Y, мкм', fontsize=12)
    axes[0].set_title('Карта количества оптических фотонов', fontsize=13)
    plt.colorbar(im1, ax=axes[0], label='Фотонов/пиксель')
    
    # 2) Аттенюация (рентгеновское изображение)
    att_finite = attenuation_smooth[~np.isinf(attenuation_smooth)]
    if len(att_finite) > 0:
        att_vmin = np.percentile(att_finite, 2)
        att_vmax = np.percentile(att_finite, 98)
    else:
        att_vmin, att_vmax = 0, 1
    
    im2 = axes[1].imshow(
        attenuation_smooth.T, origin='lower', extent=extent,
        cmap='gray_r', interpolation='bilinear',
        vmin=att_vmin, vmax=att_vmax
    )
    axes[1].set_xlabel('X, мкм', fontsize=12)
    axes[1].set_ylabel('Y, мкм', fontsize=12)
    axes[1].set_title(f'Рентгеновское изображение (аттенюация)\nσ=0.8, E={E_OPTICAL_MIN}-{E_OPTICAL_MAX} эВ', fontsize=13)
    plt.colorbar(im2, ax=axes[1], label='A = -ln(I/I₀)')
    
    # 3) Отношение сигнал/фон
    ratio = np.where(bg_mask, counts_smooth / mean_bg_counts, np.nan)
    im3 = axes[2].imshow(
        ratio.T, origin='lower', extent=extent,
        cmap='viridis', interpolation='bilinear',
        vmin=0, vmax=1.2
    )
    axes[2].set_xlabel('X, мкм', fontsize=12)
    axes[2].set_ylabel('Y, мкм', fontsize=12)
    axes[2].set_title('Отношение I/I₀\n(золото = тёмное)', fontsize=13)
    plt.colorbar(im3, ax=axes[2], label='I/I₀')
    
    # 4) Геометрия (золотые полоски)
    im4 = axes[3].imshow(
        geometry, origin='lower', extent=extent,
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
        attenuation_smooth.T, origin='lower', extent=extent,
        cmap='gray_r', interpolation='bilinear',
        vmin=att_vmin, vmax=att_vmax
    )
    ax.set_xlabel('X, мкм', fontsize=14)
    ax.set_ylabel('Y, мкм', fontsize=14)
    ax.set_title(f'Рентгеновское изображение (сцинтилляция)\nE={E_OPTICAL_MIN}-{E_OPTICAL_MAX} эВ, σ=0.8', fontsize=16)
    cbar = plt.colorbar(im, ax=ax, label='A = -ln(I/I₀)')
    plt.tight_layout()
    plt.savefig('xray_scint_attenuation.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("✅ Сохранено: xray_scint_attenuation.png")
    
    # Карта количества (крупно)
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    im = ax.imshow(
        counts_smooth.T, origin='lower', extent=extent,
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
    
    # ==================== Статистика ====================
    print(f"\n{'='*55}")
    print("СТАТИСТИКА:")
    print(f"  Пикселей: {grid_size}x{grid_size} = {grid_size*grid_size:,}")
    print(f"  Ненулевых: {np.sum(counts > 0):,} ({100*np.sum(counts>0)/(grid_size*grid_size):.1f}%)")
    print(f"  Всего оптических фотонов: {len(df_optical):,}")
    print(f"  Максимум/пиксель: {int(np.max(counts))}")
    print(f"  Среднее/пиксель (ненулевые): {np.mean(counts[counts>0]):.1f}")
    print(f"  Среднее (фон, без золота): {mean_bg_counts:.1f}")
    print(f"  Аттенюация макс: {np.max(attenuation_smooth):.3f}")
    
    # Статистика по золоту и фону
    gold_mask = geometry == 1
    if np.sum(gold_mask) > 0 and np.sum(bg_mask) > 0:
        mean_gold_counts = np.mean(counts[gold_mask])
        mean_bg_counts_val = np.mean(counts[bg_mask])
        contrast = 1 - mean_gold_counts / mean_bg_counts_val
        print(f"\n  Среднее (золото): {mean_gold_counts:.1f}")
        print(f"  Среднее (фон): {mean_bg_counts_val:.1f}")
        print(f"  Контраст: {contrast*100:.1f}%")
        print(f"  Отношение I_gold/I_bg: {mean_gold_counts/mean_bg_counts_val:.3f}")
    print(f"{'='*55}")
    
    # ==================== Сохранение данных ====================
    np.savez('xray_scint_data.npz',
             counts=counts,
             counts_smooth=counts_smooth,
             attenuation=attenuation,
             attenuation_smooth=attenuation_smooth,
             geometry=geometry,
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
