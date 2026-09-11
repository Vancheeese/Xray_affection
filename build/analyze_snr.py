#!/usr/bin/env python3
"""
Оценка SNR:
- Область фона (без золотых полос): высокий сигнал
- Область сигнала (с золотыми полосами): низкий сигнал
- Строит график маски с золотыми полосами
Оптимизировано для больших файлов.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
import os
import subprocess

from sim_params import read_params

# =============================================
# Параметры геометрии (читаются из src/global_parameters.cc)
# =============================================
params = read_params()
pixel_size = params.get('pixelSize', 3.5)   # мкм
grid_size = int(params.get('gridSize', 100))
lead_size = pixel_size * grid_size          # 350 мкм

slit_width = params.get('slitWidth', 16.0)  # мкм — ширина золотой полоски
slit_period = slit_width * 2  # период (полоска + зазор такой же ширины)
print(f"Параметры: pixelSize={pixel_size}, gridSize={grid_size}, slitWidth={slit_width}")

# =============================================
# Загрузка данных
# =============================================
csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hits_data.csv')
if len(sys.argv) > 1:
    csv_path = sys.argv[1]

print(f"Читаю файл: {csv_path}")

# Быстрая фильтрация через grep + awk
tmp_path = csv_path + '.tmp.npy'
awk_cmd = "grep -w 'opticalphoton' " + csv_path + " | awk -F'\\t' '{print $2, $3}' > " + tmp_path
print("Фильтрация через awk...")
subprocess.run(awk_cmd, shell=True, check=True)

x_coords, y_coords = np.loadtxt(tmp_path).T
print(f"Оптических фотонов: {len(x_coords)}")

os.remove(tmp_path)

# =============================================
# 2D гистограмма
# =============================================
x_min, x_max = -lead_size / 2, lead_size / 2
y_min, y_max = -lead_size / 2, lead_size / 2

nx, ny = int(lead_size), int(lead_size)  # 1 мкм/пиксель
H, xedges, yedges = np.histogram2d(
    x_coords, y_coords,
    bins=[nx, ny], range=[[x_min, x_max], [y_min, y_max]]
)

# =============================================
# Создаём маску золотых полос
# =============================================
x_centers = 0.5 * (xedges[:-1] + xedges[1:])
y_centers = 0.5 * (yedges[:-1] + yedges[1:])

# Позиции золотых полос
num_slits = int(lead_size / slit_period)
start_x = -num_slits * slit_period / 2.0 + slit_width / 2.0

# Маска: True = есть золото, False = нет золота
mask_gold = np.zeros((nx, ny), dtype=bool)
for i in range(num_slits):
    x_slit_center = start_x + i * slit_period
    x_idx = int(x_slit_center - x_min)
    half_w = int(slit_width / 2)
    # Золотая полоска: X в диапазоне [x_start, x_end], все Y
    x_start = max(0, x_idx - half_w)
    x_end = min(nx, x_idx + half_w)
    mask_gold[x_start:x_end, :] = True

# =============================================
# SNR: фон vs сигнал
# =============================================
# Фон = область БЕЗ золота (высокий сигнал)
# Сигнал = область С золотом (низкий сигнал)

background_pixels = H[~mask_gold]
signal_pixels = H[mask_gold]

bg_mean = background_pixels.mean()
bg_std = background_pixels.std()
sig_mean = signal_pixels.mean()
sig_std = signal_pixels.std()

# SNR = (фон - сигнал) / шум_фона
snr = (bg_mean - sig_mean) / bg_std if bg_std > 0 else 0

print(f"\n=== SNR Analysis ===")
print(f"Пикселей фона (без золота): {len(background_pixels)}")
print(f"Пикселей сигнала (с золотом): {len(signal_pixels)}")
print(f"\nФон (без золота):")
print(f"  mean = {bg_mean:.2f}")
print(f"  std  = {bg_std:.2f}")
print(f"\nСигнал (с золотом):")
print(f"  mean = {sig_mean:.2f}")
print(f"  std  = {sig_std:.2f}")
print(f"\nSNR = (bg_mean - sig_mean) / bg_std = {snr:.2f}")
print(f"\nSNR={snr:.4f}")

# =============================================
# Визуализация: маска золотых полос
# =============================================
output_dir = os.path.dirname(os.path.abspath(csv_path))

# Сохраняем результаты в файл для run_batch
results_path = os.path.join(output_dir, 'snr_results.txt')
with open(results_path, 'w') as f:
    f.write(f"Background mean = {bg_mean:.4f}\n")
    f.write(f"Signal mean = {sig_mean:.4f}\n")
    f.write(f"SNR = {snr:.4f}\n")
    f.write(f"SNR={snr:.4f}\n")
print(f"Результаты сохранены: {results_path}")

fig, axes = plt.subplots(2, 2, figsize=(14, 14))

# 1. Полное изображение
im0 = axes[0, 0].imshow(H.T, origin='lower', extent=[x_min, x_max, y_min, y_max],
                         aspect='equal', cmap='hot')
axes[0, 0].set_xlabel('X, мкм')
axes[0, 0].set_ylabel('Y, мкм')
axes[0, 0].set_title('Рентгеновское изображение')
plt.colorbar(im0, ax=axes[0, 0], label='Фотоны')

# 2. Маска (где золото — белые области)
im1 = axes[0, 1].imshow(mask_gold.T, origin='lower',
                         extent=[x_min, x_max, y_min, y_max],
                         aspect='equal', cmap='Reds')
axes[0, 1].set_xlabel('X, мкм')
axes[0, 1].set_ylabel('Y, мкм')
axes[0, 1].set_title('Маска золотых полос\n(белое = золото)')
plt.colorbar(im1, ax=axes[0, 1], label='Золото')

# 3. Фон (без золота)
im2 = axes[1, 0].imshow(H.T * (~mask_gold).T, origin='lower',
                         extent=[x_min, x_max, y_min, y_max],
                         aspect='equal', cmap='hot', vmin=0, vmax=bg_mean)
axes[1, 0].set_xlabel('X, мкм')
axes[1, 0].set_ylabel('Y, мкм')
axes[1, 0].set_title(f'Фон (без золота)\nmean={bg_mean:.1f}')
plt.colorbar(im2, ax=axes[1, 0], label='Фотоны')

# 4. Сигнал (с золотом)
im3 = axes[1, 1].imshow(H.T * mask_gold.T, origin='lower',
                         extent=[x_min, x_max, y_min, y_max],
                         aspect='equal', cmap='hot', vmin=0, vmax=sig_mean*2)
axes[1, 1].set_xlabel('X, мкм')
axes[1, 1].set_ylabel('Y, мкм')
axes[1, 1].set_title(f'Сигнал (с золотом)\nmean={sig_mean:.1f}')
plt.colorbar(im3, ax=axes[1, 1], label='Фотоны')

plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'snr_mask.png'), dpi=150)
plt.close()
print(f"\nГрафик сохранён: snr_mask.png")

print("Готово.")
