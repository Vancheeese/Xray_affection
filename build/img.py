import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
import gc

# ------------------- Параметры -------------------
scale=100

GRID_MIN = -5.0/scale
GRID_MAX = 5.0/scale
NUM_BINS = 200
PHOTONS_PER_POSITION = 3
INITIAL_ENERGY = 30.0
SCINTILLATION_YIELD = 54000

# ------------------- Чтение (простое и надежное) -------------------
def read_hits_file(filename):
    data = []
    
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    # Проверяем первую строку на наличие заголовка
    first_line = lines[0].strip()
    start_row = 0
    
    if 'Energy_eV' in first_line:
        start_row = 1  # Пропускаем заголовок
    
    # Парсим каждую строку
    for line in lines[start_row:]:
        if not line.strip():
            continue
        
        parts = line.strip().split('\t')
        
        # Нам нужны столбцы: Energy_eV, PosX_cm, PosY_cm, Type, EventID
        # Но может быть лишний столбец между PosY_cm и Type
        if len(parts) >= 5:
            energy = float(parts[0])
            pos_x = float(parts[1])
            pos_y = float(parts[2])
            
            # Определяем, где находится Type и EventID
            if len(parts) == 5:
                # Формат: Energy, PosX, PosY, Type, EventID
                type_val = parts[3]
                event_id = int(parts[4])
            elif len(parts) == 6:
                # Формат: Energy, PosX, PosY, Extra, Type, EventID
                type_val = parts[4]
                event_id = int(parts[5])
            else:
                # Пробуем найти Type по ключевому слову
                type_val = None
                event_id = None
                for i, part in enumerate(parts):
                    if 'optical_photon' in part or 'scattered' in part:
                        type_val = part
                        if i + 1 < len(parts):
                            event_id = int(parts[i + 1])
                        break
            
            if type_val is not None:
                data.append([energy, pos_x, pos_y, type_val.lower(), event_id])
    
    # Создаем DataFrame
    df = pd.DataFrame(data, columns=['Energy_eV', 'PosX_cm', 'PosY_cm', 'Type', 'EventID'])
    return df

print("Чтение файла...")
df = read_hits_file('hits_data.csv')
print(f"Загружено записей: {len(df):,}")

if len(df) == 0:
    print("ОШИБКА: Не удалось прочитать данные из файла!")
    exit(1)

# Фильтрация - только оптические фотоны
df_optical = df[df['Type'] == 'optical_photon'].copy()
df_optical = df_optical[df_optical['Energy_eV'] < 10].copy()
print(f"Оптических фотонов: {len(df_optical):,}")

# Статистика событий
if 'EventID' in df_optical.columns and len(df_optical) > 0:
    photons_per_event = df_optical.groupby('EventID').size()
    theoretical_max = INITIAL_ENERGY * SCINTILLATION_YIELD / 1000
    print(f"\nСтатистика по событиям:")
    print(f"  Всего событий: {len(photons_per_event):,}")
    print(f"  Фотонов на событие: мин={photons_per_event.min()}, "
          f"ср={photons_per_event.mean():.0f}, макс={photons_per_event.max()}")
    print(f"  Теоретический максимум: {theoretical_max:.0f}")

del df
gc.collect()

# ------------------- БИНИРОВАНИЕ -------------------
print(f"\nБинирование координат в сетку {NUM_BINS}x{NUM_BINS}...")
print(f"Обрабатывается {len(df_optical):,} фотонов...")

if len(df_optical) == 0:
    print("ОШИБКА: Нет оптических фотонов для обработки!")
    exit(1)

optical_counts, x_edges, y_edges = np.histogram2d(
    df_optical['PosX_cm'].values,
    df_optical['PosY_cm'].values,
    bins=NUM_BINS,
    range=[[GRID_MIN, GRID_MAX], [GRID_MIN, GRID_MAX]]
)

print(f"Готово!")
print(f"  Ненулевых пикселей: {np.sum(optical_counts > 0):,}")
print(f"  Минимум фотонов: {np.min(optical_counts):.0f}")
print(f"  Максимум фотонов: {int(np.max(optical_counts))}")

del df_optical
gc.collect()

# ------------------- ПОСТОБРАБОТКА -------------------
print("\nПостобработка...")

# 1. Нормализация интенсивности
signal_intensity = optical_counts / PHOTONS_PER_POSITION

# 2. Заменяем нули на очень маленькое значение (чтобы избежать -inf)
signal_intensity[signal_intensity == 0] = 1e-6

# 3. Вычисляем ослабление
attenuation = -np.log(signal_intensity)

# 4. Обрезаем экстремальные значения (процентили для хорошего контраста)
p_low = 5   # Нижний процентиль
p_high = 95 # Верхний процентиль

vmin = np.percentile(attenuation[~np.isnan(attenuation)], p_low)
vmax = np.percentile(attenuation[~np.isnan(attenuation)], p_high)

print(f"Диапазон ослабления: [{vmin:.2f}, {vmax:.2f}]")

# 5. Нормируем в [0, 1]
attenuation_norm = np.clip((attenuation - vmin) / (vmax - vmin), 0, 1)

