#!/usr/bin/env python3
"""
Генератор mac-файла для Geant4.
Считывает параметры из global_parameters.cc и создает one.mac
с правильным количеством событий.
"""

import re
import os

def read_global_parameters(cc_file='src/global_parameters.cc'):
    """Читает pixelSize и gridSize из global_parameters.cc"""
    params = {}
    
    # Путь к файлу относительно текущего скрипта
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cc_file = os.path.join(script_dir, '..', 'src', 'global_parameters.cc')
    
    if not os.path.exists(cc_file):
        print(f"Файл не найден: {cc_file}")
        return {'pixelSize': 10.0, 'gridSize': 100, 'particlesPerPixel': 1}
    
    with open(cc_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Ищем gridSize
    match = re.search(r'gridSize\s*=\s*(\d+)', content)
    params['gridSize'] = int(match.group(1)) if match else 100
    
    # Ищем particlesPerPixel
    match = re.search(r'particlesPerPixel\s*=\s*(\d+)', content)
    params['particlesPerPixel'] = int(match.group(1)) if match else 1
    
    return params

def generate_mac(params, output_file='one.mac'):
    """Генерирует mac-файл с правильным количеством событий"""
    
    grid_size = params['gridSize']
    particles_per_pixel = params['particlesPerPixel']
    
    # Общее количество событий = gridSize * gridSize * particlesPerPixel
    total_events = grid_size * grid_size * particles_per_pixel
    
    print(f"Параметры из global_parameters.cc:")
    print(f"  gridSize = {grid_size}")
    print(f"  particlesPerPixel = {particles_per_pixel}")
    print(f"  Общее количество событий: {total_events:,}")
    print(f"  (формула: {grid_size} × {grid_size} × {particles_per_pixel})")
    
    # Генерируем mac-файл
    mac_content = f"""/run/initialize

# Автоматически сгенерировано: gridSize={grid_size}, particlesPerPixel={particles_per_pixel}
# Общее количество событий = {grid_size}² × {particles_per_pixel} = {total_events:,}
/run/beamOn {total_events}
"""
    
    # Сохраняем в one.mac (в папке build, если скрипт там)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    mac_file = os.path.join(script_dir, output_file)
    
    with open(mac_file, 'w', encoding='utf-8') as f:
        f.write(mac_content)
    
    print(f"\n✓ Файл {mac_file} сгенерирован")
    return mac_file

if __name__ == '__main__':
    params = read_global_parameters()
    generate_mac(params)
