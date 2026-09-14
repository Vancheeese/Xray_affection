#!/usr/bin/env python3
"""
Зависимости характеристик детектора от толщины сцинтиллятора.

Собирает по папкам results/<толщина>um/ результаты пакетного прогона:
  - FWHM краевого перехода из edge_profile_results.txt
  - SNR из snr_results.txt
и строит общий график resolution_vs_thickness.png.

Скрипт ничего не моделирует и не анализирует — только читает готовые
результаты analyze_edge.py и analyze_snr.py.

Запуск: python3 plot_dependencies.py [папка_results]
Без аргумента используется папка results рядом с этим скриптом.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import re
import sys

# =============================================
# Папка с результатами
# =============================================
script_dir = os.path.dirname(os.path.abspath(__file__))
results_dir = os.path.abspath(
    sys.argv[1] if len(sys.argv) > 1 else os.path.join(script_dir, 'results')
)

print(f"Читаю результаты из: {results_dir}")

if not os.path.isdir(results_dir):
    print(f"Ошибка: папка {results_dir} не найдена")
    sys.exit(1)

# =============================================
# Чтение значения из вида "FWHM=4.4358" / "SNR = 0.8942"
# =============================================
def read_value(path, key):
    """Возвращает последнее число из строк '<key> = <число>', либо None.

    Берётся последнее вхождение, так как в файле результат дублируется:
    человекочитаемой строкой с единицами и машиночитаемой строкой без них.
    Строка 'FWHM=nan' (неудачный фиттинг) не матчится и даёт None.
    """
    if not os.path.isfile(path):
        return None
    pattern = re.compile(key + r'\s*=\s*([0-9.eE+-]+)')
    value = None
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                try:
                    value = float(match.group(1))
                except ValueError:
                    pass
    return value


# =============================================
# Сбор данных по папкам <толщина>um
# =============================================
thickness_pattern = re.compile(r'^(\d+(?:\.\d+)?)\s*um$')

records = []
for name in sorted(os.listdir(results_dir)):
    folder = os.path.join(results_dir, name)
    if not os.path.isdir(folder):
        continue

    match = thickness_pattern.match(name)
    if not match:
        continue
    thickness = float(match.group(1))

    fwhm = read_value(os.path.join(folder, 'edge_profile_results.txt'), 'FWHM')
    snr = read_value(os.path.join(folder, 'snr_results.txt'), 'SNR')

    if fwhm is None and snr is None:
        print(f"  {name}: результатов анализа нет, пропускаю")
        continue

    if fwhm is None:
        print(f"  {name}: нет FWHM (нужен analyze_edge.py)")
    if snr is None:
        print(f"  {name}: нет SNR (нужен analyze_snr.py)")

    records.append((thickness, fwhm, snr))

# Сортировка по возрастанию толщины
records.sort(key=lambda r: r[0])

if not records:
    print("\nНет ни одного результата — строить нечего.")
    print("Сначала выполните анализ: bash run_batch_analysis.sh")
    sys.exit(1)

# =============================================
# Сводная таблица
# =============================================
print(f"\nСводка по {len(records)} толщинам:")
print(f"{'Толщина, мкм':>14} | {'FWHM, мкм':>10} | {'SNR':>8}")
print("-" * 40)
for thickness, fwhm, snr in records:
    fwhm_str = f"{fwhm:.4f}" if fwhm is not None else "нет"
    snr_str = f"{snr:.4f}" if snr is not None else "нет"
    print(f"{thickness:>14.1f} | {fwhm_str:>10} | {snr_str:>8}")

thicknesses = [r[0] for r in records]

# =============================================
# Визуализация
# =============================================
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# --- 1. Пространственное разрешение (FWHM края) ---
ax = axes[0]
x = [r[0] for r in records if r[1] is not None]
y = [r[1] for r in records if r[1] is not None]
if x:
    ax.plot(x, y, 'o-', color='tab:blue', linewidth=2, markersize=8)
    for xi, yi in zip(x, y):
        ax.annotate(f"{yi:.2f}", (xi, yi), textcoords='offset points',
                    xytext=(0, 9), ha='center', fontsize=9)
    ax.set_xticks(x)
    ax.margins(y=0.15)
else:
    ax.text(0.5, 0.5, 'нет данных', ha='center', va='center',
            transform=ax.transAxes)
ax.set_xlabel('Толщина сцинтиллятора, мкм')
ax.set_ylabel('FWHM краевого перехода, мкм')
ax.set_title('Пространственное разрешение от толщины')
ax.grid(True, alpha=0.3)

# --- 2. SNR ---
ax = axes[1]
x = [r[0] for r in records if r[2] is not None]
y = [r[2] for r in records if r[2] is not None]
if x:
    ax.plot(x, y, 's-', color='tab:red', linewidth=2, markersize=8)
    for xi, yi in zip(x, y):
        ax.annotate(f"{yi:.2f}", (xi, yi), textcoords='offset points',
                    xytext=(0, 9), ha='center', fontsize=9)
    ax.set_xticks(x)
    ax.margins(y=0.15)
else:
    ax.text(0.5, 0.5, 'нет данных', ha='center', va='center',
            transform=ax.transAxes)
ax.set_xlabel('Толщина сцинтиллятора, мкм')
ax.set_ylabel('SNR')
ax.set_title('Отношение сигнал/шум от толщины')
ax.grid(True, alpha=0.3)

plt.tight_layout()

out_path = os.path.join(script_dir, 'resolution_vs_thickness.png')
plt.savefig(out_path, dpi=150)
plt.close()
print(f"\nГрафик сохранён: {out_path}")

print("Готово.")
