import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
import gc

# ------------------- Параметры -------------------
scale = 100

GRID_MIN = -5.0 / scale
GRID_MAX = 5.0 / scale
NUM_BINS = 200
PHOTONS_PER_POSITION = 120
INITIAL_ENERGY = 30.0
SCINTILLATION_YIELD = 54000

# ------------------- Настройка шрифтов -------------------
plt.rcParams['font.size'] = 16
plt.rcParams['axes.labelsize'] = 18
plt.rcParams['axes.titlesize'] = 24
plt.rcParams['xtick.labelsize'] = 15
plt.rcParams['ytick.labelsize'] = 15

# ------------------- БЫСТРОЕ чтение данных -------------------
def read_hits_file_fast(filename):
    """
    Быстрое чтение файла с поддержкой разных кодировок
    """
    for encoding in ['utf-8', 'utf-8-sig', 'latin1', 'cp1251', 'ascii']:
        try:
            # Пытаемся прочитать с заголовком
            df = pd.read_csv(filename, sep='\t', comment='#', encoding=encoding)
            
            # Проверяем наличие нужных колонок
            required_cols = ['Energy_eV', 'PosX_cm', 'PosY_cm', 'Type', 'EventID']
            if all(col in df.columns for col in required_cols):
                pass  # Колонки уже есть
            else:
                # Если колонки не совпадают, читаем без заголовка
                df = pd.read_csv(filename, sep='\t', header=None, comment='#', encoding=encoding)
                if len(df.columns) == 5:
                    df.columns = required_cols
            
            # Конвертируем числовые колонки
            df['Energy_eV'] = pd.to_numeric(df['Energy_eV'], errors='coerce')
            df['PosX_cm'] = pd.to_numeric(df['PosX_cm'], errors='coerce')
            df['PosY_cm'] = pd.to_numeric(df['PosY_cm'], errors='coerce')
            df['EventID'] = pd.to_numeric(df['EventID'], errors='coerce')
            
            # Удаляем строки с NaN
            df.dropna(subset=['Energy_eV', 'PosX_cm', 'PosY_cm', 'Type'], inplace=True)
            
            return df[required_cols]
                
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"Ошибка чтения (кодировка {encoding}): {e}")
            continue
    
    return pd.DataFrame()

print("Быстрое чтение файла...")
df = read_hits_file_fast('hits_data.csv')
print(f"Загружено записей: {len(df):,}")

if len(df) == 0:
    print("ОШИБКА: Не удалось прочитать данные!")
    exit(1)

# Быстрая фильтрация
df_optical = df[(df['Type'] == 'optical_photon') & (df['Energy_eV'] < 10.0)].copy()
print(f"Оптических фотонов: {len(df_optical):,}")

if len(df_optical) == 0:
    print("ОШИБКА: Нет оптических фотонов!")
    print("Доступные типы:", df['Type'].unique())
    exit(1)

# Освобождаем память
del df
gc.collect()

# ------------------- БИНИРОВАНИЕ (оптимизировано) -------------------
print(f"\nБинирование {NUM_BINS}x{NUM_BINS}...")

optical_counts, x_edges, y_edges = np.histogram2d(
    df_optical['PosX_cm'].values,
    df_optical['PosY_cm'].values,
    bins=NUM_BINS,
    range=[[GRID_MIN, GRID_MAX], [GRID_MIN, GRID_MAX]]
)

print(f"  Ненулевых пикселей: {np.sum(optical_counts > 0):,}")
print(f"  Максимум фотонов: {int(np.max(optical_counts))}")

# Освобождаем память
del df_optical
gc.collect()

# Проверка
if np.sum(optical_counts) == 0:
    print("ОШИБКА: Нет данных в сетке!")
    exit(1)

# ------------------- ПОСТОБРАБОТКА -------------------
print("Постобработка...")

# Нормализация
signal_intensity = optical_counts / PHOTONS_PER_POSITION
signal_intensity[signal_intensity == 0] = 1e-6

# Ослабление
attenuation = -np.log(signal_intensity)

# Обрезка по процентилям
attenuation_finite = attenuation[~np.isnan(attenuation) & ~np.isinf(attenuation)]
vmin = np.percentile(attenuation_finite, 5)
vmax = np.percentile(attenuation_finite, 95)

# Нормализация, гамма, сглаживание
attenuation_norm = np.clip((attenuation - vmin) / (vmax - vmin), 0, 1)
attenuation_gamma = np.power(attenuation_norm, 0.5)
attenuation_smoothed = gaussian_filter(attenuation_gamma, sigma=1.0)

# ------------------- ТОЛЬКО ФИНАЛЬНОЕ ИЗОБРАЖЕНИЕ -------------------
print("Создание финального изображения...")

extent = [GRID_MIN, GRID_MAX, GRID_MIN, GRID_MAX]

fig_final, ax_final = plt.subplots(1, 1, figsize=(14, 12))

im_final = ax_final.imshow(
    attenuation_smoothed.T, 
    origin='lower', 
    extent=extent, 
    cmap='gray_r', 
    interpolation='bilinear', 
    vmin=0, 
    vmax=1
)

ax_final.set_xlabel('X, см')
ax_final.set_ylabel('Y, см')
ax_final.set_title(f'Рентгеновское изображение при моделировании (E={INITIAL_ENERGY} кэВ)')

# Увеличиваем метки на осях
ax_final.tick_params(axis='both')

cbar = plt.colorbar(im_final, ax=ax_final)
cbar.set_label('Относительное ослабление')
cbar.ax.tick_params(labelsize=18)

plt.tight_layout()
plt.savefig('xray_image.png', dpi=300, bbox_inches='tight', facecolor='white')
plt.show()

# Сохранение данных
np.savez('xray_data.npz',
         counts=optical_counts,
         attenuation=attenuation_smoothed,
         bins_x=x_edges,
         bins_y=y_edges)

print("\n✓ Готово! Сохранено:")
print("  - xray_image.png (финальное изображение)")
print("  - xray_data.npz (данные)")

# Краткая диагностика
total_photons = int(np.sum(optical_counts))
print(f"\nДиагностика:")
print(f"  Размер: {NUM_BINS}x{NUM_BINS} = {NUM_BINS*NUM_BINS:,} пикселей")
print(f"  Всего фотонов: {total_photons:,}")
print(f"  Максимум фотонов: {int(np.max(optical_counts))}")