#!/usr/bin/env python3
"""
Правильное измерение ширины горизонтальных щелей
Адаптировано под новые щели: 90, 110, 130 мкм
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter

def measure_slit_width(csv_file, slit_y_mm, real_width_um):
    """Измерение ширины горизонтальной щели по Y профилю"""
    
    df = pd.read_csv(csv_file, sep='\t')
    df_optical = df[df['Type'] == 'optical_photon']
    df_optical = df_optical[df_optical['Energy_eV'] < 10]
    
    # Профиль по Y (усредняем по X в центре)
    x_range = 0.02  # см (200 мкм) - берём только центр по X
    df_center = df_optical[(df_optical['PosX_cm'] > -x_range/2) & 
                            (df_optical['PosX_cm'] < x_range/2)]
    
    y_bins = np.linspace(-0.05, 0.05, 1000)  # высокое разрешение
    y_hist, y_edges = np.histogram(df_center['PosY_cm'], bins=y_bins)
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2
    
    # Сглаживание
    y_hist_smoothed = gaussian_filter(y_hist, sigma=2.0)
    
    # Нормализация
    if y_hist_smoothed.max() > 0:
        y_hist_norm = y_hist_smoothed / y_hist_smoothed.max()
    else:
        return 0, 0, None, None
    
    # Ищем пик около ожидаемой позиции
    y_pos_cm = slit_y_mm / 10
    y_idx = np.argmin(np.abs(y_centers - y_pos_cm))
    search_range = slice(max(0, y_idx-100), min(len(y_centers), y_idx+100))
    
    # Проверяем, что есть данные в диапазоне
    if search_range.start >= search_range.stop:
        return 0, 0, None, None
    
    local_max_idx = np.argmax(y_hist_norm[search_range]) + search_range.start
    
    # Измеряем FWHM
    max_val = y_hist_norm[local_max_idx]
    if max_val < 0.1:
        return 0, 0, None, None
        
    half_max = max_val / 2
    
    left = local_max_idx
    while left > 0 and y_hist_norm[left] > half_max:
        left -= 1
    
    right = local_max_idx
    while right < len(y_hist_norm) - 1 and y_hist_norm[right] > half_max:
        right += 1
    
    # Ширина в микронах
    width_cm = y_centers[right] - y_centers[left]
    width_um = width_cm * 10000  # 1 см = 10000 мкм
    
    return width_um, max_val, y_centers, y_hist_norm


# ==================== НОВЫЕ ПАРАМЕТРЫ ЩЕЛЕЙ ====================
# При разрешении ~90 мкм, щели должны быть: 90, 110, 130 мкм
SLITS = {
    '90um': {'y_pos_mm': -0.250, 'real_width_um': 90, 'color': 'red'},
    '110um': {'y_pos_mm': 0.000, 'real_width_um': 110, 'color': 'green'},
    '130um': {'y_pos_mm': 0.250, 'real_width_um': 130, 'color': 'blue'},
}

THICKNESSES = [10, 25, 50, 75, 100, 150, 200, 300, 500]

# ==================== АНАЛИЗ ====================

print("="*70)
print("ИЗМЕРЕНИЕ ШИРИНЫ ЩЕЛЕЙ (НОВЫЕ ЩЕЛИ: 90, 110, 130 мкм)")
print("="*70)

results = {}

for thickness in THICKNESSES:
    filepath = f"results/hits_data_{thickness}um.csv"
    
    try:
        df_test = pd.read_csv(filepath, sep='\t')
    except:
        print(f"\n❌ Файл не найден: {thickness} мкм")
        continue
    
    print(f"\n📊 Толщина CsI: {thickness} мкм")
    print("-" * 50)
    
    for slit_name, params in SLITS.items():
        try:
            width_um, max_val, y_centers, profile = measure_slit_width(
                filepath, params['y_pos_mm'], params['real_width_um']
            )
            
            if width_um == 0:
                print(f"  Щель {slit_name}: не обнаружена")
                continue
                
            real_width = params['real_width_um']
            blur = width_um - real_width
            status = "✅" if width_um < real_width * 1.5 else "⚠️"
            
            print(f"  Щель {slit_name}: измерено {width_um:.0f} мкм (реально {real_width} мкм), размытие {blur:.0f} мкм {status}")
            
            results.setdefault(thickness, {})[slit_name] = width_um
            results.setdefault(thickness, {})[f'{slit_name}_blur'] = blur
            
        except Exception as e:
            print(f"  Щель {slit_name}: ошибка - {e}")

# ==================== СВОДНАЯ ТАБЛИЦА ====================

print("\n" + "="*70)
print("СВОДНАЯ ТАБЛИЦА (измеренная ширина щелей, мкм)")
print("="*70)
print("Толщина | 90um щель | 110um щель | 130um щель")
print("-" * 55)

for t in THICKNESSES:
    if t in results:
        print(f"{t:5d} мкм | {results[t].get('90um', 0):9.0f} | {results[t].get('110um', 0):10.0f} | {results[t].get('130um', 0):10.0f}")

# ==================== ГРАФИКИ ====================

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# График 1: Измеренная ширина vs толщина
ax1 = axes[0]
colors = {'90um': 'red', '110um': 'green', '130um': 'blue'}
for slit_name, params in SLITS.items():
    thick_list = []
    width_list = []
    for t in THICKNESSES:
        if t in results and slit_name in results[t]:
            thick_list.append(t)
            width_list.append(results[t][slit_name])
    
    if thick_list:
        ax1.plot(thick_list, width_list, 'o-', color=colors[slit_name], 
                label=f'Щель {params["real_width_um"]} мкм', linewidth=2, markersize=8)
        ax1.axhline(y=params['real_width_um'], color=colors[slit_name], 
                   linestyle='--', alpha=0.3)

ax1.set_xlabel('Толщина сцинтиллятора CsI (мкм)', fontsize=12)
ax1.set_ylabel('Измеренная ширина щели (мкм)', fontsize=12)
ax1.set_title('Зависимость измеренной ширины от толщины CsI', fontsize=12)
ax1.legend()
ax1.grid(True, alpha=0.3)
ax1.set_xscale('log')

# График 2: Размытие vs толщина
ax2 = axes[1]
for slit_name, params in SLITS.items():
    thick_list = []
    blur_list = []
    for t in THICKNESSES:
        if t in results and f'{slit_name}_blur' in results[t]:
            thick_list.append(t)
            blur_list.append(results[t][f'{slit_name}_blur'])
    
    if thick_list:
        ax2.plot(thick_list, blur_list, 'o-', color=colors[slit_name], 
                label=f'Щель {params["real_width_um"]} мкм', linewidth=2, markersize=8)

ax2.set_xlabel('Толщина сцинтиллятора CsI (мкм)', fontsize=12)
ax2.set_ylabel('Размытие (измеренная - реальная) мкм', fontsize=12)
ax2.set_title('Размытие изображения от толщины CsI', fontsize=12)
ax2.legend()
ax2.grid(True, alpha=0.3)
ax2.set_xscale('log')

plt.suptitle('ОЦЕНКА РАЗРЕШАЮЩЕЙ СПОСОБНОСТИ (НОВЫЕ ЩЕЛИ 90-130 мкм)', fontsize=14)
plt.tight_layout()
plt.savefig('resolution_new_slits.png', dpi=150)
plt.show()

print("\n✅ График сохранён: resolution_new_slits.png")