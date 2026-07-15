#!/usr/bin/env python3
"""
SNR analysis for direct X-ray detection (without scintillator).
Analyzes registered gamma/e-/e+ particles on Si detector.

Run from build folder:
    python3 snr_direct.py
"""

import numpy as np
import matplotlib.pyplot as plt
import re
import os

# ==================== Read global parameters ====================
def read_global_parameters():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cc_file = os.path.join(script_dir, '..', 'src', 'global_parameters.cc')
    
    params = {
        'pixelSize': 10.0,
        'gridSize': 100,
        'slitWidth': 50.0,
        'particlesPerPixel': 1
    }
    
    if not os.path.exists(cc_file):
        print(f"WARNING: {cc_file} not found. Using defaults.")
        return params
    
    with open(cc_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    match = re.search(r'pixelSize\s*=\s*([\d.]+)', content)
    if match:
        params['pixelSize'] = float(match.group(1))
    
    match = re.search(r'gridSize\s*=\s*(\d+)', content)
    if match:
        params['gridSize'] = int(match.group(1))
    
    match = re.search(r'slitWidth\s*=\s*([\d.]+)', content)
    if match:
        params['slitWidth'] = float(match.group(1))
    
    match = re.search(r'particlesPerPixel\s*=\s*(\d+)', content)
    if match:
        params['particlesPerPixel'] = int(match.group(1))
    
    return params


# ==================== Main analysis ====================
def main():
    print("=" * 55)
    print("SNR ANALYSIS (DIRECT X-RAY DETECTION)")
    print("=" * 55)
    
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
    
    print(f"\nGeometry parameters:")
    print(f"  pixelSize = {pixel_size} um")
    print(f"  gridSize = {grid_size}")
    print(f"  slitWidth = {slit_width} um")
    print(f"  slitPeriod = {slit_period} um")
    print(f"  Number of strips: {num_slits}")
    print(f"  particlesPerPixel = {particles_per_pixel}")
    
    # Load data
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(script_dir, 'xray_direct_data.npz')
    
    if not os.path.exists(data_file):
        print(f"\nERROR: {data_file} not found.")
        print("First run: python3 build_xray_direct.py")
        return
    
    data = np.load(data_file)
    counts = data['counts']
    geometry = data['geometry']
    x_edges = data['x_edges']
    y_edges = data['y_edges']
    mean_bg_counts = data['mean_bg_counts']
    
    print(f"\nLoaded data: {counts.shape[0]}x{counts.shape[1]} pixels")
    
    # Background mask (no gold)
    bg_mask = geometry == 0
    gold_mask = geometry == 1
    
    n_bg_pixels = int(np.sum(bg_mask))
    n_gold_pixels = int(np.sum(gold_mask))
    
    print(f"\nPixel statistics:")
    print(f"  Background (no gold): {n_bg_pixels:,}")
    print(f"  Under gold strips: {n_gold_pixels:,}")
    
    # Extract counts
    bg_counts = counts[bg_mask].flatten()
    gold_counts = counts[gold_mask].flatten()
    
    # SNR calculation (background pixels)
    mean_bg = np.mean(bg_counts)
    std_bg = np.std(bg_counts)
    snr = mean_bg / std_bg if std_bg > 0 else float('inf')
    
    # Gold statistics
    mean_gold = np.mean(gold_counts)
    std_gold = np.std(gold_counts)
    
    # Contrast
    contrast = 1 - (mean_gold / mean_bg) if mean_bg > 0 else 0
    
    # CNR (Contrast-to-Noise Ratio)
    cnr = abs(mean_bg - mean_gold) / np.sqrt(std_bg**2 + std_gold**2) if (std_bg**2 + std_gold**2) > 0 else 0
    
    print(f"\n{'=' * 55}")
    print("SNR RESULTS (BACKGROUND PIXELS):")
    print(f"{'=' * 55}")
    print(f"  Mean particles/pixel (bg):     {mean_bg:.2f}")
    print(f"  Std dev (noise, bg):           {std_bg:.2f}")
    print(f"  SNR (mean/std):                {snr:.2f}")
    print(f"  Particles per primary:         {mean_bg / particles_per_pixel:.2f}")
    print(f"\nGOLD STRIPS STATISTICS:")
    print(f"  Mean particles/pixel (gold):   {mean_gold:.2f}")
    print(f"  Std dev (noise, gold):         {std_gold:.2f}")
    print(f"\nCONTRAST:")
    print(f"  Contrast (1 - I_gold/I_bg):    {contrast * 100:.1f}%")
    print(f"  I_gold / I_bg ratio:           {mean_gold / mean_bg:.3f}")
    print(f"  CNR (Contrast-to-Noise):       {cnr:.2f}")
    print(f"{'=' * 55}")
    
    # Theoretical Poisson SNR
    poisson_snr = np.sqrt(mean_bg) if mean_bg > 0 else 0
    print(f"\nTheoretical SNR (Poisson, sqrt(N)): {poisson_snr:.2f}")
    
    if snr > 0 and poisson_snr > 0:
        ratio = snr / poisson_snr
        if ratio < 0.9:
            print("WARNING: SNR below Poisson limit -> extra noise present")
        elif ratio > 1.1:
            print("OK: SNR close to or above Poisson -> good detection quality")
        else:
            print("OK: SNR matches Poisson statistics")
    
    # Visualization
    plt.figure(figsize=(10, 6))
    
    # Histogram of background counts
    plt.hist(bg_counts, bins=50, color='steelblue', edgecolor='black', alpha=0.7, label='Background')
    plt.hist(gold_counts, bins=50, color='gold', edgecolor='black', alpha=0.7, label='Under gold')
    
    plt.axvline(mean_bg, color='blue', linestyle='--', linewidth=2, label=f'Bg mean: {mean_bg:.1f}')
    plt.axvline(mean_bg - std_bg, color='blue', linestyle=':', linewidth=1, label=f'Bg +/- sigma')
    plt.axvline(mean_bg + std_bg, color='blue', linestyle=':', linewidth=1)
    
    plt.axvline(mean_gold, color='orange', linestyle='--', linewidth=2, label=f'Gold mean: {mean_gold:.1f}')
    
    plt.xlabel('Number of particles per pixel', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.title(f'Direct X-ray Detection\nSNR = {snr:.2f}, Contrast = {contrast*100:.1f}%, CNR = {cnr:.2f}', fontsize=14)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(script_dir, 'snr_direct_histogram.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\n[OK] Histogram saved: snr_direct_histogram.png")
    
    # Save text results
    results_file = os.path.join(script_dir, 'snr_direct_results.txt')
    with open(results_file, 'w', encoding='utf-8') as f:
        f.write("=" * 55 + "\n")
        f.write("SNR RESULTS (DIRECT X-RAY DETECTION)\n")
        f.write("=" * 55 + "\n")
        f.write(f"Mean particles/pixel (bg):     {mean_bg:.2f}\n")
        f.write(f"Std dev (noise, bg):           {std_bg:.2f}\n")
        f.write(f"SNR (mean/std):                {snr:.2f}\n")
        f.write(f"Particles per primary:         {mean_bg / particles_per_pixel:.2f}\n")
        f.write(f"\n")
        f.write(f"Mean particles/pixel (gold):   {mean_gold:.2f}\n")
        f.write(f"Std dev (noise, gold):         {std_gold:.2f}\n")
        f.write(f"\n")
        f.write(f"Contrast (1 - I_gold/I_bg):    {contrast * 100:.1f}%\n")
        f.write(f"I_gold / I_bg ratio:           {mean_gold / mean_bg:.3f}\n")
        f.write(f"CNR (Contrast-to-Noise):       {cnr:.2f}\n")
        f.write(f"\n")
        f.write(f"Theoretical SNR (Poisson):     {poisson_snr:.2f}\n")
        if snr > 0 and poisson_snr > 0:
            ratio = snr / poisson_snr
            f.write(f"SNR/Poisson ratio:             {ratio:.2f}\n")
            if ratio < 0.9:
                f.write("Status: SNR below Poisson limit -> extra noise\n")
            elif ratio > 1.1:
                f.write("Status: SNR above Poisson -> good quality\n")
            else:
                f.write("Status: SNR matches Poisson statistics\n")
        f.write(f"{'=' * 55}\n")
    
    print(f"[OK] Results saved: snr_direct_results.txt")


if __name__ == '__main__':
    main()
