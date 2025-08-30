from fastapi import APIRouter

from services.auth import get_yandex_auth_url, exchange_code_for_token, \
    get_user_info, create_access_token, get_current_user

example_router = APIRouter()

from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

@example_router.get("/", response_class=HTMLResponse)
async def home():
    """Главная страница с кнопкой авторизации"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FastAPI OAuth2 Demo</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 800px; 
                margin: 50px auto; 
                padding: 20px;
                text-align: center;
            }
            .auth-btn {
                background: #ffcc00;
                border: none;
                padding: 15px 30px;
                font-size: 18px;
                border-radius: 5px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                color: black;
            }
            .auth-btn:hover { background: #e6b800; }
            .profile { 
                background: #f0f0f0; 
                padding: 20px; 
                border-radius: 10px; 
                margin: 20px 0;
            }
        </style>
    </head>
    <body>
        <h1>🚀 FastAPI + Яндекс OAuth2</h1>
        <p>Демонстрация авторизации через Яндекс.Паспорт</p>

        <a href="/auth/login" class="auth-btn">
            🔐 Войти через Яндекс
        </a>

        <div style="margin-top: 40px;">
            <h3>📋 Что происходит:</h3>
            <ol style="text-align: left; max-width: 500px; margin: 0 auto;">
                <li>Нажимаешь кнопку</li>
                <li>Перенаправление на Яндекс</li>
                <li>Авторизация в Яндекс.Паспорт</li>
                <li>Возврат с кодом авторизации</li>
                <li>Обмен кода на токен</li>
                <li>Получение данных пользователя</li>
                <li>Создание JWT токена</li>
            </ol>
        </div>
    </body>
    </html>
    """


@example_router.get("/profile", response_class=HTMLResponse)
async def profile_page():
    """
    Страница профиля с реальными данными пользователя

    Использует JavaScript для получения данных через API
    с JWT токеном из cookie
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Профиль - FastAPI OAuth2</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 800px; 
                margin: 50px auto; 
                padding: 20px;
            }
            .profile { 
                background: #e8f5e8; 
                padding: 20px; 
                border-radius: 10px; 
                border-left: 4px solid #4CAF50;
            }
            .user-info {
                background: white;
                padding: 15px;
                border-radius: 8px;
                margin: 15px 0;
                border: 1px solid #ddd;
            }
            .avatar {
                width: 64px;
                height: 64px;
                border-radius: 50%;
                margin-right: 15px;
                float: left;
            }
            .user-details {
                overflow: hidden;
                padding-left: 10px;
            }
            .loading {
                color: #666;
                font-style: italic;
            }
            .error {
                color: #ff4444;
                background: #ffe6e6;
                padding: 10px;
                border-radius: 5px;
                border: 1px solid #ffcccc;
            }
            .logout-btn {
                background: #ff4444;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
            }
            .api-btn {
                background: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                margin-left: 10px;
            }
            .token-info {
                background: #f0f8ff;
                padding: 10px;
                border-radius: 5px;
                font-family: monospace;
                font-size: 12px;
                margin: 10px 0;
                word-break: break-all;
            }
        </style>
    </head>
    <body>
        <h1>✅ Добро пожаловать!</h1>

        <div class="profile">
            <h3>👤 Данные пользователя</h3>

            <!-- Здесь будут загружены данные пользователя -->
            <div id="user-data" class="loading">
                🔄 Загрузка данных пользователя...
            </div>

            <!-- JWT токен информация -->
            <div style="margin-top: 20px;">
                <h4>🔐 JWT Токен</h4>
                <div id="token-info" class="token-info">
                    Загрузка токена...
                </div>
            </div>
        </div>

        <div style="margin-top: 30px;">
            <a href="/" class="logout-btn">← Вернуться на главную</a>
            <button onclick="refreshData()" class="api-btn">🔄 Обновить данные</button>
            <button onclick="testProtectedRoute()" class="api-btn">🔒 Тест защищенного API</button>
        </div>

        <!-- Результат тестирования API -->
        <div id="api-test-result" style="margin-top: 20px;"></div>

        <script>
            // Функция для получения JWT токена из cookie
            function getTokenFromCookie() {
                const cookies = document.cookie.split(';');
                for (let cookie of cookies) {
                    const [name, value] = cookie.trim().split('=');
                    if (name === 'jwt_token') {
                        return value;
                    }
                }
                return null;
            }

            // Функция для парсинга JWT токена (только для демо!)
            function parseJWT(token) {
                try {
                    const base64Url = token.split('.')[1];
                    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
                    const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function(c) {
                        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                    }).join(''));
                    return JSON.parse(jsonPayload);
                } catch (e) {
                    return null;
                }
            }

            // Функция для загрузки данных пользователя
            async function loadUserData() {
                const token = getTokenFromCookie();
                const userDataDiv = document.getElementById('user-data');
                const tokenInfoDiv = document.getElementById('token-info');

                if (!token) {
                    userDataDiv.innerHTML = `
                        <div class="error">
                            ❌ JWT токен не найден в cookies.<br>
                            Возможно, истекло время сессии. 
                            <a href="/auth/login">Войдите заново</a>
                        </div>
                    `;
                    return;
                }

                // Показываем информацию о токене
                const tokenPayload = parseJWT(token);
                if (tokenPayload) {
                    const expDate = new Date(tokenPayload.exp * 1000);
                    tokenInfoDiv.innerHTML = `
                        <strong>Токен валиден до:</strong> ${expDate.toLocaleString()}<br>
                        <strong>Выдан:</strong> ${tokenPayload.iss}<br>
                    `;
                }

                try {
                    // Делаем запрос к защищенному API
                    const response = await fetch('/auth/me', {
                        method: 'GET',
                        headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                        }
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }

                    const data = await response.json();
                    const user = data.user;

                    // Формируем аватар URL для Яндекса
                    const avatarUrl = user.avatar ? 
                        `https://avatars.yandex.net/get-yapic/${user.avatar}/islands-68` : 
                        'https://avatars.yandex.net/get-yapic/0/0-0/islands-68';

                    // Отображаем данные пользователя
                    userDataDiv.innerHTML = `
                        <div class="user-info">
                            <img src="${avatarUrl}" alt="Аватар" class="avatar" onerror="this.src='https://via.placeholder.com/64x64/cccccc/666666?text=👤'">
                            <div class="user-details">
                                <h4>${user.name || 'Имя не указано'}</h4>
                                <p><strong>📧 Email:</strong> ${user.email || 'Не предоставлен'}</p>
                                <p><strong>🕒 Авторизован:</strong> ${new Date().toLocaleString()}</p>
                            </div>
                            <div style="clear: both;"></div>
                        </div>

                        <div style="margin-top: 15px; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                            <strong>✅ OAuth2 Flow завершен успешно!</strong><br>
                            <small>Данные получены от Яндекс API и обработаны FastAPI сервером</small>
                        </div>
                    `;

                } catch (error) {
                    console.error('Ошибка загрузки данных:', error);
                    userDataDiv.innerHTML = `
                        <div class="error">
                            ❌ Ошибка загрузки данных: ${error.message}<br>
                            <small>Проверьте консоль браузера для деталей</small>
                        </div>
                    `;
                }
            }

            // Функция обновления данных
            async function refreshData() {
                document.getElementById('user-data').innerHTML = '<div class="loading">🔄 Обновление...</div>';
                await loadUserData();
            }

            // Тестирование защищенного маршрута
            async function testProtectedRoute() {
                const token = getTokenFromCookie();
                const resultDiv = document.getElementById('api-test-result');

                if (!token) {
                    resultDiv.innerHTML = '<div class="error">Токен не найден</div>';
                    return;
                }

                try {
                    const response = await fetch('/protected', {
                        method: 'GET',
                        headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                        }
                    });

                    const data = await response.json();

                    resultDiv.innerHTML = `
                        <div style="background: #e8f5e8; padding: 15px; border-radius: 5px; margin-top: 10px;">
                            <h4>🔒 Тест защищенного API</h4>
                            <pre style="background: white; padding: 10px; border-radius: 3px; overflow-x: auto;">${JSON.stringify(data, null, 2)}</pre>
                        </div>
                    `;
                } catch (error) {
                    resultDiv.innerHTML = `<div class="error">Ошибка: ${error.message}</div>`;
                }
            }

            // Загружаем данные при загрузке страницы
            window.addEventListener('load', loadUserData);
        </script>
    </body>
    </html>
    """


