import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
import gc
import os
from pathlib import Path

# ------------------- Параметры -------------------
scale = 100

GRID_MIN = -5.0 / scale
GRID_MAX = 5.0 / scale
NUM_BINS = 200
PHOTONS_PER_POSITION = 10
INITIAL_ENERGY = 30.0
SCINTILLATION_YIELD = 54000

# Папка с результатами
RESULTS_DIR = "./results"
OUTPUT_DIR = "./results/images"

# Создаём папку для изображений
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------- Чтение данных -------------------
def read_hits_file(filepath):
    """
    Чтение файла в формате:
    Energy_eV	PosX_cm	PosY_cm	Type	EventID
    """
    data = []
    
    if not os.path.exists(filepath):
        print(f"Файл не найден: {filepath}")
        return pd.DataFrame()
    
    # Проверка размера файла
    file_size = os.path.getsize(filepath)
    if file_size < 100:
        print(f"⚠️ Файл слишком маленький ({file_size} байт) — удаляем и пропускаем")
        try:
            os.remove(filepath)
        except:
            pass
        return pd.DataFrame()
    
    # Пробуем разные кодировки
    encodings = ['utf-8', 'latin-1', 'cp1251', 'iso-8859-1']
    lines = None
    used_encoding = None
    
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                content = f.read()
                # Проверяем, что это похоже на текстовый файл с табами
                if '\t' in content or ' ' in content:
                    lines = content.splitlines()
                    used_encoding = enc
                    break
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    # Если не удалось прочитать ни в одной кодировке, пробуем бинарный режим
    if lines is None:
        try:
            with open(filepath, 'rb') as f:
                raw = f.read()
                # Оставляем только печатаемые ASCII символы + табы + переводы строк
                clean_bytes = []
                for b in raw:
                    if (32 <= b <= 126) or b in (9, 10, 13):
                        clean_bytes.append(b)
                    else:
                        clean_bytes.append(32)  # заменяем на пробел
                clean_text = bytes(clean_bytes).decode('ascii')
                lines = clean_text.splitlines()
                print(f"✅ Файл прочитан в бинарном режиме, очищен от мусора")
        except Exception as e:
            print(f"❌ Ошибка чтения файла {filepath}: {e}")
            return pd.DataFrame()
    
    if lines is None or not lines:
        print(f"⚠️ Файл {filepath} пуст или нечитаем")
        return pd.DataFrame()
    
    # Определяем заголовок
    first_line = lines[0].strip()
    start_row = 0
    
    if 'Energy_eV' in first_line and 'PosX_cm' in first_line and 'PosY_cm' in first_line:
        start_row = 1
    
    # Обрабатываем строки
    for line_num, line in enumerate(lines[start_row:], start=start_row + 1):
        if not line.strip():
            continue
        
        # Очищаем от непечатаемых символов
        line = ''.join(c for c in line if c.isprintable() or c in '\t\n\r')
        
        parts = line.strip().split('\t')
        
        if len(parts) == 5:
            try:
                energy = float(parts[0])
                pos_x = float(parts[1])
                pos_y = float(parts[2])
                type_val = parts[3].lower().strip()
                event_id = int(parts[4])
                data.append([energy, pos_x, pos_y, type_val, event_id])
            except (ValueError, IndexError) as e:
                continue
        elif len(parts) >= 5:
            # Попытка восстановить данные, если разделитель - пробел
            try:
                parts2 = line.strip().split()
                if len(parts2) >= 5:
                    energy = float(parts2[0])
                    pos_x = float(parts2[1])
                    pos_y = float(parts2[2])
                    type_val = parts2[3].lower().strip()
                    event_id = int(parts2[4])
                    data.append([energy, pos_x, pos_y, type_val, event_id])
            except (ValueError, IndexError):
                continue
    
    if not data:
        print(f"⚠️ Не удалось распарсить данные из файла {filepath}")
        # Удаляем повреждённый файл
        try:
            os.remove(filepath)
            print(f"   Повреждённый файл удалён")
        except:
            pass
        return pd.DataFrame()
    
    df = pd.DataFrame(data, columns=['Energy_eV', 'PosX_cm', 'PosY_cm', 'Type', 'EventID'])
    print(f"✅ Прочитано {len(df):,} записей из {os.path.basename(filepath)}")
    return df


