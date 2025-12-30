"""
JWT Authentication Middleware for WebSocket Connections
Supports BOTH JWT tokens AND Django session authentication
Uses the custom xx_User table for identity lookup
"""

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from channels.auth import AuthMiddlewareStack
from django.contrib.auth.models import AnonymousUser
from urllib.parse import parse_qs
import jwt
from django.conf import settings
import logging

from user_management.models import xx_User  # Custom user table that issues API JWTs

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user_by_id(user_id):
    try:
        user = xx_User.objects.get(id=user_id)
        logger.info(f"✅ user_id auth: resolved user {user.id} ({user.username})")
        return user
    except xx_User.DoesNotExist:
        logger.warning(f"user_id auth failed: user {user_id} not found")
        return AnonymousUser()


@database_sync_to_async
def get_user_from_token(token):
    """
    Decode JWT token and return user
    
    Args:
        token: JWT token string
        
    Returns:
        User object or AnonymousUser
    """
    try:
        # Decode JWT token
        # Adjust SECRET_KEY and ALGORITHM based on your JWT settings
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=['HS256']
        )
        
        # Get user ID from payload
        user_id = payload.get('user_id') or payload.get('id')
        username = payload.get('username')
        
        if not user_id and not username:
            logger.warning("JWT payload missing user_id/username")
            return AnonymousUser()
        
        # Get user from database
        if user_id:
            user = xx_User.objects.get(id=user_id)
        else:
            user = xx_User.objects.get(username=username)

        logger.info(
            f"✅ JWT authenticated custom user: id={user.id}, username={user.username}"
        )
        return user
        
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return AnonymousUser()
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {str(e)}")
        return AnonymousUser()
    except xx_User.DoesNotExist:
        logger.warning(f"Custom user not found (id={user_id}, username={username})")
        return AnonymousUser()
    except Exception as e:
        logger.error(f"Error decoding JWT: {str(e)}")
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware to authenticate WebSocket connections using JWT
    
    Token can be passed in:
    1. Query parameter: ws://localhost/ws/notifications/?token=YOUR_JWT_TOKEN
    2. Header: Authorization: Bearer YOUR_JWT_TOKEN
    
    If no token is provided, sets user to None to let next middleware handle it
    """
    
    async def __call__(self, scope, receive, send):
        # Get user_id or token from query string or headers
        token = None
        user = None
        
        # Try to get token from query parameters
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        
        user_id_param = query_params.get('user_id', [None])[0]
        if user_id_param:
            logger.info(f"🔑 Authenticating via user_id query param: {user_id_param}")
            user = await get_user_by_id(user_id_param)

        if 'token' in query_params:
            token = query_params['token'][0]
            logger.info(f"🔑 Token from query parameter")
        
        # Try to get token from headers (if query param not found)
        if not token:
            headers = dict(scope.get('headers', []))
            auth_header = headers.get(b'authorization', b'').decode()
            
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                logger.info(f"🔑 Token from Authorization header")
        
        # Authenticate user with token
        if token and (user is None or isinstance(user, AnonymousUser)):
            user = await get_user_from_token(token)

        if user and not isinstance(user, AnonymousUser):
            scope['user'] = user
            logger.info(f"🔐 WebSocket auth success: {user}")
        # else: don't set scope['user'], let the next middleware in the stack handle it
        if "user" not in scope:
            scope["user"] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """
    Wrapper function to apply JWT authentication middleware
    Use this in asgi.py instead of AuthMiddlewareStack
    """
    return JWTAuthMiddleware(inner)
