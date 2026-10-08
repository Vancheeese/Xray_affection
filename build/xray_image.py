#!/usr/bin/env python3
"""Построение 2D рентгеновского изображения из hits_data.csv.

Учитывает объектив: координаты из hits_data.csv лежат в плоскости изображения
(после линзы). Делим их на M — получаем координаты в плоскости объекта
(Au-сетки). Размер бина = pixelSize (объектный пиксель) → изображение 1:1
с исходной сеткой gridSize x gridSize.
"""

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
pixel_size = params.get('pixelSize', 3.5)            # мкм, объектный пиксель
grid_size  = int(params.get('gridSize', 100))
M          = params.get('lensMagnification', 2.7)    # увеличение объектива

lead_size = pixel_size * grid_size                   # 350 мкм, FOV в плоскости объекта

print(f"Параметры:")
print(f"  pixelSize          = {pixel_size} мкм")
print(f"  gridSize           = {grid_size}")
print(f"  lensMagnification  = {M}")
print(f"  FOV объекта        = {lead_size} x {lead_size} мкм")
print(f"  FOV изображения    = {lead_size*M:.1f} x {lead_size*M:.1f} мкм")
print(f"  Эффективный пиксель = {pixel_size:.3f} мкм (объектный)")

# --- Загрузка данных ---
csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hits_data.csv')
if len(sys.argv) > 1:
    csv_path = sys.argv[1]

print(f"\nЧитаю файл: {csv_path}")

# Быстрая фильтрация через grep + awk
tmp_path = csv_path + '.tmp.txt'
awk_cmd = "grep -w 'opticalphoton' " + csv_path + " | awk -F'\\t' '{print $2, $3}' > " + tmp_path
print("Фильтрация через awk...")
subprocess.run(awk_cmd, shell=True, check=True)

if os.path.getsize(tmp_path) == 0:
    print("ERROR: Нет оптических фотонов в данных")
    os.remove(tmp_path)
    sys.exit(1)

x_img, y_img = np.loadtxt(tmp_path).T
os.remove(tmp_path)
print(f"Оптических фотонов (в плоскости изображения): {len(x_img)}")

# --- Пересчёт из плоскости изображения в плоскость объекта ---
# Формула: x_object = x_image / M, обратное инверсирование
x_obj = -x_img / M
y_obj = -y_img / M

print(f"Диапазон X (объект): [{x_obj.min():.1f}, {x_obj.max():.1f}] мкм")
print(f"Диапазон Y (объект): [{y_obj.min():.1f}, {y_obj.max():.1f}] мкм")

# --- Создаём 2D гистограмму в координатах объекта ---
# Размер бина = pixelSize (объектный пиксель) → 1 пиксель изображения = 1 пиксель сетки
bin_size = pixel_size / M
nx = int(round(lead_size / bin_size))
ny = int(round(lead_size / bin_size))

x_min, x_max = -lead_size / 2.0, lead_size / 2.0
y_min, y_max = -lead_size / 2.0, lead_size / 2.0

H, xedges, yedges = np.histogram2d(
    x_obj, y_obj,
    bins=[nx, ny], range=[[x_min, x_max], [y_min, y_max]]
)

print(f"\nРазмер изображения: {nx} x {ny} пикселей")
print(f"Размер бина (объект): {bin_size:.3f} мкм")
print(f"Диапазон X: [{x_min:.1f}, {x_max:.1f}] мкм")
print(f"Диапазон Y: [{y_min:.1f}, {y_max:.1f}] мкм")
print(f"Всего фотонов в гистограмме: {int(H.sum())}")
print(f"Среднее: {H.mean():.2f}, макс: {int(H.max())}, мин: {int(H.min())}")

# --- Сохранение ---
output_dir = os.path.dirname(os.path.abspath(csv_path))

# PNG
img_path = os.path.join(output_dir, 'xray_image.png')
fig, ax = plt.subplots(1, 1, figsize=(8, 8))
im = ax.imshow(H.T, origin='lower', extent=[x_min, x_max, y_min, y_max],
               aspect='equal', cmap='hot', interpolation='nearest')
ax.set_xlabel('X, мкм (плоскость объекта)')
ax.set_ylabel('Y, мкм (плоскость объекта)')
ax.set_title(f'Рентгеновское изображение (M = {M})\n'
             f'FOV = {lead_size:.0f} x {lead_size:.0f} мкм, '
             f'{nx}x{ny} пикселей по {bin_size:.2f} мкм')
plt.colorbar(im, label='Количество фотонов')
plt.tight_layout()
plt.savefig(img_path, dpi=150)
plt.close()
print(f"Изображение сохранено: {img_path}")

# NPZ
npz_path = os.path.join(output_dir, 'xray_image.npz')
np.savez(npz_path, data=H, xedges=xedges, yedges=yedges,
         M=M, pixel_size=pixel_size, grid_size=grid_size)
print(f"Данные сохранены: {npz_path}")

print("Готово.")