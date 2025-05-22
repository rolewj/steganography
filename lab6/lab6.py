import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()]
)

logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.getLogger('PIL').setLevel(logging.WARNING)

import os
logging.debug(f"Current working directory: {os.getcwd()}")
logging.debug(f"Directory listing: {os.listdir()}")


import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import csv
import re

import logging

def process_csv(csv_file: str, tag):
    try:
        df = pd.read_csv(csv_file, sep=';', dtype={'filename': str})
        
        required_columns = {'filename', 'Xi-square', 'RS-analyse', 'AUMP'}
        if not required_columns.issubset(df.columns):
            missing = required_columns - set(df.columns)
            raise ValueError(f"Отсутствуют обязательные столбцы: {missing}")
        
        if df['filename'].isnull().any():
            raise ValueError("Обнаружены пустые значения в столбце 'filename'")
        
        empty_mask = ~df['filename'].str.contains('_stego', na=False)
        empty_df = df[empty_mask]
        filled_df = df[~empty_mask]
        
        methods = ['Xi-square', 'RS-analyse', 'AUMP']
        fp_rates = []
        fn_rates = []
        
        for method in methods:
            fp = empty_df[empty_df[method] == 1].shape[0]
            fp_rate = fp / len(empty_df) if len(empty_df) > 0 else 0
            fp_rates.append(fp_rate)
            
            fn = filled_df[filled_df[method] == 0].shape[0]
            fn_rate = fn / len(filled_df) if len(filled_df) > 0 else 0
            fn_rates.append(fn_rate)
        
        x = range(len(methods))
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(12, 7))
        fig.canvas.manager.set_window_title(f'График №{tag}')
        bars1 = ax.bar(x, fp_rates, width, label='Ошибка I рода', color='tomato', alpha = 0.8)
        bars2 = ax.bar([i + width for i in x], fn_rates, width, label='Ошибка II рода', color='teal', alpha = 0.8)
        
        ax.set_ylabel('Доля ошибок', fontsize=12)
        ax.set_title('Сравнение ошибок детектирования по методам', fontsize=14)
        ax.set_xticks([i + width/2 for i in x])
        ax.set_xticklabels(methods)
        ax.legend()
        ax.grid(axis='y', linestyle='--', alpha=0.8)
        
        for bars in (bars1, bars2):
            for bar in bars:
                height = bar.get_height()
                ax.annotate(f'{height:.1%}',
                            xy=(bar.get_x() + bar.get_width()/2, height),
                            xytext=(0, 3),
                            textcoords="offset points",
                            ha='center', va='bottom')
        
        plt.ylim(0, 1)
        plt.tight_layout()
        plt.show()

    except Exception as e:
        print(f"Ошибка обработки: {str(e)}")
        print("Требуемые параметры CSV:")
        print("- Столбец 'filename' с маркировкой '_stego' для заполненных контейнеров")
        print("- Числовые столбцы методов (0=не обнаружено, 1=обнаружено)")

def parse_file(file_path):
    logging.debug(f"Начало парсинга файла: {file_path}")
    with open(file_path, encoding='utf-8') as f:
        text = f.read()
    logging.debug(f"Первые 200 символов {file_path}:\n{text[:200]!r}")
    results = []
    text = open(file_path, encoding='utf-8').read().strip()
    blocks = re.split(r"\r?\n\s*\r?\n+", text)
    logging.debug(f"Разбил текст на {len(blocks)} блоков")
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 4 or not lines[0].startswith("Файл:"):
            continue
        path = lines[0].split(":", 1)[1].strip().replace("\\", "/")
        chi   = float(lines[1].split(":", 1)[1].strip())
        aump  = float(lines[2].split(":", 1)[1].strip())
        rs    = float(lines[3].split(":", 1)[1].strip())
        filename = os.path.basename(path)
        results.append((filename, chi, rs, aump))
    logging.debug(f"parse_file возвращает {len(results)} записей")
    return results


def compare_with_thresholds(chi_square, rs_analysis, aump, chi_threshold, rs_threshold, aump_threshold):
    chi_square_check = 1 if chi_square >= chi_threshold else 0
    rs_analysis_check = 1 if rs_analysis >= rs_threshold else 0
    aump_check = 1 if aump >= aump_threshold else 0
    return chi_square_check, rs_analysis_check, aump_check

def read_files(file_paths):
    not_processed_results = []
    for file_path in file_paths:
        logging.debug(f"Пытаюсь открыть файл: {file_path}")
        if not os.path.exists(file_path):
            logging.warning(f"Файл не найден: {file_path}")
            continue

        try:
            entries = parse_file(file_path)
            logging.debug(f"В файле {file_path} найдено блоков: {len(entries)}")
            for filename, chi, rs, aump in entries:
                not_processed_results.append([filename, chi, rs, aump])
        except Exception as e:
            logging.error(f"Ошибка парсинга {file_path}: {e}")
    logging.debug(f"Всего записей после чтения: {len(not_processed_results)}")
    return not_processed_results


def perocess_results(chi_threshold, rs_threshold, aump_threshold, not_processed_results):
    processed_results = []
    for _, (image_filename, chi_square, rs_analysis, aump) in enumerate(not_processed_results):
        chi_check, rs_check, aump_check = compare_with_thresholds(chi_square, rs_analysis, aump, chi_threshold, rs_threshold, aump_threshold)
        processed_results.append([image_filename, chi_check, rs_check, aump_check])
    return processed_results

def write_to_csv(output_csv, processed_results):
    header = ['filename', 'Xi-square', 'RS-analyse', 'AUMP']
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(header)
        for _, (image_filename, chi_square, rs_analysis, aump) in enumerate(processed_results):
            writer.writerow([image_filename, chi_square, rs_analysis, aump])

if __name__ == "__main__":
    file_paths = [
        'clean_images.txt',
        'stego_lab3_4.txt'
    ]

    not_processed_results = read_files(file_paths)
    print("parsed rows:", not_processed_results)

    methods = ['Xi-square', 'RS-analyse', 'AUMP']

    def calculate_fp_fn(processed_results):
        df = pd.DataFrame(processed_results, columns=['filename', 'Xi-square', 'RS-analyse', 'AUMP'])
        empty_mask = ~df['filename'].str.contains('_stego', na=False)
        filled_mask = df['filename'].str.contains('_stego', na=False)

        fp_rates = {}
        fn_rates = {}

        for method in methods:
            fp = df.loc[empty_mask, method].sum()
            fp_rate = fp / empty_mask.sum() if empty_mask.sum() > 0 else 0
            fn = (df.loc[filled_mask, method] == 0).sum()
            fn_rate = fn / filled_mask.sum() if filled_mask.sum() > 0 else 0

            fp_rates[method] = fp_rate
            fn_rates[method] = fn_rate

        return fp_rates, fn_rates

    chi_threshold = 4000
    rs_threshold = 0.01
    aump_threshold = 1.25

    processed_results = perocess_results(chi_threshold, rs_threshold, aump_threshold, not_processed_results)
    write_to_csv('analysis_results.csv', processed_results)
    process_csv('analysis_results.csv', 'Best')