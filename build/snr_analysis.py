#!/usr/bin/env python3
"""
Оценка соотношения сигнал/шум (SNR) по фоновым пикселям (без объекта).
Запускать из папки build: python3 snr_analysis.py
"""

import numpy as np
import matplotlib.pyplot as plt
import re
import os

# ==================== Чтение параметров из global_parameters.cc ====================
def read_global_parameters():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cc_file = os.path.join(script_dir, '..', 'src', 'global_parameters.cc')
    
    params = {'pixelSize': 10.0, 'gridSize': 100, 'slitWidth': 50.0, 'particlesPerPixel': 1}
    
    if not os.path.exists(cc_file):
        print(f"⚠ Файл не найден: {cc_file}. Используются значения по умолчанию.")
        return params
    
    with open(cc_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    match = re.search(r'pixelSize\s*=\s*([\d.]+)', content)
    if match: params['pixelSize'] = float(match.group(1))
    
    match = re.search(r'gridSize\s*=\s*(\d+)', content)
    if match: params['gridSize'] = int(match.group(1))
    
    match = re.search(r'slitWidth\s*=\s*([\d.]+)', content)
    if match: params['slitWidth'] = float(match.group(1))
    
    match = re.search(r'particlesPerPixel\s*=\s*(\d+)', content)
    if match: params['particlesPerPixel'] = int(match.group(1))
    
    return params

# ==================== Основная логика ====================
def main():
    print("="*55)
    print("АНАЛИЗ СОТНОШЕНИЯ СИГНАЛ/ШУМ (SNR)")
    print("="*55)
    
    params = read_global_parameters()
    pixel_size = params['pixelSize']
    grid_size = params['gridSize']
    slit_width = params['slitWidth']
    particles_per_pixel = params['particlesPerPixel']
    
    lead_size = pixel_size * grid_size
    slit_period = slit_width * 2
    num_slits = int(lead_size / slit_period)
    total_width = num_slits * slit_period
    start_x = -total_width / 2.0 + slit_width / 2.0
    
    print(f"\nПараметры геометрии:")
    print(f"  pixelSize = {pixel_size} мкм, gridSize = {grid_size}")
    print(f"  slitWidth = {slit_width} мкм, slitPeriod = {slit_period} мкм")
    print(f"  Полосок: {num_slits}, Области: {lead_size} мкм")
    print(f"  particlesPerPixel = {particles_per_pixel}")
    
    # Загрузка данных
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(script_dir, 'xray_counts_data.npz')
    
    if not os.path.exists(data_file):
        print(f"\n❌ Файл {data_file} не найден. Сначала запустите build_xray_image.py")
        return
    
    data = np.load(data_file)
    counts = data['counts']
    x_edges = data['x_edges']
    y_edges = data['y_edges']
    
    print(f"\nЗагружено данных: {counts.shape[0]}x{counts.shape[1]} пикселей")
    
    # Вычисление центров пикселей
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2
    
    # Определение маски: True = полоска, False = зазор (фон)
    is_strip = ((x_centers - start_x) % slit_period) < slit_width
    mask_2d = np.tile(is_strip[np.newaxis, :], (grid_size, 1))
    
    # Извлечение фоновых пикселей (без объекта)
    bg_counts = counts[~mask_2d].flatten()
    n_bg_pixels = len(bg_counts)
    n_strip_pixels = np.sum(mask_2d)
    
    print(f"\nСтатистика пикселей:")
    print(f"  Фоновые (без полосок): {n_bg_pixels}")
    print(f"  С объектом (под полосками): {n_strip_pixels}")
    
    # Расчет SNR
    mean_bg = np.mean(bg_counts)
    std_bg = np.std(bg_counts)
    snr = mean_bg / std_bg if std_bg > 0 else float('inf')
    
    print(f"\n{'='*55}")
    print("РЕЗУЛЬТАТЫ SNR (ФОНОВЫЕ ПИКСЕЛИ):")
    print(f"  Среднее количество фотонов/пиксель: {mean_bg:.2f}")
    print(f"  Стандартное отклонение (шум):      {std_bg:.2f}")
    print(f"  SNR (μ/σ):                          {snr:.2f}")
    print(f"  Фотонов на 1 первичную частицу:     {mean_bg/particles_per_pixel:.2f}")
    print(f"{'='*55}")
    
    # Теоретическая оценка
    poisson_snr = np.sqrt(mean_bg) if mean_bg > 0 else 0
    print(f"\nТеоретический SNR (Пуассон, √N): {poisson_snr:.2f}")
    if snr > 0 and poisson_snr > 0:
        ratio = snr / poisson_snr
        if ratio < 0.9:
            print("⚠️  SNR ниже пуассоновского предела → добавлены шумы (оптическое растекание, неидеальность поверхности)")
        elif ratio > 1.1:
            print("✅ SNR близок или выше пуассоновского → хорошее качество детектирования")
    
    print(f"\n📈 Зависимость SNR от particlesPerPixel:")
    print(f"   Теоретически SNR ~ √(particlesPerPixel)")
    print(f"   При {particles_per_pixel} частицах/пиксель: ожидаемый рост SNR в √{particles_per_pixel} ≈ {np.sqrt(particles_per_pixel):.2f} раза")
    
    # Визуализация распределения (сохраняем, не показываем)
    plt.figure(figsize=(8, 5))
    plt.hist(bg_counts, bins=50, color='steelblue', edgecolor='black', alpha=0.7)
    plt.axvline(mean_bg, color='red', linestyle='--', label=f'Среднее: {mean_bg:.1f}')
    plt.axvline(mean_bg - std_bg, color='orange', linestyle=':', label=f'μ-σ: {mean_bg-std_bg:.1f}')
    plt.axvline(mean_bg + std_bg, color='orange', linestyle=':', label=f'μ+σ: {mean_bg+std_bg:.1f}')
    plt.xlabel('Количество оптических фотонов в пикселе', fontsize=12)
    plt.ylabel('Частота', fontsize=12)
    plt.title(f'Распределение фотонов в фоновых пикселях\nSNR = {snr:.2f}, N_пикселей = {n_bg_pixels}', fontsize=14)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(script_dir, 'snr_histogram.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\n✅ Гистограмма сохранена: snr_histogram.png")

    # Сохранение текстовых результатов в файл
    results_file = os.path.join(script_dir, 'snr_results.txt')
    with open(results_file, 'w', encoding='utf-8') as f:
        f.write("="*55 + "\n")
        f.write("РЕЗУЛЬТАТЫ SNR (ФОНОВЫЕ ПИКСЕЛИ):\n")
        f.write("="*55 + "\n")
        f.write(f"Среднее количество фотонов/пиксель: {mean_bg:.2f}\n")
        f.write(f"Стандартное отклонение (шум):      {std_bg:.2f}\n")
        f.write(f"SNR (μ/σ):                          {snr:.2f}\n")
        f.write(f"Фотонов на 1 первичную частицу:     {mean_bg/particles_per_pixel:.2f}\n")
        f.write("="*55 + "\n")
        f.write(f"Теоретический SNR (Пуассон, √N): {poisson_snr:.2f}\n")
        if snr > 0 and poisson_snr > 0:
            ratio = snr / poisson_snr
            if ratio < 0.9:
                f.write("⚠️  SNR ниже пуассоновского предела → добавлены шумы (оптическое растекание, неидеальность поверхности)\n")
            elif ratio > 1.1:
                f.write("✅ SNR близок или выше пуассоновского → хорошее качество детектирования\n")
        f.write(f"\n📈 Зависимость SNR от particlesPerPixel:\n")
        f.write(f"   Теоретически SNR ~ √(particlesPerPixel)\n")
        f.write(f"   При {particles_per_pixel} частицах/пиксель: ожидаемый рост SNR в √{particles_per_pixel} ≈ {np.sqrt(particles_per_pixel):.2f} раза\n")
    
    print(f"✅ Текстовые результаты сохранены: snr_results.txt")

if __name__ == '__main__':
    main()