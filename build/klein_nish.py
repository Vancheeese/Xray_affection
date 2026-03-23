import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import warnings
warnings.filterwarnings('ignore')

# Константы
E_initial_keV = 100.0
E_e_rest_keV = 511.0
r_e_cm = 2.8179403262e-13  # классический радиус электрона в см

# Параметры эксперимента
thickness_um = 100.0
density_Al = 2.70
atomic_mass_Al = 26.98
avogadro = 6.02214076e23
electrons_per_atom_Al = 13

# Расчёт количества электронов
thickness_cm = thickness_um * 1e-4
atoms_per_cm3 = (density_Al / atomic_mass_Al) * avogadro
electrons_per_cm3 = atoms_per_cm3 * electrons_per_atom_Al
electrons_per_cm2 = electrons_per_cm3 * thickness_cm
N0 = 1e7  # количество падающих фотонов

print(f"Плотность электронов: {electrons_per_cm2:.2e} электронов/см²")
print(f"Ожидаемый масштаб: {N0 * electrons_per_cm2:.2e}")

def klein_nishina_dsigma_dOmega(theta_rad):
    """
    Дифференциальное сечение Клейна-Нишины в см²/ср
    """
    # Энергия рассеянного фотона
    E_scattered = E_initial_keV / (1 + (E_initial_keV / E_e_rest_keV) * (1 - np.cos(theta_rad)))
    ratio = E_scattered / E_initial_keV
    
    # Формула Клейна-Нишины
    dsigma_dOmega = (r_e_cm**2 / 2) * ratio**2 * (ratio + 1/ratio - np.sin(theta_rad)**2)
    
    return dsigma_dOmega

def read_and_bin_data(filename, num_bins=8, max_angle_deg=80):
    """Читает данные и возвращает статистику"""
    angles_deg = []
    energies_keV = []
    
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split()
            try:
                energy = float(parts[2])
                angle = float(parts[5])
                angles_deg.append(np.degrees(angle))
                energies_keV.append(energy)
            except (IndexError, ValueError):
                continue
    
    angles_deg = np.array(angles_deg)
    energies_keV = np.array(energies_keV)
    
    # Создаем бины
    bin_edges = np.linspace(0, max_angle_deg, num_bins + 1)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    bin_width = bin_edges[1] - bin_edges[0]
    
    # Подсчитываем количество частиц
    counts, _ = np.histogram(angles_deg, bins=bin_edges)
    total_events = len(angles_deg)
    
    # Телесный угол для кольцевого детектора
    bin_centers_rad = np.radians(bin_centers)
    delta_theta_rad = np.radians(bin_width)
    solid_angle = 2 * np.pi * np.sin(bin_centers_rad) * delta_theta_rad
    
    # Экспериментальное сечение: dσ/dΩ = N_exp / (N0 * n_e * ΔΩ)
    # где N_exp - количество событий в бине
    exp_cross_section = counts / (N0 * electrons_per_cm2 * solid_angle)
    exp_errors = np.sqrt(counts) / (N0 * electrons_per_cm2 * solid_angle)
    
    return {
        'bin_centers': bin_centers,
        'bin_centers_rad': bin_centers_rad,
        'bin_width': bin_width,
        'solid_angle': solid_angle,
        'counts': counts,
        'exp_cross_section': exp_cross_section,
        'exp_errors': exp_errors,
        'total_events': total_events,
        'angles_deg': angles_deg,
        'energies_keV': energies_keV
    }