# ============================================================================
# OAUTH2 ENDPOINTS
# ============================================================================

@example_router.get("/auth/login")
async def login():
    """
    Начало OAuth2 flow - перенаправление на Яндекс

    В production добавь:
    - State parameter для защиты от CSRF
    - Запоминание redirect_url для возврата пользователя
    """
    auth_url = get_yandex_auth_url()
    return RedirectResponse(url=auth_url)


@example_router.get("/auth/callback")
async def auth_callback(request: Request, code: str = None, error: str = None):
    """
    Callback endpoint - сюда Яндекс возвращает код авторизации

    URL должен точно совпадать с настройками в Яндекс.OAuth!
    """

    # Обработка ошибок от Яндекса
    if error:
        error_descriptions = {
            "access_denied": "Пользователь отклонил запрос на авторизацию",
            "invalid_request": "Некорректный запрос к серверу авторизации",
            "unauthorized_client": "Клиент не авторизован для данного типа запроса",
            "unsupported_response_type": "Неподдерживаемый тип ответа",
            "invalid_scope": "Некорректная область доступа",
            "server_error": "Внутренняя ошибка сервера авторизации",
            "temporarily_unavailable": "Сервер авторизации временно недоступен"
        }

        error_msg = error_descriptions.get(error,
                                           f"Неизвестная ошибка: {error}")

        # В production логируй ошибки
        print(f"OAuth Error: {error} - {error_msg}")

        raise HTTPException(
            status_code=400,
            detail=f"Ошибка авторизации: {error_msg}"
        )

    if not code:
        raise HTTPException(
            status_code=400,
            detail="Код авторизации не получен"
        )

    try:
        # Обмениваем код на токен
        token_data = await exchange_code_for_token(code)

        # Получаем данные пользователя
        user_info = await get_user_info(token_data["access_token"])

        # Создаем JWT токен для нашего приложения
        jwt_token = create_access_token(data={
            "sub": user_info["id"],
            "email": user_info.get("default_email"),
            "name": user_info.get("real_name", user_info.get("display_name")),
            "avatar": user_info.get("default_avatar_id")
        })

        # В production используй secure cookies или отправь токен на фронтенд
        response = RedirectResponse(url="/profile")

        response.set_cookie(key="jwt_token", value=jwt_token)
        return response

    except Exception as e:
        # В production используй proper logging
        print(f"OAuth callback error: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail="Ошибка при обработке авторизации"
        )


# ============================================================================
# PROTECTED ENDPOINTS
# ============================================================================

@example_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Получение данных текущего пользователя
    Требует валидный JWT токен в заголовке Authorization: Bearer <token>
    """
    return {
        "user": current_user,
        "message": "Данные получены успешно"
    }


@example_router.get("/protected")
async def protected_route(current_user: dict = Depends(get_current_user)):
    """Пример защищенного endpoint"""
    return {
        "message": f"Привет, {current_user.get('name', 'пользователь')}!",
        "access_level": "authorized"
    }
