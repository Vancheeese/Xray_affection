import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, LinearSegmentedColormap

# --- Параметры эксперимента ---
GRID_MIN = -5.0          # Минимальная координата сетки (см)
GRID_MAX = 5.0           # Максимальная координата сетки (см)
STEP = 10/99               # Шаг сетки (см)
PHOTONS_PER_POSITION = 500  # Количество фотонов, испущенных из каждой позиции
INITIAL_ENERGY = 80.0    # Начальная энергия фотонов (кэВ)

# --- Чтение данных из файла ---
# Файл имеет заголовок, разделитель - табуляция (пробелы)
df = pd.read_csv('hits_data.csv', delimiter='\t')

# Проверяем, что данные загрузились
print(f"Загружено записей: {len(df)}")
print(f"Первые 5 строк:\n{df.head()}")

# --- Группировка и анализ данных ---
# Группируем по координатам X и Y
grouped = df.groupby(['PosX_cm', 'PosY_cm'])

# Для каждой позиции считаем количество попавших фотонов и сумму их энергий
hit_counts = grouped.size().rename('hit_count')
energy_sum = grouped['Energy_keV'].sum().rename('energy_sum')

# Объединяем результаты в один DataFrame
stats = pd.concat([hit_counts, energy_sum], axis=1).reset_index()

# Добавляем колонку с теоретическим ожидаемым количеством фотонов (без ослабления)
stats['expected_count'] = PHOTONS_PER_POSITION

# Добавляем колонку с коэффициентом пропускания (Transmission)
# Transmission = (попавшие фотоны) / (испущенные фотоны)
stats['transmission'] = stats['hit_count'] / PHOTONS_PER_POSITION

# Добавляем колонку с измеренным ослаблением (Attenuation = -ln(Transmission))
# Для позиций, где фотоны не попали, Transmission = 0, Attenuation = inf.
# Заменим inf на большое число для визуализации
with np.errstate(divide='ignore'):
    stats['attenuation'] = -np.log(stats['transmission'])
stats['attenuation'].replace([np.inf, -np.inf], np.nan, inplace=True)

# --- Создание сетки для изображения ---
# Определяем координаты всех позиций сетки
x_coords = np.arange(GRID_MIN, GRID_MAX + STEP/2, STEP)
y_coords = np.arange(GRID_MIN, GRID_MAX + STEP/2, STEP)
X_grid, Y_grid = np.meshgrid(x_coords, y_coords, indexing='ij')

# Создаём массивы для значений на сетке
hit_grid = np.zeros_like(X_grid, dtype=float)
transmission_grid = np.zeros_like(X_grid, dtype=float)
attenuation_grid = np.full_like(X_grid, np.nan, dtype=float)

# Заполняем сетку данными из статистики
for _, row in stats.iterrows():
    ix = np.abs(x_coords - row['PosX_cm']).argmin()
    iy = np.abs(y_coords - row['PosY_cm']).argmin()
    hit_grid[ix, iy] = row['hit_count']
    transmission_grid[ix, iy] = row['transmission']
    attenuation_grid[ix, iy] = row['attenuation']

# --- Создание рентгеновской цветовой карты (черно-белая с инверсией) ---
# Медицинские рентгеновские снимки: плотные ткани (высокое ослабление) - белые,
# воздух/мягкие ткани (низкое ослабление) - черные
xray_cmap = LinearSegmentedColormap.from_list('xray', ['black', 'gray', 'white'])
# Альтернатива: инвертированная grayscale
xray_cmap_inv = 'gray_r'  # _r означает инверсию (черный->белый)

# Для цветных рентгеновских снимков (псевдоцвета как в медицинских сканерах)
medical_cmap = LinearSegmentedColormap.from_list('medical', ['black', '#4a0e4e', '#8b3a62', '#d96c6c', '#f5c4a3', 'white'])

# --- Визуализация ---
fig, axes = plt.subplots(2, 2, figsize=(14, 11))
fig.suptitle('Рентгеновское изображение (40 кэВ) - анализ пропускания', fontsize=16, fontweight='bold')

# 1. Карта количества зарегистрированных фотонов (рентгеновский стиль)
im1 = axes[0, 0].imshow(hit_grid.T, origin='lower', extent=[GRID_MIN, GRID_MAX, GRID_MIN, GRID_MAX],
                        cmap=xray_cmap_inv, interpolation='nearest')
axes[0, 0].set_title('Детектированные фотоны (рентгеновский режим)', fontsize=12)
axes[0, 0].set_xlabel('X, см')
axes[0, 0].set_ylabel('Y, см')
plt.colorbar(im1, ax=axes[0, 0], label='Количество фотонов')

# 2. Карта коэффициента пропускания
im2 = axes[0, 1].imshow(transmission_grid.T, origin='lower', extent=[GRID_MIN, GRID_MAX, GRID_MIN, GRID_MAX],
                        cmap='viridis', vmin=0, vmax=1, interpolation='nearest')
axes[0, 1].set_title('Коэффициент пропускания (I/I₀)', fontsize=12)
axes[0, 1].set_xlabel('X, см')
axes[0, 1].set_ylabel('Y, см')
plt.colorbar(im2, ax=axes[0, 1], label='Пропускание')

