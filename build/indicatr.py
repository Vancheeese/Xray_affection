import numpy as np
import matplotlib.pyplot as plt
import re

# ============================================
# ПАРАМЕТРЫ ЭКСПЕРИМЕНТА
# ============================================
E0 = 100.0  # начальная энергия фотонов в кэВ
m_e = 511.0  # энергия покоя электрона в кэВ
r_e2 = (2.818e-13)**2  # квадрат классического радиуса электрона в см^2

# Параметры мишени (алюминий, 50 мкм)
thickness_cm = 100e-4  # 50 мкм в см
density = 2.7  # г/см^3
A = 26.98  # г/моль
Z = 13
N_A = 6.022e23  # число Авогадро

# Число падающих частиц
N0 = 1e7

# Расчет числа рассеивающих центров на см^2
n_atoms_per_cm3 = (density * N_A) / A
n_atoms_per_cm2 = n_atoms_per_cm3 * thickness_cm
n_electrons_per_cm2 = n_atoms_per_cm2 * Z

print(f"Число рассеивающих центров n = {n_electrons_per_cm2:.2e} электронов/см²")
print(f"Толщина мишени: 50 мкм")
print(f"Число падающих частиц N0 = {N0:.0e}")

# ============================================
# ЗАГРУЗКА ДАННЫХ ИЗ ФАЙЛА
# ============================================
def load_data(filename):
    """Загрузка данных из текстового файла"""
    energies = []
    angles_rad = []
    
    with open(filename, 'r') as f:
        for line in f:
            # Поиск чисел в строке
            numbers = re.findall(r"[-+]?\d*\.\d+|\d+", line)
            if len(numbers) >= 2:
                energy = float(numbers[0])
                angle_rad = float(numbers[1])
                energies.append(energy)
                angles_rad.append(angle_rad)
    
    return np.array(energies), np.array(angles_rad)

# Загрузка данных
try:
    energies, angles_rad = load_data('stuff1.csv')
    angles_deg = np.degrees(angles_rad)
    print(f"Загружено событий: {len(energies)}")
except FileNotFoundError:
    print("Файл stuff1.csv не найден!")
    exit()

# Диагностика углов
print("\n" + "="*70)
print("ДИАГНОСТИКА УГЛОВ:")
print("="*70)
print(f"Всего событий в файле: {len(angles_deg)}")
print(f"Мин угол: {np.min(angles_deg):.2f}° ({np.min(angles_rad):.3f} рад)")
print(f"Макс угол: {np.max(angles_deg):.2f}° ({np.max(angles_rad):.3f} рад)")
print(f"Средний угол: {np.mean(angles_deg):.2f}°")
print(f"Медианный угол: {np.median(angles_deg):.2f}°")

# ============================================
# БИННИНГ ПО УГЛАМ (8 бинов от 0 до 80 градусов)
# ============================================
n_bins = 8
bin_edges_deg = np.linspace(0, 80, n_bins + 1)
bin_edges_rad = np.radians(bin_edges_deg)
bin_centers_deg = (bin_edges_deg[:-1] + bin_edges_deg[1:]) / 2
bin_centers_rad = np.radians(bin_centers_deg)
bin_widths_deg = np.diff(bin_edges_deg)

# Подсчет событий в бинах
counts, _ = np.histogram(angles_deg, bins=bin_edges_deg)

# Сколько событий попадает в наши бины (0-80°)
in_range = np.sum((angles_deg >= 0) & (angles_deg <= 80))
out_range = np.sum(angles_deg > 80)
print(f"\nСобытий в диапазоне 0-80°: {in_range} ({100*in_range/len(angles_deg):.1f}%)")
print(f"Событий за пределами 80°: {out_range} ({100*out_range/len(angles_deg):.1f}%)")

# ============================================
# ТЕЛЕСНЫЕ УГЛЫ БИНОВ
# ============================================
cos_theta1 = np.cos(bin_edges_rad[:-1])
cos_theta2 = np.cos(bin_edges_rad[1:])
solid_angles = 2 * np.pi * (cos_theta1 - cos_theta2)

# ============================================
# ЭКСПЕРИМЕНТАЛЬНОЕ ДИФФЕРЕНЦИАЛЬНОЕ СЕЧЕНИЕ
# ============================================
dN_dOmega = counts / solid_angles
dsigma_dOmega_exp = dN_dOmega / (N0 * n_electrons_per_cm2)

