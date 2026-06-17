#!/usr/bin/env python3
"""
Правильное измерение ширины горизонтальных щелей
Адаптировано под новые щели: 90, 110, 130 мкм
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
import os

def read_hits_file_safe(filepath):
    """
    Надёжное чтение файла hits_data_*.csv с обработкой кодировок и бинарного мусора
    """
    if not os.path.exists(filepath):
        return None
    
    # Проверка размера
    file_size = os.path.getsize(filepath)
    if file_size < 100:
        print(f"⚠️ Файл слишком маленький ({file_size} байт) — удаляем")
        os.remove(filepath)
        return None
    
    # Пробуем разные кодировки
    encodings = ['utf-8', 'latin-1', 'cp1251', 'iso-8859-1']
    lines = None
    
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                content = f.read()
                if '\t' in content or ' ' in content:
                    lines = content.splitlines()
                    break
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    # Если не удалось, читаем как бинарный и очищаем
    if lines is None:
        try:
            with open(filepath, 'rb') as f:
                raw = f.read()
                clean_bytes = []
                for b in raw:
                    if (32 <= b <= 126) or b in (9, 10, 13):
                        clean_bytes.append(b)
                    else:
                        clean_bytes.append(32)
                clean_text = bytes(clean_bytes).decode('ascii')
                lines = clean_text.splitlines()
        except Exception as e:
            print(f"❌ Ошибка чтения бинарного файла: {e}")
            return None
    
    if not lines:
        return None
    
    # Определяем заголовок
    first_line = lines[0].strip()
    start_row = 0
    if 'Energy_eV' in first_line and 'PosX_cm' in first_line and 'PosY_cm' in first_line:
        start_row = 1
    
    data = []
    for line in lines[start_row:]:
        if not line.strip():
            continue
        # Очищаем от непечатаемых
        line = ''.join(c for c in line if c.isprintable() or c in '\t\n\r')
        parts = line.strip().split('\t')
        if len(parts) == 5:
            try:
                energy = float(parts[0])
                pos_x = float(parts[1])
                pos_y = float(parts[2])
                type_val = parts[3].lower().strip()
                event_id = int(parts[4])
                data.append([energy, pos_x, pos_y, type_val, event_id])
            except:
                continue
        elif len(parts) >= 5:
            # Попытка с пробелами
            try:
                parts2 = line.strip().split()
                if len(parts2) >= 5:
                    energy = float(parts2[0])
                    pos_x = float(parts2[1])
                    pos_y = float(parts2[2])
                    type_val = parts2[3].lower().strip()
                    event_id = int(parts2[4])
                    data.append([energy, pos_x, pos_y, type_val, event_id])
            except:
                continue
    
    if not data:
        return None
    
    df = pd.DataFrame(data, columns=['Energy_eV', 'PosX_cm', 'PosY_cm', 'Type', 'EventID'])
    return df


def measure_slit_width(df, slit_y_mm, real_width_um):
    """Измерение ширины горизонтальной щели по Y профилю"""
    
    if df is None or len(df) == 0:
        return 0, 0, None, None
    
    df_optical = df[df['Type'] == 'optical_photon'].copy()
    df_optical = df_optical[df_optical['Energy_eV'] < 10]
    
    if len(df_optical) == 0:
        return 0, 0, None, None
    
    # Профиль по Y (усредняем по X в центре)
    x_range = 0.02  # см (200 мкм) - берём только центр по X
    df_center = df_optical[(df_optical['PosX_cm'] > -x_range/2) & 
                            (df_optical['PosX_cm'] < x_range/2)]
    
    if len(df_center) == 0:
        return 0, 0, None, None
    
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
SLITS = {
    '90um': {'y_pos_mm': -0.250, 'real_width_um': 90, 'color': 'red'},
    '110um': {'y_pos_mm': 0.000, 'real_width_um': 110, 'color': 'green'},
    '130um': {'y_pos_mm': 0.250, 'real_width_um': 130, 'color': 'blue'},
}

# Актуальные толщины (соответствуют run_thickness.sh)
THICKNESSES = [50, 100, 150, 200, 300, 500]

# ==================== АНАЛИЗ ====================

print("="*70)
print("ИЗМЕРЕНИЕ ШИРИНЫ ЩЕЛЕЙ (НОВЫЕ ЩЕЛИ: 90, 110, 130 мкм)")
print("="*70)

results = {}

for thickness in THICKNESSES:
    filepath = f"results/hits_data_{thickness}um.csv"
    
    # Читаем файл безопасно
    df = read_hits_file_safe(filepath)
    
    if df is None:
        print(f"\n❌ Не удалось прочитать файл для толщины {thickness} мкм")
        continue
    
    print(f"\n📊 Толщина CsI: {thickness} мкм")
    print("-" * 50)
    
    for slit_name, params in SLITS.items():
        try:
            width_um, max_val, y_centers, profile = measure_slit_width(
                df, params['y_pos_mm'], params['real_width_um']
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