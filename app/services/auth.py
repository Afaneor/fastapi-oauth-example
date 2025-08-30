from urllib.parse import urlencode

import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from pydantic import BaseModel
from config import settings


# JWT настройки
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    id: str
    email: Optional[str] = None
    name: Optional[str] = None
    avatar: Optional[str] = None



def get_yandex_auth_url() -> str:
    """
    Генерация URL для авторизации в Яндекс.Паспорт

    В production добавь:
    - state parameter для защиты от CSRF атак
    - force_confirm=yes для повторного подтверждения
    - display=popup для popup авторизации
    """
    params = {
        "response_type": "code",
        "client_id": settings.yandex_client_id,
        "redirect_uri": settings.redirect_uri,
        # "scope": "chat.app.spaces",  # в яндексе они объявлены на уровне приложения, в гугле можно посмотреть тут https://developers.google.com/identity/protocols/oauth2/scopes
        # "state": generate_state(),  # Добавь в production!
    }

    # Формируем query string вручную для лучшего контроля
    query_params = urlencode(params)

    return f"{settings.yandex_oauth_url}?{query_params}"


async def exchange_code_for_token(code: str) -> Dict[str, Any]:
    """
    Обмен authorization code на access token

    Это критически важная функция - здесь происходит обмен
    кода на токен для доступа к API Яндекса
    """

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": settings.yandex_client_id,
        "client_secret": settings.yandex_client_secret,  # Никогда не логируй это!
        "redirect_uri": settings.redirect_uri,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "FastAPI-OAuth2-App/1.0"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                settings.yandex_token_url,
                data=data,
                headers=headers,
                timeout=10.0  # Timeout для production
            )

            # Логируем для отладки (убери client_secret!)
            print(f"Token request status: {response.status_code}")

            if response.status_code != 200:
                error_data = response.json() if response.headers.get(
                    "content-type") == "application/json" else {}
                print(f"Token error: {error_data}")

                raise HTTPException(
                    status_code=400,
                    detail=f"Ошибка получения токена: {error_data.get('error_description', 'Unknown error')}"
                )

            token_data = response.json()

            # Валидируем ответ
            if "access_token" not in token_data:
                raise HTTPException(
                    status_code=400,
                    detail="Некорректный ответ от сервера Яндекса"
                )

            return token_data

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=408,
                detail="Timeout при получении токена от Яндекса"
            )
        except httpx.RequestError as e:
            print(f"Request error: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Сервис Яндекс.OAuth временно недоступен"
            )


async def get_user_info(access_token: str) -> Dict[str, Any]:
    """
    Получение информации о пользователе через Яндекс API

    Используем полученный access_token для запроса данных пользователя
    """

    headers = {
        "Authorization": f"OAuth {access_token}",
        "User-Agent": "FastAPI-OAuth2-App/1.0"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                settings.yandex_api_base_url,
                headers=headers,
                timeout=10.0
            )

            if response.status_code != 200:
                print(
                    f"User info error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=400,
                    detail="Ошибка получения данных пользователя"
                )

            user_data = response.json()

            # Валидируем обязательные поля
            if "id" not in user_data:
                raise HTTPException(
                    status_code=400,
                    detail="Некорректные данные пользователя от Яндекса"
                )

            return user_data

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=408,
                detail="Timeout при получении данных пользователя"
            )
        except httpx.RequestError as e:
            print(f"User info request error: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Сервис Яндекс.API временно недоступен"
            )


# ============================================================================
# JWT FUNCTIONS
# ============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Создание JWT токена для нашего приложения

    После успешной OAuth2 авторизации создаем собственный JWT токен
    для дальнейшей работы с нашим API
    """

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Добавляем стандартные JWT claims
    to_encode.update({
        "exp": expire,  # Expiration time
        "iat": datetime.now(),  # Issued at
        "iss": "fastapi-oauth2-app"  # Issuer
    })

    # Кодируем токен
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)

    return encoded_jwt


def verify_token(token: str, credentials_exception):
    """Валидация JWT токена"""

    try:
        # Декодируем токен
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])

        # Получаем user_id из токена
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        # Проверяем expiration (jwt библиотека делает это автоматически)
        return payload

    except JWTError as e:
        print(f"JWT Error: {str(e)}")
        raise credentials_exception


async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Dependency для получения текущего пользователя

    Используй в защищенных endpoint'ах:
    @app.get("/protected")
    async def protected(user = Depends(get_current_user)):
        return {"user_id": user["sub"]}
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Недействительный токен авторизации",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Извлекаем токен из заголовка "Bearer <token>"
        access_token = token.credentials

        # Валидируем токен и получаем payload
        payload = verify_token(access_token, credentials_exception)

        return payload

    except Exception as e:
        print(f"Get current user error: {str(e)}")
        raise credentials_exception


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def generate_state() -> str:
    """
    Генерация state parameter для защиты от CSRF атак

    В production обязательно используй state parameter!
    """
    import secrets
    return secrets.token_urlsafe(32)


async def refresh_token(refresh_token: str) -> Dict[str, Any]:
    """
    Обновление access_token через refresh_token

    Яндекс поддерживает refresh токены, но для демо не реализуем
    В production это критически важно для длительных сессий
    """
    # TODO: Реализовать в production
    pass