# Погрешности (статистические)
dsigma_err = dsigma_dOmega_exp / np.sqrt(counts)
dsigma_err[counts == 0] = 0

# ============================================
# ТЕОРЕТИЧЕСКАЯ ФОРМУЛА КЛЕЙНА-НИШИНЫ
# ============================================
def klein_nishina(theta_rad, E0, m_e, r_e2):
    """
    Дифференциальное сечение Клейна-Нишины
    """
    cos_theta = np.cos(theta_rad)
    epsilon = E0 / m_e
    E_ratio = 1.0 / (1.0 + epsilon * (1.0 - cos_theta))
    
    return (r_e2 / 2.0) * E_ratio**2 * (E_ratio + 1.0/E_ratio - np.sin(theta_rad)**2)

# Расчет теории для центров бинов
dsigma_dOmega_theor = klein_nishina(bin_centers_rad, E0, m_e, r_e2)

# Для гладкой кривой
theta_smooth_deg = np.linspace(0, 80, 200)
theta_smooth_rad = np.radians(theta_smooth_deg)
dsigma_smooth = klein_nishina(theta_smooth_rad, E0, m_e, r_e2)

# ============================================
# АНАЛИЗ ОТНОШЕНИЙ
# ============================================
ratio_per_bin = dsigma_dOmega_exp / dsigma_dOmega_theor
mean_ratio = np.mean(ratio_per_bin)
std_ratio = np.std(ratio_per_bin)

print("\n" + "="*70)
print(f"ОТНОШЕНИЕ ЭКСП/ТЕОР ПО БИНАМ ({n_bins} бинов, 0-80°):")
print("="*70)
for i in range(n_bins):
    print(f"Бин {i+1} ({bin_edges_deg[i]:.0f}-{bin_edges_deg[i+1]:.0f}°): {ratio_per_bin[i]:.3f}")
print(f"\nСреднее отношение: {mean_ratio:.3f} ± {std_ratio:.3f}")
print(f"Относительный разброс: {std_ratio/mean_ratio*100:.1f}%")

# ============================================
# ПОСТРОЕНИЕ ГРАФИКОВ (4 графика)
# ============================================
plt.figure(figsize=(14, 10))

# График 1: Сравнение эксперимента с теорией
plt.subplot(2, 2, 1)
plt.errorbar(bin_centers_deg, dsigma_dOmega_exp, yerr=dsigma_err, 
             fmt='o', color='red', capsize=3, markersize=8, label='Эксперимент')
plt.plot(theta_smooth_deg, dsigma_smooth, 'b-', linewidth=2, label='Теория')
plt.plot(theta_smooth_deg, dsigma_smooth * mean_ratio, 'g--', linewidth=2, 
         label=f'Теория × {mean_ratio:.3f}')
plt.xlabel('Угол θ (градусы)')
plt.ylabel('dσ/dΩ (см²/ср)')
plt.title(f'Сравнение с теорией ({n_bins} бинов, 0-80°)')
plt.grid(True, alpha=0.3)
plt.legend()
plt.xlim(0, 80)

# График 2: Отношение эксп/теор по бинам
plt.subplot(2, 2, 2)
plt.bar(bin_centers_deg, ratio_per_bin, width=bin_widths_deg[0]*0.8, 
        alpha=0.7, edgecolor='black', color='skyblue')
plt.axhline(y=1.0, color='b', linestyle='-', linewidth=2, label='Теория')
plt.axhline(y=mean_ratio, color='r', linestyle='--', linewidth=2, 
            label=f'Среднее = {mean_ratio:.3f}')
plt.fill_between([0, 80], mean_ratio - std_ratio, mean_ratio + std_ratio, 
                 alpha=0.2, color='red', label=f'±1σ = ±{std_ratio:.3f}')
plt.xlabel('Угол θ (градусы)')
plt.ylabel('Отношение эксп/теор')
plt.title('Отношение эксперимента к теории')
plt.grid(True, alpha=0.3)
plt.legend()
plt.xlim(0, 80)
plt.ylim(0, 2.5)