# 3. Классическое рентгеновское изображение (ослабление, черно-белое)
# Нормализуем значения для лучшего контраста
attenuation_clean = attenuation_grid.copy()
attenuation_max = np.nanpercentile(attenuation_clean, 99)  # Игнорируем выбросы
attenuation_clean = np.clip(attenuation_clean, 0, attenuation_max)

im3 = axes[1, 0].imshow(attenuation_clean.T, origin='lower', extent=[GRID_MIN, GRID_MAX, GRID_MIN, GRID_MAX],
                        cmap=xray_cmap_inv, interpolation='nearest', vmin=0, vmax=attenuation_max)
axes[1, 0].set_title('Рентгеновский снимок (ослабление) - µ·x', fontsize=12, fontweight='bold')
axes[1, 0].set_xlabel('X, см')
axes[1, 0].set_ylabel('Y, см')
plt.colorbar(im3, ax=axes[1, 0], label='Ослабление, -ln(I/I₀)')

# Добавляем пояснение
axes[1, 0].text(0.02, 0.98, 'Белый = высокая плотность\nЧерный = низкая плотность', 
                transform=axes[1, 0].transAxes, fontsize=9,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# 4. Рентгеновское изображение в улучшенном контрасте (медицинский стиль)
# Применяем гамма-коррекцию для лучшей видимости деталей
attenuation_gamma = np.power(attenuation_clean / attenuation_max, 0.5)  # Гамма 0.5
im4 = axes[1, 1].imshow(attenuation_gamma.T, origin='lower', extent=[GRID_MIN, GRID_MAX, GRID_MIN, GRID_MAX],
                        cmap=xray_cmap_inv, interpolation='bilinear')
axes[1, 1].set_title('Рентгеновский снимок (улучшенный контраст)', fontsize=12)
axes[1, 1].set_xlabel('X, см')
axes[1, 1].set_ylabel('Y, см')
plt.colorbar(im4, ax=axes[1, 1], label='Нормированное ослабление')

plt.tight_layout()
plt.show()

# --- Дополнительное окно с увеличенным рентгеновским изображением ---
fig2, ax2 = plt.subplots(1, 1, figsize=(10, 9))
fig2.suptitle('Рентгеновское изображение (40 кэВ)', fontsize=16, fontweight='bold')

# Улучшенное изображение с медицинской цветовой гаммой
attenuation_clean2 = attenuation_grid.copy()
attenuation_max2 = np.nanpercentile(attenuation_clean2, 99.5)
attenuation_clean2 = np.clip(attenuation_clean2, 0, attenuation_max2)

# Применяем различную обработку для лучшего визуального восприятия
attenuation_processed = np.power(attenuation_clean2 / attenuation_max2, 0.45)

im_big = ax2.imshow(attenuation_processed.T, origin='lower', 
                    extent=[GRID_MIN, GRID_MAX, GRID_MIN, GRID_MAX],
                    cmap='gray_r', interpolation='bilinear')
ax2.set_xlabel('X, см', fontsize=12)
ax2.set_ylabel('Y, см', fontsize=12)
ax2.grid(False)

# Добавляем цветовую шкалу
cbar = plt.colorbar(im_big, ax=ax2, fraction=0.046, pad=0.04)
cbar.set_label('Относительное ослабление (µ·x)', fontsize=10)

# Добавляем информационную подпись
ax2.text(0.02, 0.02, f'Энергия: {INITIAL_ENERGY} кэВ\nФотонов на точку: {PHOTONS_PER_POSITION}', 
         transform=ax2.transAxes, fontsize=9, verticalalignment='bottom',
         bbox=dict(boxstyle='round', facecolor='black', alpha=0.6, color='white'))

plt.tight_layout()
plt.show()

# --- Вывод статистики ---
print("\n" + "="*50)
print("СТАТИСТИКА ОБРАБОТКИ")
print("="*50)
print(f"Всего обработано позиций: {len(stats)}")
print(f"Позиций без зарегистрированных фотонов: {(stats['hit_count'] == 0).sum()}")
print(f"Средний коэффициент пропускания: {stats['transmission'].mean():.4f}")
print(f"Медианный коэффициент пропускания: {stats['transmission'].median():.4f}")
print(f"Диапазон ослабления: [{np.nanmin(attenuation_grid):.2f}, {np.nanmax(attenuation_grid):.2f}]")

# Определяем, есть ли явные "тени" (области с высоким ослаблением)
high_attenuation = stats[stats['attenuation'] > 1.0]
if not high_attenuation.empty:
    print(f"\nОбласти с высоким ослаблением (>1.0): {len(high_attenuation)} позиций")
    print(high_attenuation[['PosX_cm', 'PosY_cm', 'transmission', 'attenuation']].head(10))
else:
    print("\nОбластей с высоким ослаблением не обнаружено")

# Сохраняем результаты в CSV (опционально)
stats.to_csv('processed_hits.csv', index=False)
print("\n✓ Результаты сохранены в 'processed_hits.csv'")

# Сохраняем изображение в файл (опционально)
plt.figure(fig2.number)
plt.savefig('xray_image.png', dpi=300, bbox_inches='tight', facecolor='black')
print("✓ Рентгеновское изображение сохранено в 'xray_image.png'")