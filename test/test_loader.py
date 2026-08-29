import pytest
import os
from pathlib import Path
from unittest.mock import patch
import sys

# Добавляем путь к модулю в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from internet_game_finder_fixed.app import load_library, load_csv, LIBRARY_FILE, LIB_FILE


def test_missing_csv_file(tmp_path):
    # Создаём временный путь для теста
    non_existent_file = tmp_path / "nonexistent.csv"
    
    # Заменяем LIBRARY_FILE на несуществующий файл
    with patch('internet_game_finder_fixed.app.LIBRARY_FILE', non_existent_file):
        result = load_library()
        assert result == []


def test_empty_csv_file(tmp_path):
    # Создаём пустой CSV-файл
    empty_file = tmp_path / "empty.csv"
    empty_file.write_text("", encoding="utf-8")
    
    with patch('internet_game_finder_fixed.app.LIBRARY_FILE', empty_file):
        result = load_library()
        assert result == []


def test_csv_with_header_only(tmp_path):
    # Создаём CSV с только заголовком
    header_only_file = tmp_path / "header_only.csv"
    header_only_file.write_text("name,platform,coop_players,has_pvp,year,genre,free2play,url
", encoding="utf-8")
    
    with patch('internet_game_finder_fixed.app.LIBRARY_FILE', header_only_file):
        result = load_library()
        assert result == []


def test_csv_with_valid_data(tmp_path):
    # Создаём CSV с валидными данными
    valid_file = tmp_path / "valid.csv"
    valid_file.write_text(
        "name,platform,coop_players,has_pvp,year,genre,free2play,url
"
        "Test Game,PC,4,No,2020,Action,No,http://example.com/test
",
        encoding="utf-8"
    )
    
    with patch('internet_game_finder_fixed.app.LIBRARY_FILE', valid_file):
        result = load_library()
        assert len(result) == 1
        assert result[0]["name"] == "Test Game"
        assert result[0]["platform"] == "PC"


def test_csv_missing_required_columns(tmp_path):
    # Создаём CSV без обязательной колонки 'name'
    invalid_file = tmp_path / "invalid.csv"
    invalid_file.write_text(
        "platform,coop_players,has_pvp,year,genre,free2play,url
"
        "PC,4,No,2020,Action,No,http://example.com/test
",
        encoding="utf-8"
    )
    
    with patch('internet_game_finder_fixed.app.LIBRARY_FILE', invalid_file):
        result = load_library()
        assert result == []


def test_missing_load_csv_file(tmp_path):
    # Тестируем load_csv с отсутствующим файлом
    non_existent_file = tmp_path / "nonexistent.csv"
    result = load_csv(non_existent_file)
    assert result == []


def test_empty_load_csv_file(tmp_path):
    # Тестируем load_csv с пустым файлом
    empty_file = tmp_path / "empty.csv"
    empty_file.write_text("", encoding="utf-8")
    result = load_csv(empty_file)
    assert result == []


def test_valid_load_csv_file(tmp_path):
    # Тестируем load_csv с валидным файлом
    valid_file = tmp_path / "valid.csv"
    valid_file.write_text(
        "name,url
"
        "Test Game,http://example.com/test
",
        encoding="utf-8"
    )
    result = load_csv(valid_file)
    assert len(result) == 1
    assert result[0]["name"] == "Test Game"
    assert result[0]["url"] == "http://example.com/test"