# График 3: Гистограмма углов
plt.subplot(2, 2, 3)
plt.hist(angles_deg, bins=50, alpha=0.7, edgecolor='black', color='green')
plt.axvline(80, color='red', linestyle='--', linewidth=2, label='Граница 80°')
for i, edge in enumerate(bin_edges_deg):
    plt.axvline(edge, color='gray', linestyle=':', alpha=0.5)
plt.xlabel('Угол (градусы)')
plt.ylabel('Событий')
plt.title('Распределение углов')
plt.grid(True, alpha=0.3)
plt.legend()

# График 4: Энергия vs угол
plt.subplot(2, 2, 4)
# Берем случайные 5000 точек для наглядности
indices = np.random.choice(len(energies), min(5000, len(energies)), replace=False)
plt.scatter(angles_deg[indices], energies[indices], s=1, alpha=0.5, c='blue')
plt.xlabel('Угол (градусы)')
plt.ylabel('Энергия (кэВ)')
plt.title('Энергия рассеянных фотонов')
plt.grid(True, alpha=0.3)
plt.xlim(0, 85)
plt.ylim(85, 101)

plt.tight_layout()
plt.savefig('klein_nishina_analysis_8bins_80deg.png', dpi=150)
print("\nГрафик сохранен в файл 'klein_nishina_analysis_8bins_80deg.png'")

# ============================================
# ВЫВОД ТАБЛИЦЫ РЕЗУЛЬТАТОВ
# ============================================
print("\n" + "="*90)
print(f"РЕЗУЛЬТАТЫ ПО БИНАМ ({n_bins} бинов, 0-80°):")
print("="*90)
print(f"{'Бин':<5} {'Углы,°':<12} {'N_событий':<12} {'dσ/dΩ_эксп':<18} {'dσ/dΩ_теор':<18} {'Эксп/Теор':<12} {'Погр.%':<8}")
print("-"*90)

for i in range(n_bins):
    rel_err = dsigma_err[i]/dsigma_dOmega_exp[i]*100 if counts[i] > 0 else 0
    print(f"{i+1:<5} {bin_edges_deg[i]:.0f}-{bin_edges_deg[i+1]:.0f}      "
          f"{counts[i]:<12} {dsigma_dOmega_exp[i]:.4e}   {dsigma_dOmega_theor[i]:.4e}   "
          f"{ratio_per_bin[i]:.3f}      {rel_err:.1f}%")

# ============================================
# РАСЧЕТ ХИ-КВАДРАТ
# ============================================
chi2 = 0
ndf = 0
for i in range(n_bins):
    if counts[i] > 0 and dsigma_err[i] > 0:
        chi2 += ((dsigma_dOmega_exp[i] - dsigma_dOmega_theor[i]) / dsigma_err[i])**2
        ndf += 1

chi2_calib = 0
for i in range(n_bins):
    if counts[i] > 0 and dsigma_err[i] > 0:
        chi2_calib += ((dsigma_dOmega_exp[i] - mean_ratio * dsigma_dOmega_theor[i]) / dsigma_err[i])**2

print("\n" + "="*70)
print(f"χ² = {chi2:.2f}, число степеней свободы = {ndf}")
print(f"χ²/ndf = {chi2/ndf:.2f}")
print(f"Калиброванный χ²/ndf = {chi2_calib/ndf:.2f}")

# ============================================
# ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ
# ============================================
print("\n" + "="*70)
print("КАЛИБРОВКА:")
print("="*70)
print(f"Среднее отношение эксп/теор = {mean_ratio:.3f} ± {std_ratio:.3f}")
print(f"Относительный разброс = {std_ratio/mean_ratio*100:.1f}%")
print(f"Рекомендуемый калибровочный множитель: {mean_ratio:.3f}")

# Сравнение с 7 бинами до 70°
bins7_mean = 1.650
bins7_std = 0.128
print(f"\nСравнение с 7 бинами (0-70°):")
print(f"7 бинов (0-70°): среднее = {bins7_mean:.3f} ± {bins7_std:.3f}")
print(f"8 бинов (0-80°): среднее = {mean_ratio:.3f} ± {std_ratio:.3f}")
print(f"Разница: {abs(mean_ratio - bins7_mean):.3f} ({abs(mean_ratio - bins7_mean)/bins7_mean*100:.1f}%)")

plt.show()