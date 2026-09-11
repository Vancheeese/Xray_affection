#!/usr/bin/env python3
"""Построение 2D рентгеновского изображения из hits_data.csv.
Оптимизировано: использует awk для быстрой фильтрации."""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
import os
import subprocess

from sim_params import read_params

# --- Параметры геометрии (читаются из src/global_parameters.cc) ---
params = read_params()
pixel_size = params.get('pixelSize', 3.5)   # мкм
grid_size = int(params.get('gridSize', 100))
lead_size = pixel_size * grid_size          # 350 мкм

# --- Загрузка данных ---
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

if len(x_coords) == 0:
    print("ERROR: Нет оптических фотонов в данных")
    sys.exit(1)

# --- Создаём 2D гистограмму ---
x_min, x_max = -lead_size / 2, lead_size / 2
y_min, y_max = -lead_size / 2, lead_size / 2

# Разрешение: 1 мкм на пиксель
nx, ny = int(lead_size), int(lead_size)
H, xedges, yedges = np.histogram2d(
    x_coords, y_coords,
    bins=[nx, ny], range=[[x_min, x_max], [y_min, y_max]]
)

print(f"Размер изображения: {nx} x {ny} пикселей")
print(f"Диапазон X: [{x_min:.1f}, {x_max:.1f}] мкм")
print(f"Диапазон Y: [{y_min:.1f}, {y_max:.1f}] мкм")
print(f"Всего фотонов на изображении: {H.sum()}")
print(f"Среднее: {H.mean():.1f}, макс: {H.max()}, мин: {H.min()}")

# --- Сохранение ---
output_dir = os.path.dirname(os.path.abspath(csv_path))

# PNG
img_path = os.path.join(output_dir, 'xray_image.png')
fig, ax = plt.subplots(1, 1, figsize=(8, 8))
im = ax.imshow(H.T, origin='lower', extent=[x_min, x_max, y_min, y_max],
               aspect='equal', cmap='hot')
ax.set_xlabel('X, мкм')
ax.set_ylabel('Y, мкм')
ax.set_title('Рентгеновское изображение (оптические фотоны)')
plt.colorbar(im, label='Количество фотонов')
plt.tight_layout()
plt.savefig(img_path, dpi=150)
plt.close()
print(f"Изображение сохранено: {img_path}")

# NPZ
npz_path = os.path.join(output_dir, 'xray_image.npz')
np.savez(npz_path, data=H, xedges=xedges, yedges=yedges)
print(f"Данные сохранены: {npz_path}")

print("Готово.")
