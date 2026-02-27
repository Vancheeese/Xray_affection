#!/usr/bin/env python
# this script requires Python3, numpy, scipy, matplotlib, and xraydb modules. Use:
#        pip install xraydb matplotlib
import numpy as np
import matplotlib.pyplot as plt
import xraydb
import re

# X-ray attenuation calculations
# inputs from web form
# Filename: xrayweb_atten.py
filename = 'stuff.csv'
formula = 'Cu'  # значение по умолчанию
thickness = 0.1  # значение по умолчанию
trans_exp = []  # массив для экспериментальных значений прошедшего излучения
energies_exp = []  # массив для энергий из файла

energy = np.arange(50000, 150000+10000, 10000)

try:
    with open(filename, 'r') as file:
        lines = file.readlines()
        
        # Обработка каждой строки
        for line in lines:
            line = line.strip()
            
            # Поиск строки с Material
            if line.startswith('Material:'):
                # Извлекаем часть после G4_
                match = re.search(r'G4_(\w+)', line)
                if match:
                    formula = match.group(1)
                    print(f"Найдена формула: {formula}")
            
            # Поиск строки с Thickness
            elif line.startswith('Thickness:'):
                # Извлекаем числовое значение толщины
                match = re.search(r'Thickness:\s*([\d.]+)', line)
                if match:
                    thickness = float(match.group(1))
                    print(f"Найдена толщина: {thickness} мм")
            
            # Поиск строк с Pass photons
            elif 'Pass photons:' in line:
                match_photons = re.search(r'Pass photons:\s*(\d+)', line)
                if match_photons:
                    trans_exp.append(int(match_photons.group(1)))
            
            # Поиск строк с Energy
            elif 'Energy:' in line:
                match_energy = re.search(r'Energy:\s*(\d+)\s*keV', line)
                if match_energy:
                    energies_exp.append(int(match_energy.group(1)) * 1000)  # переводим keV в eV
                
except FileNotFoundError:
    print(f"Файл {filename} не найден. Используются значения по умолчанию.")
except Exception as e:
    print(f"Ошибка при чтении файла: {e}")
    
    # Словарь с плотностями материалов
densities = {
    'Cu': 8.9600,
    'Al': 2.7000,
    # можно добавить другие материалы
    'Fe': 7.8700,
    'Pb': 11.3400,
}

density = densities.get(formula)

if density is not None:
    print(f"Плотность {formula}: {density} gr/cm³")
else:
    print(f"Материал {formula} не найден в базе данных")

mu_array = xraydb.material_mu(formula, energy, density=density)
atten_length = 10.0 / mu_array

trans = np.exp(-0.1*thickness*mu_array)
atten = 1 - trans

trans_exp = np.diff(trans_exp, prepend=0)

trans_exp=np.array(trans_exp)/100000

# plt.plot(energy, atten_length, label='1/e length (mm)')
# plt.xlabel('Energy (eV)')
# plt.ylabel('1/e length (mm)')
# plt.title('1/e length for %s' % formula)
# plt.show()


plt.plot(energy/1000, trans, label='Теорерическая')
plt.plot(np.array(energies_exp)/1000, trans_exp, label='Экспериментальная')
#plt.plot(energy, atten, label='attenuated')
plt.xlabel('Энергия (кэВ)')
plt.ylabel('Доля прошедшего излучения')
plt.title('Ослабление интенсивности излучения, %s, %.3f мм\n' %(formula, thickness))
plt.grid(True)
plt.minorticks_on()
plt.legend()
plt.tight_layout()
plt.show()

