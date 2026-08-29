import pytest
from unittest.mock import patch, MagicMock
from internet_game_finder_fixed.fetcher import get_html, extract_games


@patch('internet_game_finder_fixed.fetcher.requests.get')
def test_successful_html_fetch(mock_get):
    # Мокнируем успешный ответ
    mock_response = MagicMock()
    mock_response.text = "<html><a href='/allgames/1-test.html'>Test Game</a></html>"
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response
    
    html = get_html("http://example.com")
    assert html is not None
    assert "Test Game" in html


@patch('internet_game_finder_fixed.fetcher.requests.get')
def test_timeout_fetch(mock_get):
    # Мокнируем таймаут
    mock_get.side_effect = Timeout("Timeout error")
    
    html = get_html("http://example.com")
    assert html is None


@patch('internet_game_finder_fixed.fetcher.requests.get')
def test_http_error_fetch(mock_get):
    # Мокнируем HTTP-ошибку 404
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")
    mock_get.return_value = mock_response
    
    html = get_html("http://example.com")
    assert html is None


@patch('internet_game_finder_fixed.fetcher.requests.get')
def test_temporary_http_error_retry(mock_get):
    # Мокнируем временную ошибку 500 (должен быть retry)
    mock_response_500 = MagicMock()
    mock_response_500.status_code = 500
    mock_response_500.raise_for_status.side_effect = HTTPError("500 Server Error")
    
    mock_response_success = MagicMock()
    mock_response_success.text = "<html><a href='/allgames/1-test.html'>Test Game</a></html>"
    mock_response_success.raise_for_status = MagicMock()
    
    # Первые 2 вызова — ошибка 500, третий — успех
    mock_get.side_effect = [HTTPError("500 Server Error"), HTTPError("500 Server Error"), mock_response_success]
    
    html = get_html("http://example.com")
    assert html is not None
    assert "Test Game" in html


@patch('internet_game_finder_fixed.fetcher.requests.get')
def test_empty_html(mock_get):
    # Мокнируем пустой HTML
    mock_response = MagicMock()
    mock_response.text = "<html></html>"
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response
    
    games = extract_games("http://example.com")
    assert games == []


@patch('internet_game_finder_fixed.fetcher.requests.get')
def test_no_expected_elements(mock_get):
    # Мокнируем HTML без ожидаемых элементов
    mock_response = MagicMock()
    mock_response.text = "<html><div>No games here</div></html>"
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response
    
    games = extract_games("http://example.com")
    assert games == []