# 6. Гамма-коррекция для улучшения контраста
gamma = 0.5
attenuation_gamma = np.power(attenuation_norm, gamma)

# 7. Сглаживание
print("Сглаживание...")
attenuation_smoothed = gaussian_filter(attenuation_gamma, sigma=1.0)

# ------------------- ВИЗУАЛИЗАЦИЯ -------------------
print("Визуализация...")
extent = [GRID_MIN, GRID_MAX, GRID_MIN, GRID_MAX]

fig, axes = plt.subplots(2, 2, figsize=(14, 12))

# 1. Сырые counts
im1 = axes[0,0].imshow(optical_counts.T, origin='lower', extent=extent, 
                        cmap='hot', interpolation='nearest')
axes[0,0].set_title('Количество фотонов (сырые данные)')
axes[0,0].set_xlabel('X, см')
axes[0,0].set_ylabel('Y, см')
plt.colorbar(im1, ax=axes[0,0], label='Количество фотонов')

# 2. Интенсивность (лог-шкала)
im2 = axes[0,1].imshow(np.log10(optical_counts.T + 1), origin='lower', extent=extent, 
                        cmap='viridis', interpolation='nearest')
axes[0,1].set_title('Логарифм количества фотонов')
axes[0,1].set_xlabel('X, см')
axes[0,1].set_ylabel('Y, см')
plt.colorbar(im2, ax=axes[0,1], label='log10(фотонов)')

# 3. Ослабление (нормализованное)
im3 = axes[1,0].imshow(attenuation_gamma.T, origin='lower', extent=extent, 
                        cmap='gray_r', interpolation='bilinear', vmin=0, vmax=1)
axes[1,0].set_title('Рентгеновское изображение (ослабление)')
axes[1,0].set_xlabel('X, см')
axes[1,0].set_ylabel('Y, см')
plt.colorbar(im3, ax=axes[1,0], label='Относительное ослабление')

# 4. Сглаженное изображение
im4 = axes[1,1].imshow(attenuation_smoothed.T, origin='lower', extent=extent, 
                        cmap='gray_r', interpolation='bilinear', vmin=0, vmax=1)
axes[1,1].set_title('Рентгеновское изображение (сглаженное)')
axes[1,1].set_xlabel('X, см')
axes[1,1].set_ylabel('Y, см')
plt.colorbar(im4, ax=axes[1,1], label='Относительное ослабление')

plt.suptitle(f'Сцинтилляционный детектор CsI, E={INITIAL_ENERGY} кэВ', fontsize=14)
plt.tight_layout()
plt.savefig('xray_image.png', dpi=300, bbox_inches='tight')
plt.show()

# ------------------- ОТДЕЛЬНОЕ ИЗОБРАЖЕНИЕ ДЛЯ СОХРАНЕНИЯ -------------------
print("\nСоздание финального изображения...")
fig_final, ax_final = plt.subplots(1, 1, figsize=(12, 10))

im_final = ax_final.imshow(attenuation_smoothed.T, origin='lower', extent=extent, 
                            cmap='gray_r', interpolation='bilinear', vmin=0, vmax=1)
ax_final.set_xlabel('X, см', fontsize=12)
ax_final.set_ylabel('Y, см', fontsize=12)
ax_final.set_title(f'Рентгеновский снимок (CsI сцинтиллятор, {INITIAL_ENERGY} кэВ)', fontsize=14)

cbar = plt.colorbar(im_final, ax=ax_final, fraction=0.046, pad=0.04)
cbar.set_label('Относительное ослабление', fontsize=10)

plt.tight_layout()
plt.savefig('xray_final.png', dpi=300, bbox_inches='tight', facecolor='black')
plt.show()

print("\n✓ Сохранено:")
print("  - xray_image.png (четыре графика)")
print("  - xray_final.png (финальное изображение)")
print("  - xray_data.npz (данные)")

# Сохранение данных
np.savez('xray_data.npz',
         counts=optical_counts,
         attenuation=attenuation_smoothed,
         bins_x=x_edges,
         bins_y=y_edges)

# ------------------- ДИАГНОСТИКА -------------------
print("\n" + "="*60)
print("ДИАГНОСТИКА")
print("="*60)
print(f"Размер сетки: {NUM_BINS} x {NUM_BINS} = {NUM_BINS*NUM_BINS:,} пикселей")
print(f"Пикселей с фотонами: {np.sum(optical_counts > 0):,}")
print(f"Пустых пикселей: {np.sum(optical_counts == 0):,}")
print(f"Всего фотонов: {int(np.sum(optical_counts)):,}")
print(f"Среднее фотонов на пиксель: {np.mean(optical_counts):.2f}")
print(f"Максимум фотонов: {int(np.max(optical_counts))}")

# Проверка распределения
if np.max(optical_counts) > 0:
    print(f"\nРаспределение интенсивности:")
    print(f"  Пикселей с <10% от максимума: {np.sum(optical_counts < 0.1 * np.max(optical_counts)):,}")
    print(f"  Пикселей с >90% от максимума: {np.sum(optical_counts > 0.9 * np.max(optical_counts)):,}")