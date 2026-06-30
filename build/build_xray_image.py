import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
import re
import os

# ==================== Чтение параметров из global_parameters.cc ====================
def read_global_parameters():
    """Читает pixelSize и gridSize из global_parameters.cc (папка src/ рядом со скриптом)"""
    params = {}
    
    # Путь к файлу относительно текущего скрипта
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cc_file = os.path.join(script_dir, '..', 'src', 'global_parameters.cc')
    
    if not os.path.exists(cc_file):
        print(f"Файл не найден: {cc_file}")
        print(f"Используем значения по умолчанию: pixelSize=10, gridSize=100, slitWidth=50")
        return {'pixelSize': 10.0, 'gridSize': 100, 'slitWidth': 50.0}
    
    print(f"  Файл параметров: {cc_file}")
    
    with open(cc_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Ищем pixelSize
    match = re.search(r'pixelSize\s*=\s*([\d.]+)', content)
    if match:
        params['pixelSize'] = float(match.group(1))
    else:
        params['pixelSize'] = 10.0
    
    # Ищем gridSize
    match = re.search(r'gridSize\s*=\s*(\d+)', content)
    if match:
        params['gridSize'] = int(match.group(1))
    else:
        params['gridSize'] = 100
    
    # Ищем slitWidth
    match = re.search(r'slitWidth\s*=\s*([\d.]+)', content)
    if match:
        params['slitWidth'] = float(match.group(1))
    else:
        params['slitWidth'] = 50.0
    
    # Ищем particlesPerPixel
    match = re.search(r'particlesPerPixel\s*=\s*(\d+)', content)
    if match:
        params['particlesPerPixel'] = int(match.group(1))
    else:
        params['particlesPerPixel'] = 1
    
    return params

# ==================== Чтение данных ====================
def read_hits_data(filename='hits_data.csv'):
    """Читает файл с данными о фотонах"""
    for encoding in ['utf-8', 'utf-8-sig', 'latin1', 'cp1251']:
        try:
            df = pd.read_csv(filename, sep='\t', comment='#', encoding=encoding, low_memory=False)
            required_cols = ['Energy_eV', 'PosX_um', 'PosY_um']
            if all(col in df.columns for col in required_cols):
                df['Energy_eV'] = pd.to_numeric(df['Energy_eV'], errors='coerce')
                df['PosX_um'] = pd.to_numeric(df['PosX_um'], errors='coerce')
                df['PosY_um'] = pd.to_numeric(df['PosY_um'], errors='coerce')
                df.dropna(subset=['Energy_eV', 'PosX_um', 'PosY_um'], inplace=True)
                return df[required_cols]
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"Ошибка чтения: {e}")
            continue
    
    return pd.DataFrame()