def process_thickness(filepath, thickness_um):
    """Обработка одной толщины и сохранение изображения"""
    
    print(f"\n{'='*60}")
    print(f"Обработка толщины: {thickness_um} мкм")
    print(f"{'='*60}")
    
    # Чтение файла
    df = read_hits_file(filepath)
    
    if len(df) == 0:
        print(f"❌ Нет данных для толщины {thickness_um} мкм")
        return None
    
    print(f"Загружено записей: {len(df):,}")
    
    # Фильтрация - только оптические фотоны
    df_optical = df[df['Type'] == 'optical_photon'].copy()
    print(f"Оптических фотонов: {len(df_optical):,}")
    
    if len(df_optical) == 0:
        print(f"❌ Нет оптических фотонов для толщины {thickness_um} мкм")
        return None
    
    # Фильтрация по энергии
    df_optical = df_optical[df_optical['Energy_eV'] < 10].copy()
    print(f"После фильтрации по энергии: {len(df_optical):,}")
    
    # Статистика событий
    if 'EventID' in df_optical.columns and len(df_optical) > 0:
        photons_per_event = df_optical.groupby('EventID').size()
        print(f"Событий: {len(photons_per_event):,}")
        print(f"Фотонов/событие: {photons_per_event.mean():.0f}")
    
    # Бинирование
    print(f"\nБинирование в сетку {NUM_BINS}x{NUM_BINS}...")
    print(f"Диапазон X: [{df_optical['PosX_cm'].min():.3f}, {df_optical['PosX_cm'].max():.3f}] см")
    print(f"Диапазон Y: [{df_optical['PosY_cm'].min():.3f}, {df_optical['PosY_cm'].max():.3f}] см")
    
    optical_counts, x_edges, y_edges = np.histogram2d(
        df_optical['PosX_cm'].values,
        df_optical['PosY_cm'].values,
        bins=NUM_BINS,
        range=[[GRID_MIN, GRID_MAX], [GRID_MIN, GRID_MAX]]
    )
    
    print(f"Ненулевых пикселей: {np.sum(optical_counts > 0):,}")
    print(f"Максимум фотонов: {int(np.max(optical_counts))}")
    
    if np.sum(optical_counts) == 0:
        print(f"❌ Нет данных для построения гистограммы")
        return None
    
    # Постобработка
    print("\nПостобработка...")
    
    # Нормализация интенсивности
    signal_intensity = optical_counts / PHOTONS_PER_POSITION
    signal_intensity[signal_intensity == 0] = 1e-6
    
    # Вычисляем ослабление
    attenuation = -np.log(signal_intensity)
    
    # Обрезаем экстремальные значения
    attenuation_finite = attenuation[~np.isnan(attenuation) & ~np.isinf(attenuation)]
    if len(attenuation_finite) > 0:
        vmin = np.percentile(attenuation_finite, 5)
        vmax = np.percentile(attenuation_finite, 95)
    else:
        vmin, vmax = 0, 1
    
    # Нормируем
    attenuation_norm = np.clip((attenuation - vmin) / (vmax - vmin), 0, 1)
    attenuation_gamma = np.power(attenuation_norm, 0.5)
    attenuation_smoothed = gaussian_filter(attenuation_gamma, sigma=1.0)
    
    extent = [GRID_MIN, GRID_MAX, GRID_MIN, GRID_MAX]
    
    # Сохраняем изображение
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    
    # 1. Сырые counts
    im1 = axes[0, 0].imshow(optical_counts.T, origin='lower', extent=extent,
                            cmap='hot', interpolation='nearest')
    axes[0, 0].set_title('Количество фотонов (сырые данные)')
    axes[0, 0].set_xlabel('X, см')
    axes[0, 0].set_ylabel('Y, см')
    plt.colorbar(im1, ax=axes[0, 0], label='Количество фотонов')
    
    # 2. Логарифм
    im2 = axes[0, 1].imshow(np.log10(optical_counts.T + 1), origin='lower', extent=extent,
                            cmap='viridis', interpolation='nearest')
    axes[0, 1].set_title('Логарифм количества фотонов')
    axes[0, 1].set_xlabel('X, см')
    axes[0, 1].set_ylabel('Y, см')
    plt.colorbar(im2, ax=axes[0, 1], label='log10(фотонов)')
    
    # 3. Ослабление
    im3 = axes[1, 0].imshow(attenuation_gamma.T, origin='lower', extent=extent,
                            cmap='gray_r', interpolation='bilinear', vmin=0, vmax=1)
    axes[1, 0].set_title('Рентгеновское изображение (ослабление)')
    axes[1, 0].set_xlabel('X, см')
    axes[1, 0].set_ylabel('Y, см')
    plt.colorbar(im3, ax=axes[1, 0], label='Относительное ослабление')
    
    # 4. Сглаженное
    im4 = axes[1, 1].imshow(attenuation_smoothed.T, origin='lower', extent=extent,
                            cmap='gray_r', interpolation='bilinear', vmin=0, vmax=1)
    axes[1, 1].set_title('Рентгеновское изображение (сглаженное)')
    axes[1, 1].set_xlabel('X, см')
    axes[1, 1].set_ylabel('Y, см')
    plt.colorbar(im4, ax=axes[1, 1], label='Относительное ослабление')
    
    plt.suptitle(f'CsI сцинтиллятор, толщина = {thickness_um} мкм, E={INITIAL_ENERGY} кэВ', fontsize=14)
    plt.tight_layout()
    
    # Сохраняем
    output_file = os.path.join(OUTPUT_DIR, f'xray_image_{thickness_um}um.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✅ Сохранено: {output_file}")
    
    # Сохраняем финальное изображение отдельно
    fig_final, ax_final = plt.subplots(1, 1, figsize=(12, 10))
    im_final = ax_final.imshow(attenuation_smoothed.T, origin='lower', extent=extent,
                               cmap='gray_r', interpolation='bilinear', vmin=0, vmax=1)
    ax_final.set_xlabel('X, см', fontsize=12)
    ax_final.set_ylabel('Y, см', fontsize=12)
    ax_final.set_title(f'CsI сцинтиллятор, толщина = {thickness_um} мкм, E={INITIAL_ENERGY} кэВ', fontsize=14)
    plt.colorbar(im_final, ax=ax_final, fraction=0.046, pad=0.04)
    plt.tight_layout()
    
    output_final = os.path.join(OUTPUT_DIR, f'xray_final_{thickness_um}um.png')
    plt.savefig(output_final, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✅ Сохранено: {output_final}")
    
    # Сохраняем данные
    data_file = os.path.join(OUTPUT_DIR, f'xray_data_{thickness_um}um.npz')
    np.savez(data_file,
             counts=optical_counts,
             attenuation=attenuation_smoothed,
             bins_x=x_edges,
             bins_y=y_edges)
    print(f"✅ Сохранены данные: {data_file}")
    
    return {
        'thickness_um': thickness_um,
        'total_photons': int(np.sum(optical_counts)),
        'max_photons': int(np.max(optical_counts)),
        'nonzero_pixels': int(np.sum(optical_counts > 0))
    }


# ==================== ОСНОВНАЯ ПРОГРАММА ====================

print("="*60)
print("ОБРАБОТКА РЕЗУЛЬТАТОВ СИМУЛЯЦИЙ")
print("="*60)

# Находим все файлы в папке results
results_files = []
for f in os.listdir(RESULTS_DIR):
    if f.startswith('hits_data_') and f.endswith('.csv'):
        # Извлекаем толщину из имени файла
        thickness_str = f.replace('hits_data_', '').replace('.csv', '').replace('um', '')
        try:
            thickness_um = int(thickness_str)
            results_files.append((thickness_um, os.path.join(RESULTS_DIR, f)))
        except ValueError:
            continue

# Сортируем по толщине
results_files.sort(key=lambda x: x[0])

print(f"\nНайдено файлов: {len(results_files)}")
print("Толщины:", [f[0] for f in results_files])

# Обрабатываем каждый файл с обработкой ошибок
all_stats = []
for thickness_um, filepath in results_files:
    try:
        stats = process_thickness(filepath, thickness_um)
        if stats:
            all_stats.append(stats)
    except Exception as e:
        print(f"❌ Ошибка обработки файла {filepath}: {e}")
        print(f"   Пропускаем толщину {thickness_um} мкм...")
        # Удаляем повреждённый файл
        try:
            os.remove(filepath)
            print(f"   Повреждённый файл удалён")
        except:
            pass
        continue
    gc.collect()

# ==================== СВОДНАЯ СТАТИСТИКА ====================

print("\n" + "="*60)
print("СВОДНАЯ СТАТИСТИКА ПО ВСЕМ ТОЛЩИНАМ")
print("="*60)

if all_stats:
    print("\nТолщина | Всего фотонов | Макс/пиксель | Ненулевых пикселей")
    print("-" * 60)
    for s in all_stats:
        print(f"  {s['thickness_um']:3d} мкм  |   {s['total_photons']:9,d}   |     {s['max_photons']:5,d}     |       {s['nonzero_pixels']:6,d}")
    
    # Сохраняем сводку
    summary_df = pd.DataFrame(all_stats)
    summary_df.to_csv(os.path.join(OUTPUT_DIR, 'summary.csv'), index=False)
    print(f"\n✅ Сводка сохранена: {os.path.join(OUTPUT_DIR, 'summary.csv')}")
    
    # График зависимости количества фотонов от толщины
    plt.figure(figsize=(10, 6))
    thicknesses = [s['thickness_um'] for s in all_stats]
    total_photons = [s['total_photons'] for s in all_stats]
    
    plt.plot(thicknesses, total_photons, 'o-', linewidth=2, markersize=8, color='blue')
    plt.xlabel('Толщина сцинтиллятора CsI (мкм)', fontsize=12)
    plt.ylabel('Общее количество зарегистрированных фотонов', fontsize=12)
    plt.title('Зависимость выхода фотонов от толщины CsI', fontsize=14)
    plt.grid(True, alpha=0.3)
    
    output_graph = os.path.join(OUTPUT_DIR, 'photons_vs_thickness.png')
    plt.savefig(output_graph, dpi=150)
    plt.close()
    print(f"✅ График сохранён: {output_graph}")