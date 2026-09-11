#!/usr/bin/env python3
"""
Одномерный профиль I(x), нахождение краёв, аппроксимация erf,
вычисление FWHM краевого перехода.
Оптимизировано для больших файлов.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.special import erf
from scipy.optimize import curve_fit
from scipy.signal import find_peaks
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

# Быстрая фильтрация через awk
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
# 1D профиль I(x) — усреднение по Y
# =============================================
I_x = H.mean(axis=1)  # усреднение по Y
x_centers = 0.5 * (xedges[:-1] + xedges[1:])

print(f"\nПрофиль: {len(x_centers)} точек по X")
print(f"Диапазон X: [{x_centers.min():.1f}, {x_centers.max():.1f}] мкм")
print(f"I(x): min={I_x.min():.1f}, max={I_x.max():.1f}, mean={I_x.mean():.1f}")

# Поиск краёв
dI = np.gradient(I_x)
win = 5
dI_smooth = np.convolve(dI, np.ones(win)/win, mode='same')

# Краевые артефакты: на границах гистограммы (x = ±175 мкм) производная
# заведомо больше реальных переходов полос, поэтому ищем экстремумы
# только во внутренней области, исключая отступ margin пикселей.
margin = 2 * win
dI_inner = dI_smooth[margin:-margin]

# Порог считаем от глубины реальных СПАДОВ внутри области, а не от
# np.max(np.abs(...)), который завышается краевыми артефактами.
threshold = 0.3 * abs(np.min(dI_inner))
neg_peaks, _ = find_peaks(-dI_inner, height=threshold,
                          distance=int(slit_period/2), prominence=0.3)
neg_peaks.sort()
neg_peaks += margin  # возврат к глобальной нумерации точек профиля

print(f"\nНайдено краёв: {len(neg_peaks)}")
for i, idx in enumerate(neg_peaks):
    print(f"  Край {i+1}: x = {x_centers[idx]:.1f} мкм, dI/dx = {dI_smooth[idx]:.2f}")

if len(neg_peaks) == 0:
    print("\nКрая не найдены!")
    sys.exit(1)

best_edge_idx = neg_peaks[0]
x0_guess = x_centers[best_edge_idx]

# =============================================
# Функция erf для ПАДАЮЩЕГО края (фон → минимум)
# =============================================
def erf_edge(x, A, B, x0, sigma):
    # A — уровень минимума (под золотом)
    # B — амплитуда (фон - минимум), положительная
    # x0 — позиция края, sigma — ширина
    return A + B * 0.5 * (1.0 - erf((x - x0) / (np.sqrt(2) * sigma)))

# =============================================
# Область фиттинга
# =============================================
fit_width = slit_period / 2  # половина периода — захватываем один край
x_fit = x_centers[(x_centers > x0_guess - fit_width) &
                  (x_centers < x0_guess + fit_width)]
I_fit = I_x[(x_centers > x0_guess - fit_width) &
            (x_centers < x0_guess + fit_width)]

print(f"\nАппроксимация края:")
print(f"  Позиция: x0 = {x0_guess:.1f} мкм")
print(f"  Область фиттинга: [{x_fit.min():.1f}, {x_fit.max():.1f}] мкм")
print(f"  Точек для фиттинга: {len(x_fit)}")

# Начальные параметры (ПРАВИЛЬНЫЕ!)
A0 = I_fit.min()
B0 = I_fit.max() - I_fit.min()
sigma0 = 5.0
p0 = [A0, B0, x0_guess, sigma0]
popt = None  # по умолчанию

try:
    popt, pcov = curve_fit(erf_edge, x_fit, I_fit, p0=p0, maxfev=10000)
    A_fit, B_fit, x0_fit, sigma_fit = popt
    
    # FWHM краевого перехода
    fwhm = 2.0 * np.sqrt(2.0 * np.log(2.0)) * sigma_fit
    
    # Ошибки параметров
    perr = np.sqrt(np.diag(pcov))
    
    print(f"\n  Результат фиттинга:")
    print(f"    A (фон)   = {A_fit:.2f} ± {perr[0]:.2f}")
    print(f"    B         = {B_fit:.2f} ± {perr[1]:.2f}")
    print(f"    x0 (край) = {x0_fit:.2f} ± {perr[2]:.2f} мкм")
    print(f"    sigma     = {sigma_fit:.3f} ± {perr[3]:.3f} мкм")
    print(f"    FWHM      = {fwhm:.2f} мкм")
    
except RuntimeError as e:
    print(f"\nФиттинг не удался: {e}")
    fwhm = np.nan
    sigma_fit = np.nan
    x0_fit = np.nan

# =============================================
# Визуализация
# =============================================
output_dir = os.path.dirname(os.path.abspath(csv_path))

# Сохраняем результаты в файл для run_batch
results_path = os.path.join(output_dir, 'edge_profile_results.txt')
with open(results_path, 'w') as f:
    f.write(f"Edge position x0 = {x0_fit:.4f} мкм\n")
    f.write(f"Sigma = {sigma_fit:.4f} мкм\n")
    f.write(f"FWHM = {fwhm:.4f} мкм\n")
    f.write(f"FWHM={fwhm:.4f}\n")
print(f"Результаты сохранены: {results_path}")

fig, axes = plt.subplots(2, 1, figsize=(10, 10))

# 2D изображение
im0 = axes[0].imshow(H.T, origin='lower', extent=[x_min, x_max, y_min, y_max],
                     aspect='equal', cmap='hot')
axes[0].set_xlabel('X, мкм')
axes[0].set_ylabel('Y, мкм')
axes[0].set_title('2D рентгеновское изображение')
plt.colorbar(im0, ax=axes[0], label='Фотоны')

# 1D профиль + фиттинг
axes[1].plot(x_centers, I_x, 'k-', linewidth=0.8, alpha=0.5, label='I(x)')
if popt is not None:
    x_smooth = np.linspace(x_fit.min(), x_fit.max(), 300)
    axes[1].plot(x_smooth, erf_edge(x_smooth, *popt), 'r-', linewidth=2,
                 label=f'erf: x0={x0_fit:.1f}, FWHM={fwhm:.2f} мкм')
else:
    axes[1].plot([], [], 'r-', linewidth=2, label='фиттинг не удался')
axes[1].axvline(x0_guess, color='b', linestyle='--', alpha=0.5, label=f'Край ~{x0_guess:.0f} мкм')
axes[1].set_xlabel('X, мкм')
axes[1].set_ylabel('Интенсивность')
axes[1].set_title('1D профиль I(x) + аппроксимация края')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'edge_profile.png'), dpi=150)
plt.close()
print(f"\nГрафик сохранён: edge_profile.png")

print("Готово.")
