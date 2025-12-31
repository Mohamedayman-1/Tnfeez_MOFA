"""
WebSocket consumers for real-time notifications
Handles WebSocket connections for budget transfer notifications
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
import logging

logger = logging.getLogger("budget_management_websocket")


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications
    Each user gets their own notification channel
    """
    
    async def connect(self):
        """
        Called when WebSocket is establishing connection
        Adds user to their personal notification group
        """
        try:
            # Get user from scope (requires AuthMiddlewareStack)
            self.user = self.scope['user']
            
            if self.user.is_anonymous:
                # Reject anonymous users
                logger.warning(f"❌ Anonymous user tried to connect, rejecting")
                await self.close()
                return
            
            # Create group name based on user ID
            self.user_id = self.user.id
            self.group_name = f'notifications_{self.user_id}'
            
            logger.info(f"✅ User {self.user_id} connecting to group: {self.group_name}")
            
            # Add this channel to the user's notification group
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            
            # Accept the WebSocket connection
            await self.accept()
            
            logger.info(f"🟢 WebSocket CONNECTED for user {self.user_id}")
            
            # Send initial connection success message
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'WebSocket connected successfully',
                'user_id': self.user_id
            }))
        except Exception as e:
            logger.error(f"❌ ERROR in connect(): {e}", exc_info=True)
            await self.close()

    async def disconnect(self, close_code):
        """
        Called when WebSocket is closing connection
        Removes user from their notification group
        """
        logger.warning(f"🔴 WebSocket disconnecting - Close Code: {close_code}")
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
            logger.info(f"WebSocket disconnected for user {self.user_id}, close_code={close_code}")

    async def receive(self, text_data):
        """
        Called when message is received from WebSocket (client to server)
        Optional: Handle any client messages here
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'unknown')
            
            # Handle ping/pong for connection keepalive
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
            
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")

    # Custom event handlers - these are called from Celery tasks
    
    async def notification_message(self, event):
        """
        Handler for general notification messages
        Sends all notification fields as saved in the database, including Transaction_id if present.
        """
        try:
            logger.info(f"📨 notification_message received: {event}")
            # If event['data'] contains notification model fields, send them all
            notification_data = event.get('data', {})
            response = {
                'type': 'notification',
                'message': event.get('message', ''),
                'eng_message': event.get('eng_message', event.get('message', '')),
                'ara_message': event.get('ara_message', event.get('message', '')),
                'timestamp': event.get('timestamp', None),
            }
            # Add all notification fields if present (prefer top-level event)
            for key in [
                'id', 'user', 'ara_message', 'eng_message', 'is_read', 'created_at',
                'is_system_read', 'is_shown', 'type_of_Trasnction', 'Type_of_action', 'Transaction_id']:
                if key in event:
                    response[key] = event[key]
                elif key in notification_data:
                    response[key] = notification_data[key]
            # Also include all other fields in data
            for k, v in notification_data.items():
                if k not in response:
                    response[k] = v
            await self.send(text_data=json.dumps(response, default=str))
            logger.info(f"✅ notification_message sent successfully")
        except Exception as e:
            logger.error(f"❌ Error in notification_message: {e}", exc_info=True)
            logger.error(f"Event data was: {event}")
    
    async def oracle_upload_started(self, event):
        """
        Handler for Oracle upload started notification
        """
        try:
            logger.info(f"📨 oracle_upload_started received: {event}")
            await self.send(text_data=json.dumps({
                'type': 'oracle_upload_started',
                'transaction_id': event['transaction_id'],
                'message': event['message'],
                'eng_message': event.get('eng_message', event.get('message')),
                'ara_message': event.get('ara_message', event.get('message')),
                'timestamp': event.get('timestamp')
            }))
            logger.info(f"✅ oracle_upload_started sent successfully")
        except Exception as e:
            logger.error(f"❌ Error in oracle_upload_started: {e}", exc_info=True)
            logger.error(f"Event data was: {event}")
    
    async def oracle_upload_progress(self, event):
        """
        Handler for Oracle upload progress updates
        """
        try:
            logger.info(f"📨 oracle_upload_progress received: {event}")
            await self.send(text_data=json.dumps({
                'type': 'oracle_upload_progress',
                'transaction_id': event['transaction_id'],
                'step': event['step'],
                'step_number': event.get('step_number'),
                'total_steps': event.get('total_steps', 5),
                'message': event['message'],
                'eng_message': event.get('eng_message', event.get('message')),
                'ara_message': event.get('ara_message', event.get('message')),
                'status': event.get('status', 'processing'),
                'timestamp': event.get('timestamp')
            }))
            logger.info(f"✅ oracle_upload_progress sent successfully")
        except Exception as e:
            logger.error(f"❌ Error in oracle_upload_progress: {e}", exc_info=True)
            logger.error(f"Event data was: {event}")
    
    async def oracle_upload_completed(self, event):
        """
        Handler for Oracle upload completion notification
        """
        try:
            await self.send(text_data=json.dumps({
                'type': 'oracle_upload_completed',
                'transaction_id': event['transaction_id'],
                'message': event['message'],
                'eng_message': event.get('eng_message', event.get('message')),
                'ara_message': event.get('ara_message', event.get('message')),
                'success': event.get('success', True),
                'result_path': event.get('result_path'),
                'timestamp': event.get('timestamp')
            }))
        except Exception as e:
            logger.error(f"❌ Error in oracle_upload_completed: {e}", exc_info=True)
    
    async def oracle_upload_failed(self, event):
        """
        Handler for Oracle upload failure notification
        """
        try:
            await self.send(text_data=json.dumps({
                'type': 'oracle_upload_failed',
                'transaction_id': event['transaction_id'],
                'message': event['message'],
                'eng_message': event.get('eng_message', event.get('message')),
                'ara_message': event.get('ara_message', event.get('message')),
                'error': event.get('error'),
                'timestamp': event.get('timestamp')
            }))
        except Exception as e:
            logger.error(f"❌ Error in oracle_upload_failed: {e}", exc_info=True)