def main():
    filename = "stuff1.csv"
    num_bins = 8
    max_angle_deg = 80
    
    print("Загрузка и обработка данных...")
    data = read_and_bin_data(filename, num_bins, max_angle_deg)
    
    # Теоретическое сечение
    theory = klein_nishina_dsigma_dOmega(data['bin_centers_rad'])
    
    # Подгонка масштабного коэффициента (должен быть близок к 1)
    def fit_function(theta_deg, scale):
        theta_rad = np.radians(theta_deg)
        return scale * klein_nishina_dsigma_dOmega(theta_rad)
    
    try:
        popt, pcov = curve_fit(fit_function, data['bin_centers'], 
                              data['exp_cross_section'], 
                              sigma=data['exp_errors'], 
                              p0=[1.0],
                              absolute_sigma=True)
        scale_factor = popt[0]
        scale_error = np.sqrt(pcov[0, 0]) if pcov is not None else 0
        
        theory_fitted = fit_function(data['bin_centers'], scale_factor)
        
        print(f"\nМасштабный коэффициент (должен быть ~1): {scale_factor:.4f} ± {scale_error:.4f}")
        print(f"Относительная погрешность: {(scale_error/scale_factor*100):.2f}%")
        
    except Exception as e:
        print(f"Ошибка подгонки: {e}, используем scale=1")
        scale_factor = 1.0
        scale_error = 0
        theory_fitted = theory
    
    # Вычисляем отношение и погрешности
    ratio = data['exp_cross_section'] / theory_fitted
    ratio_errors = ratio * np.sqrt((data['exp_errors']/data['exp_cross_section'])**2 + 
                                    (scale_error/scale_factor)**2)
    
    # Взвешенное среднее отношение (исключая выбросы)
    mask = ~np.isnan(ratio) & ~np.isinf(ratio) & (ratio_errors > 0)
    if np.sum(mask) > 1:
        weights = 1/ratio_errors[mask]**2
        mean_ratio = np.sum(ratio[mask] * weights) / np.sum(weights)
        mean_ratio_error = 1/np.sqrt(np.sum(weights))
    else:
        mean_ratio = np.nan
        mean_ratio_error = np.nan
    
    # Вывод статистики
    print("\n" + "="*100)
    print("ПОБИННЫЙ АНАЛИЗ")
    print("="*100)
    print(f"{'Бин':<6} {'Угол':<10} {'События':<12} {'dσ/dΩ (эксп)':<18} {'dσ/dΩ (теор)':<18} {'Отношение':<12}")
    print("-"*100)
    
    for i in range(num_bins):
        print(f"{i+1:<6} {data['bin_centers'][i]:>6.1f}°  "
              f"{data['counts'][i]:>10,}   "
              f"{data['exp_cross_section'][i]:.3e} ± {data['exp_errors'][i]:.3e}  "
              f"{theory_fitted[i]:.3e}    "
              f"{ratio[i]:>8.4f}")
    
    # Хи-квадрат
    chi2 = np.sum(((data['exp_cross_section'] - theory_fitted)/data['exp_errors'])**2)
    ndf = num_bins - 1
    
    print("\n" + "="*100)
    print(f"χ² = {chi2:.1f}, NDF = {ndf}, χ²/NDF = {chi2/ndf:.2f}")
    print(f"Среднее отношение эксп/теор (взвешенное): {mean_ratio:.4f} ± {mean_ratio_error:.4f}")
    
    # Создаем графики
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # График 1: Дифференциальное сечение
    ax1 = axes[0, 0]
    ax1.errorbar(data['bin_centers'], data['exp_cross_section'], 
                yerr=data['exp_errors'], fmt='o', capsize=5,
                label='Эксперимент', color='blue', markersize=8)
    
    theta_smooth = np.linspace(0, max_angle_deg, 200)
    theory_smooth = fit_function(theta_smooth, scale_factor)
    ax1.plot(theta_smooth, theory_smooth, 'r-', linewidth=2,
            label=f'Теория Клейна-Нишины (scale={scale_factor:.3f})')
    
    ax1.set_xlabel('Угол рассеяния (градусы)', fontsize=12)
    ax1.set_ylabel('dσ/dΩ (см²/ср)', fontsize=12)
    ax1.set_title('Дифференциальное сечение комптоновского рассеяния', fontsize=12)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # График 2: Отношение эксп/теор
    ax2 = axes[0, 1]
    ax2.errorbar(data['bin_centers'], ratio, yerr=ratio_errors,
                fmt='o', capsize=5, color='green', markersize=8)
    ax2.axhline(y=1.0, color='red', linestyle='--', linewidth=2, label='Идеальное совпадение')
    if not np.isnan(mean_ratio):
        ax2.axhline(y=mean_ratio, color='blue', linestyle=':', linewidth=2,
                   label=f'Среднее = {mean_ratio:.4f}')
    
    ax2.set_xlabel('Угол рассеяния (градусы)', fontsize=12)
    ax2.set_ylabel('Отношение Эксперимент / Теория', fontsize=12)
    ax2.set_title('Отношение эксперимента к теории', fontsize=12)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0, 2)
    
    # График 3: Статистическая погрешность
    ax3 = axes[1, 0]
    relative_errors = (data['exp_errors']/data['exp_cross_section']) * 100
    bars = ax3.bar(data['bin_centers'], relative_errors, 
                   width=data['bin_width']*0.8, alpha=0.7, 
                   color='orange', edgecolor='black')
    ax3.set_xlabel('Угол рассеяния (градусы)', fontsize=12)
    ax3.set_ylabel('Относительная погрешность (%)', fontsize=12)
    ax3.set_title('Статистическая погрешность эксперимента', fontsize=12)
    ax3.grid(True, alpha=0.3, axis='y')
    
    for i, (bar, err) in enumerate(zip(bars, relative_errors)):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{err:.1f}%', ha='center', va='bottom', fontsize=9)
    
    # График 4: Энергия vs угол
    ax4 = axes[1, 1]
    scatter = ax4.scatter(data['angles_deg'], data['energies_keV'], 
                         c=data['angles_deg'], cmap='viridis', 
                         s=5, alpha=0.5)
    
    theta_theory = np.linspace(0, max_angle_deg, 100)
    E_theory = E_initial_keV / (1 + (E_initial_keV / E_e_rest_keV) * 
                                 (1 - np.cos(np.radians(theta_theory))))
    ax4.plot(theta_theory, E_theory, 'r-', linewidth=2, label='Теория Комптона')
    
    ax4.set_xlabel('Угол рассеяния (градусы)', fontsize=12)
    ax4.set_ylabel('Энергия рассеянного фотона (кэВ)', fontsize=12)
    ax4.set_title('Энергетическое распределение', fontsize=12)
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=ax4, label='Угол (градусы)')
    
    plt.suptitle(f'Комптоновское рассеяние на алюминии (N_events = {data["total_events"]:,}, N0 = {N0:.0e})', 
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()