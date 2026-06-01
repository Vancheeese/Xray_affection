#!/usr/bin/env python3
"""
Оценка разрешающей способности по MTF
Адаптировано под новые щели: 90, 110, 130 мкм
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
from scipy.fft import fft, fftfreq
import os

# ==================== ПАРАМЕТРЫ ====================
RESULTS_DIR = "./results"
PIXEL_SIZE_UM = 5  # 5 мкм/пиксель

THICKNESSES = [10, 25, 50, 75, 100, 150, 200, 300, 500]

# НОВЫЕ ЩЕЛИ (под разрешение ~90 мкм)
SLITS = {
    90: {'y_pos_mm': -0.250, 'real_width_um': 90, 'color': 'red'},
    110: {'y_pos_mm': 0.000, 'real_width_um': 110, 'color': 'green'},
    130: {'y_pos_mm': 0.250, 'real_width_um': 130, 'color': 'blue'},
}

def get_line_profile_around_slit(csv_file, y_pos_mm, x_range_mm=0.2, y_window_mm=0.4):
    """Получение профиля интенсивности вокруг щели"""
    df = pd.read_csv(csv_file, sep='\t')
    df_optical = df[df['Type'] == 'optical_photon']
    df_optical = df_optical[df_optical['Energy_eV'] < 10]
    
    if len(df_optical) == 0:
        return None, None
    
    x_range_cm = x_range_mm / 10
    y_pos_cm = y_pos_mm / 10
    y_window_cm = y_window_mm / 10
    
    df_center = df_optical[(df_optical['PosX_cm'] > -x_range_cm/2) & 
                            (df_optical['PosX_cm'] < x_range_cm/2)]
    
    df_slit = df_center[(df_center['PosY_cm'] > y_pos_cm - y_window_cm/2) &
                         (df_center['PosY_cm'] < y_pos_cm + y_window_cm/2)]
    
    if len(df_slit) == 0:
        return None, None
    
    y_bins = np.linspace(y_pos_cm - y_window_cm/2, y_pos_cm + y_window_cm/2, 500)
    y_hist, y_edges = np.histogram(df_slit['PosY_cm'], bins=y_bins)
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2
    
    if y_hist.max() > 0:
        y_hist = y_hist / y_hist.max()
    y_hist_smooth = gaussian_filter(y_hist, sigma=1.0)
    
    return y_centers, y_hist_smooth

def slit_to_mtf(profile, pixel_size_um):
    """Преобразование профиля щели в MTF"""
    lsf = profile / profile.max()
    n = len(lsf)
    mtf = np.abs(fft(lsf))
    mtf = mtf / mtf[0]
    freq = fftfreq(n, d=pixel_size_um/1000)
    freq = freq[:n//2]
    mtf = mtf[:n//2]
    return freq, mtf, lsf

def find_mtf50(freq, mtf):
    """Найти частоту, где MTF = 0.5"""
    for i in range(1, len(mtf)):
        if mtf[i] <= 0.5:
            if mtf[i-1] != mtf[i]:
                f50 = freq[i-1] + (0.5 - mtf[i-1]) * (freq[i] - freq[i-1]) / (mtf[i] - mtf[i-1])
            else:
                f50 = freq[i-1]
            return f50
    return freq[-1] if len(freq) > 0 else 0

def measure_fwhm(y_centers, profile):
    """Измерение FWHM профиля"""
    max_idx = np.argmax(profile)
    max_val = profile[max_idx]
    half_max = max_val / 2
    
    left = max_idx
    while left > 0 and profile[left] > half_max:
        left -= 1
    
    right = max_idx
    while right < len(profile) - 1 and profile[right] > half_max:
        right += 1
    
    fwhm = y_centers[right] - y_centers[left]
    fwhm_um = fwhm * 10000
    return fwhm_um

# ==================== ОСНОВНОЙ РАСЧЁТ ====================

print("="*70)
print("ОЦЕНКА РАЗРЕШАЮЩЕЙ СПОСОБНОСТИ ПО MTF (НОВЫЕ ЩЕЛИ 90-130 мкм)")
print("="*70)

all_results = []

for thickness in THICKNESSES:
    filepath = os.path.join(RESULTS_DIR, f"hits_data_{thickness}um.csv")
    
    if not os.path.exists(filepath):
        print(f"❌ Файл не найден: {thickness} мкм")
        continue
    
    print(f"\n📊 Толщина CsI: {thickness} мкм")
    print("-" * 50)
    
    for slit_width, params in SLITS.items():
        try:
            y_centers, profile = get_line_profile_around_slit(
                filepath, params['y_pos_mm'], x_range_mm=0.2, y_window_mm=0.4
            )
            
            if y_centers is None or len(profile) < 10:
                print(f"  Щель {slit_width} мкм: недостаточно данных")
                continue
            
            fwhm_um = measure_fwhm(y_centers, profile)
            freq, mtf, lsf = slit_to_mtf(profile, PIXEL_SIZE_UM)
            f50 = find_mtf50(freq, mtf)
            resolution_um = 1000 / (2 * f50) if f50 > 0 else 0
            
            all_results.append({
                'thickness_um': thickness,
                'slit_width_um': slit_width,
                'fwhm_um': fwhm_um,
                'mtf50_freq': f50,
                'resolution_um': resolution_um
            })
            
            status = "✅" if resolution_um < 100 else "⚠️"
            print(f"  Щель {slit_width} мкм: FWHM={fwhm_um:.0f} мкм, MTF50={f50:.2f} lp/mm, разрешение={resolution_um:.0f} мкм {status}")
            
        except Exception as e:
            print(f"  Щель {slit_width} мкм: ошибка - {e}")

# ==================== ВЫВОД ====================

print("\n" + "="*70)
print("СВОДНАЯ ТАБЛИЦА (по щели 110 мкм)")
print("="*70)

results_110 = [r for r in all_results if r['slit_width_um'] == 110]
if results_110:
    print("Толщина | FWHM (мкм) | MTF50 (lp/mm) | Разрешение (мкм)")
    print("-" * 55)
    for r in results_110:
        print(f"  {r['thickness_um']:3d} мкм  |    {r['fwhm_um']:3.0f}     |      {r['mtf50_freq']:4.2f}       |      {r['resolution_um']:4.0f}")
    
    best = min(results_110, key=lambda x: x['resolution_um'])
    print("\n" + "="*55)
    print(f"🎯 ОПТИМАЛЬНАЯ ТОЛЩИНА: {best['thickness_um']} мкм")
    print(f"   Разрешение: {best['resolution_um']:.0f} мкм")

# ==================== ГРАФИКИ ====================

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

if results_110:
    thicknesses = [r['thickness_um'] for r in results_110]
    resolutions = [r['resolution_um'] for r in results_110]
    fwhms = [r['fwhm_um'] for r in results_110]
    
    axes[0].plot(thicknesses, resolutions, 'o-', color='blue', linewidth=2, markersize=8)
    axes[0].set_xlabel('Толщина CsI (мкм)', fontsize=12)
    axes[0].set_ylabel('Разрешение (мкм)', fontsize=12)
    axes[0].set_title('Пространственное разрешение от толщины CsI', fontsize=12)
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xscale('log')
    axes[0].axhline(y=110, color='gray', linestyle='--', alpha=0.5, label='Реальная ширина щели')
    axes[0].legend()
    
    axes[1].plot(thicknesses, fwhms, 'o-', color='red', linewidth=2, markersize=8)
    axes[1].set_xlabel('Толщина CsI (мкм)', fontsize=12)
    axes[1].set_ylabel('FWHM (мкм)', fontsize=12)
    axes[1].set_title('FWHM щели 110 мкм', fontsize=12)
    axes[1].grid(True, alpha=0.3)
    axes[1].set_xscale('log')
    axes[1].axhline(y=110, color='gray', linestyle='--', alpha=0.5, label='Реальная ширина')
    axes[1].legend()

plt.tight_layout()
plt.savefig('mtf_results_new_slits.png', dpi=150)
plt.show()

print("\n✅ График сохранён: mtf_results_new_slits.png")