# ==================== Построение изображения ====================
def build_image(df, params, output_prefix='xray'):
    """Строит 2D изображения и сохраняет их"""
    
    pixel_size = params['pixelSize']  # мкм
    grid_size = params['gridSize']
    lead_size = pixel_size * grid_size  # общий размер в мкм
    
    # Фильтрация оптических фотонов
    df_optical = df[df['Energy_eV'] < 10.0].copy()
    print(f"Загружено фотонов: {len(df)}, оптических: {len(df_optical)}")
    
    if len(df_optical) == 0:
        print("ОШИБКА: Нет оптических фотонов!")
        return
    
    # Диапазон для гистограммы
    x_range = (-lead_size / 2, lead_size / 2)
    y_range = (-lead_size / 2, lead_size / 2)
    
    # ==================== Вариант 1: Карта количества фотонов ====================
    print("\nСтроим карту количества фотонов...")
    counts, x_edges, y_edges = np.histogram2d(
        df_optical['PosX_um'].values,
        df_optical['PosY_um'].values,
        bins=grid_size,
        range=[x_range, y_range]
    )
    
    # Сглаживание
    counts_smooth = gaussian_filter(counts.astype(float), sigma=1.0)
    counts_max = np.max(counts_smooth)
    counts_norm = counts_smooth / counts_max if counts_max > 0 else counts_smooth
    
    # Сохраняем изображение количества
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    
    im = ax.imshow(
        counts_norm.T,
        origin='lower',
        extent=[x_range[0], x_range[1], y_range[0], y_range[1]],
        cmap='gray_r',
        interpolation='bilinear'
    )
    
    ax.set_xlabel('X, мкм', fontsize=14)
    ax.set_ylabel('Y, мкм', fontsize=14)
    ax.set_title(f'Карта количества оптических фотонов\n'
                 f'pixelSize={pixel_size} мкм, gridSize={grid_size}, '
                 f'размер={lead_size} мкм', fontsize=16)
    
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Относительное количество', fontsize=12)
    
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_counts.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Сохранено: {output_prefix}_counts.png")
    
    # Сохраняем данные counts
    np.savez(f'{output_prefix}_counts_data.npz',
             counts=counts,
             counts_norm=counts_norm,
             x_edges=x_edges,
             y_edges=y_edges)
    print(f"Сохранено: {output_prefix}_counts_data.npz")
    
    # ==================== Вариант 2: Аттенюация ====================
    print("\nСтроим аттенюацию...")
    
    photons_per_pixel = params['particlesPerPixel']
    signal = counts / photons_per_pixel
    signal[signal == 0] = 1e-6
    
    attenuation = -np.log(signal)
    
    # Обрезка по процентилям для лучшей контрастности
    att_finite = attenuation[~np.isnan(attenuation) & ~np.isinf(attenuation)]
    if len(att_finite) > 0:
        vmin = np.percentile(att_finite, 5)
        vmax = np.percentile(att_finite, 95)
    else:
        vmin, vmax = 0, 1
    
    att_norm = np.clip((attenuation - vmin) / (vmax - vmin), 0, 1)
    att_gamma = np.power(att_norm, 0.5)  # гамма-коррекция
    att_smooth = gaussian_filter(att_gamma, sigma=1.0)
    
    # Сохраняем изображение аттенюации
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    
    im = ax.imshow(
        att_smooth.T,
        origin='lower',
        extent=[x_range[0], x_range[1], y_range[0], y_range[1]],
        cmap='gray_r',
        interpolation='bilinear',
        vmin=0,
        vmax=1
    )
    
    ax.set_xlabel('X, мкм', fontsize=14)
    ax.set_ylabel('Y, мкм', fontsize=14)
    ax.set_title(f'Рентгеновское изображение (аттенюация)\n'
                 f'E < 10 эВ, pixelSize={pixel_size} мкм, gridSize={grid_size}',
                 fontsize=16)
    
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Относительное ослабление', fontsize=12)
    
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_attenuation.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Сохранено: {output_prefix}_attenuation.png")
    
    # Сохраняем данные аттенюации
    np.savez(f'{output_prefix}_attenuation_data.npz',
             attenuation=att_smooth,
             attenuation_raw=attenuation,
             x_edges=x_edges,
             y_edges=y_edges)
    print(f"Сохранено: {output_prefix}_attenuation_data.npz")
    
    # ==================== Вариант 3: Базовая геометрия (золотые полоски) ====================
    print("\nСтроим базовую геометрию (золотые полоски)...")
    
    slit_width = params['slitWidth']
    slit_period = slit_width + slit_width  # шаг = ширина + зазор (равный ширине)
    num_slits = int(lead_size / slit_period) if slit_period > 0 else 0
    total_width = num_slits * slit_period
    start_x = -total_width / 2.0 + slit_width / 2.0
    
    # Создаём бинарную маску: 1 = золото, 0 = зазор
    # Полоски ориентированы вдоль оси Y
    geometry = np.zeros((grid_size, grid_size), dtype=float)
    
    x_edges_arr = np.linspace(x_range[0], x_range[1], grid_size + 1)
    x_centers = (x_edges_arr[:-1] + x_edges_arr[1:]) / 2.0
    
    for i in range(num_slits):
        slit_center_x = start_x + i * slit_period
        slit_left = slit_center_x - slit_width / 2.0
        slit_right = slit_center_x + slit_width / 2.0
        
        mask_x = (x_centers >= slit_left) & (x_centers < slit_right)
        geometry[:, mask_x] = 1.0  # полоска на всю длину по Y
    
    # Сглаживание для визуализации
    geometry_smooth = gaussian_filter(geometry, sigma=0.5)
    
    # Сохраняем изображение геометрии
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    
    im = ax.imshow(
        geometry_smooth,
        origin='lower',
        extent=[x_range[0], x_range[1], y_range[0], y_range[1]],
        cmap='Greys',
        interpolation='nearest',
        vmin=0,
        vmax=1
    )
    
    ax.set_xlabel('X, мкм', fontsize=14)
    ax.set_ylabel('Y, мкм', fontsize=14)
    ax.set_title(f'Базовая геометрия: золотые полоски\n'
                 f'Полосок: {num_slits}, ширина: {slit_width} мкм, '
                 f'шаг: {slit_period} мкм', fontsize=16)
    
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Золото (1) / Пустота (0)', fontsize=12)
    
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_geometry.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Сохранено: {output_prefix}_geometry.png")
    
    # Сохраняем данные геометрии
    np.savez(f'{output_prefix}_geometry_data.npz',
             geometry=geometry,
             geometry_smooth=geometry_smooth,
             x_edges=x_edges,
             y_edges=y_edges,
             num_slits=num_slits,
             slit_width=slit_width,
             slit_period=slit_period,
             start_x=start_x)
    print(f"Сохранено: {output_prefix}_geometry_data.npz")
    
    # ==================== Статистика ====================
    print(f"\n{'='*50}")
    print(f"Статистика:")
    print(f"  Параметров: pixelSize={pixel_size} мкм, gridSize={grid_size}")
    print(f"  Размер области: {lead_size} мкм x {lead_size} мкм")
    print(f"  Полосок: {num_slits}, ширина: {slit_width} мкм, шаг: {slit_period} мкм")
    print(f"  Всего фотонов: {len(df_optical):,}")
    print(f"  Ненулевых пикселей (counts): {np.sum(counts > 0):,}")
    print(f"  Максимум counts: {int(np.max(counts))}")
    print(f"  Максимум attenuation: {np.max(att_smooth):.3f}")
    print(f"{'='*50}")

# ==================== Основная функция ====================
def main():
    print("=" * 50)
    print("Скрипт для построения рентгеновского изображения")
    print("=" * 50)
    
    # Чтение параметров
    print("\nЧтение параметров из global_parameters.cc...")
    params = read_global_parameters()
    print(f"  pixelSize = {params['pixelSize']} мкм")
    print(f"  gridSize = {params['gridSize']}")
    print(f"  slitWidth = {params['slitWidth']} мкм")
    print(f"  particlesPerPixel = {params['particlesPerPixel']}")
    
    # Чтение данных
    print("\nЧтение hits_data.csv...")
    df = read_hits_data('hits_data.csv')
    print(f"  Загружено записей: {len(df):,}")
    
    if len(df) == 0:
        print("ОШИБКА: Не удалось прочитать данные!")
        return
    
    # Построение изображений
    print("\n" + "=" * 50)
    build_image(df, params, output_prefix='xray')
    print("\nГотово!")

if __name__ == '__main__':
    main()
