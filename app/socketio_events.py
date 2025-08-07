from flask_socketio import emit, join_room, leave_room, disconnect
from flask_login import current_user
from . import socketio, db
from .models import ChatMessage, ChatMention, Notification, UserOnlineStatus, User, MessageReaction
from datetime import datetime, timezone
import re

def extract_mentions(content):
    """Extract @mentions from message content."""
    mention_pattern = r'@(\w+)'
    mentions = re.findall(mention_pattern, content)
    return mentions

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    if current_user.is_authenticated:
        # Update user online status
        status = UserOnlineStatus.query.filter_by(user_id=current_user.id).first()
        if not status:
            status = UserOnlineStatus(user_id=current_user.id)
            db.session.add(status)
        
        status.is_online = True
        status.last_seen = datetime.now(timezone.utc)
        db.session.commit()
        
        # Join user to their personal room and general room
        join_room(f'user_{current_user.id}')
        join_room('general')
        
        # Emit user online event to all users
        emit('user_online', {
            'user_id': current_user.id,
            'username': current_user.username,
            'full_name': current_user.get_full_name()
        }, broadcast=True, include_self=False)
        
        print(f'User {current_user.username} connected')

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    if current_user.is_authenticated:
        # Update user online status
        status = UserOnlineStatus.query.filter_by(user_id=current_user.id).first()
        if status:
            status.is_online = False
            status.last_seen = datetime.now(timezone.utc)
            db.session.commit()
        
        # Emit user offline event to all users
        emit('user_offline', {
            'user_id': current_user.id,
            'username': current_user.username
        }, broadcast=True, include_self=False)
        
        print(f'User {current_user.username} disconnected')

@socketio.on('join_room')
def handle_join_room(data):
    """Handle joining a specific room."""
    if not current_user.is_authenticated:
        return
    
    room = data.get('room', 'general')
    join_room(room)
    emit('user_joined_room', {
        'user': current_user.username,
        'room': room
    }, room=room)

@socketio.on('leave_room')
def handle_leave_room(data):
    """Handle leaving a specific room."""
    if not current_user.is_authenticated:
        return
    
    room = data.get('room', 'general')
    leave_room(room)
    emit('user_left_room', {
        'user': current_user.username,
        'room': room
    }, room=room)

@socketio.on('send_message')
def handle_send_message(data):
    """Handle sending a chat message."""
    content = data.get('content', '').strip()
    room = data.get('room', 'general')
    
    if not content:
        emit('error', {'message': 'Message content is required'})
        return
    
    # Create the message
    message = ChatMessage(
        sender_id=current_user.id,
        content=content,
        room=room
    )
    db.session.add(message)
    db.session.commit()
    
    # Extract and process mentions
    mentions = extract_mentions(content)
    for username in mentions:
        user = User.query.filter_by(username=username).first()
        if user:
            mention = ChatMention(
                message_id=message.id,
                mentioned_user_id=user.id
            )
            db.session.add(mention)
            
            # Create notification for mentioned user
            if user.id != current_user.id:
                notification = Notification(
                    user_id=user.id,
                    type='mention',
                    title=f'You were mentioned by {current_user.get_full_name()}',
                    message=f'{current_user.get_full_name()} mentioned you in a message: "{content[:50]}{"..." if len(content) > 50 else ""}"',
                    related_id=message.id
                )
                db.session.add(notification)
                
                # Emit notification to mentioned user
                emit('new_notification', {
                    'id': notification.id,
                    'type': notification.type,
                    'title': notification.title,
                    'message': notification.message,
                    'created_at': notification.created_at.isoformat()
                }, room=f'user_{user.id}')
                
                # Emit mention event to mentioned user
                emit('user_mentioned', {
                    'mentioned_by': current_user.username,
                    'mentioned_by_name': current_user.get_full_name(),
                    'message_content': content,
                    'message_id': message.id,
                    'room': room
                }, room=f'user_{user.id}')
    
    db.session.commit()
    
    # Emit message to room
    emit('new_message', {
        'id': message.id,
        'sender_id': message.sender_id,
        'sender_name': current_user.get_full_name(),
        'content': message.content,
        'message_type': message.message_type,
        'file_url': message.file_url,
        'file_name': message.file_name,
        'file_size': message.file_size,
        'is_pinned': message.is_pinned,
        'created_at': message.created_at.isoformat(),
        'mentions': mentions,
        'read_by': []
    }, room=room)

@socketio.on('typing_start')
def handle_typing_start(data):
    """Handle typing start event."""
    if not current_user.is_authenticated:
        return
    
    room = data.get('room', 'general')
    emit('user_typing_start', {
        'user': current_user.username,
        'user_id': current_user.id
    }, room=room, include_self=False)

@socketio.on('typing_stop')
def handle_typing_stop(data):
    """Handle typing stop event."""
    if not current_user.is_authenticated:
        return
    
    room = data.get('room', 'general')
    emit('user_typing_stop', {
        'user': current_user.username,
        'user_id': current_user.id
    }, room=room, include_self=False)

@socketio.on('task_status_update')
def handle_task_status_update(data):
    """Handle task status updates."""
    if not current_user.is_authenticated:
        return
        
    task_id = data.get('task_id')
    new_status = data.get('status')
    
    if task_id and new_status:
        # Emit task update to all users
        emit('task_updated', {
            'task_id': task_id,
            'status': new_status,
            'updated_by': current_user.username,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }, broadcast=True)

@socketio.on('notification_read')
def handle_notification_read(data):
    """Handle notification read event."""
    if not current_user.is_authenticated:
        return
        
    notification_id = data.get('notification_id')
    
    if notification_id:
        notification = Notification.query.get(notification_id)
        if notification and notification.user_id == current_user.id:
            notification.is_read = True
            db.session.commit()
            
            emit('notification_marked_read', {
                'notification_id': notification_id
            }, room=f'user_{current_user.id}')

@socketio.on('request_online_users')
def handle_request_online_users():
    """Handle request for online users list."""
    online_users = UserOnlineStatus.query.filter_by(is_online=True).all()
    
    users_data = []
    for status in online_users:
        users_data.append({
            'user_id': status.user_id,
            'username': status.user.username,
            'full_name': status.user.get_full_name(),
            'last_seen': status.last_seen.isoformat()
        })
    
    emit('online_users_list', {'users': users_data})

@socketio.on('ping')
def handle_ping():
    """Handle ping to keep connection alive."""
    emit('pong')

@socketio.on('mark_message_read')
def handle_mark_message_read(data):
    """Handle marking a message as read."""
    if not current_user.is_authenticated:
        return
        
    message_id = data.get('message_id')
    room = data.get('room', 'general')
    
    if message_id:
        # Update message read status in database
        message = ChatMessage.query.get(message_id)
        if message:
            # Add read receipt
            read_receipt = MessageReadReceipt(
                message_id=message_id,
                read_by_id=current_user.id,
                read_at=datetime.now(timezone.utc)
            )
            db.session.add(read_receipt)
            db.session.commit()
            
            # Emit read receipt to room
            emit('message_read', {
                'message_id': message_id,
                'read_by': {
                    'user_id': current_user.id,
                    'full_name': current_user.get_full_name(),
                    'username': current_user.username
                },
                'read_at': read_receipt.read_at.isoformat()
            }, room=room)

@socketio.on('join_messenger')
def handle_join_messenger(data):
    """Handle joining the messenger room."""
    if not current_user.is_authenticated:
        return
        
    try:
        room = data.get('room', 'general')
        join_room(room)
        print(f"User {current_user.username} joined messenger room: {room}")
    except Exception as e:
        print(f"Error joining messenger room: {e}")

@socketio.on('user_typing_start')
def handle_user_typing_start(data):
    """Handle typing start indicator for messenger."""
    if not current_user.is_authenticated:
        return
        
    try:
        room = data.get('room', 'general')
        
        # Emit typing start to all users in the room except sender
        emit('user_typing_start', {
            'user_id': current_user.id,
            'user_name': current_user.get_full_name()
        }, room=room, include_self=False)
        
    except Exception as e:
        print(f"Error handling typing start: {e}")

@socketio.on('user_typing_stop')
def handle_user_typing_stop(data):
    """Handle typing stop indicator for messenger."""
    if not current_user.is_authenticated:
        return
        
    try:
        room = data.get('room', 'general')
        
        # Emit typing stop to all users in the room except sender
        emit('user_typing_stop', {
            'user_id': current_user.id
        }, room=room, include_self=False)
        
    except Exception as e:
        print(f"Error handling typing stop: {e}")

@socketio.on('add_reaction')
def handle_add_reaction(data):
    """Handle adding a reaction to a message."""
    if not current_user.is_authenticated:
        return
        
    try:
        message_id = data.get('message_id')
        reaction_type = data.get('reaction_type')
        
        if not message_id or not reaction_type:
            emit('error', {'message': 'Message ID and reaction type are required'})
            return
        
        # Check if message exists
        message = ChatMessage.query.get(message_id)
        if not message:
            emit('error', {'message': 'Message not found'})
            return
        
        # Check if user already has this reaction
        existing_reaction = MessageReaction.query.filter_by(
            message_id=message_id,
            user_id=current_user.id,
            reaction_type=reaction_type
        ).first()
        
        if existing_reaction:
            # Remove existing reaction (toggle off)
            db.session.delete(existing_reaction)
            db.session.commit()
            
            # Emit reaction removed event
            emit('reaction_removed', {
                'message_id': message_id,
                'reaction_type': reaction_type,
                'user_id': current_user.id,
                'user_name': current_user.get_full_name()
            }, room=message.room)
        else:
            # Add new reaction
            reaction = MessageReaction(
                message_id=message_id,
                user_id=current_user.id,
                reaction_type=reaction_type
            )
            db.session.add(reaction)
            db.session.commit()
            
            # Emit reaction added event
            emit('reaction_added', {
                'message_id': message_id,
                'reaction_type': reaction_type,
                'user_id': current_user.id,
                'user_name': current_user.get_full_name(),
                'reaction_id': reaction.id
            }, room=message.room)
        
    except Exception as e:
        print(f"Error handling reaction: {e}")
        emit('error', {'message': 'Failed to add reaction'})

@socketio.on('get_message_reactions')
def handle_get_message_reactions(data):
    """Handle getting reactions for a message."""
    try:
        message_id = data.get('message_id')
        
        if not message_id:
            emit('error', {'message': 'Message ID is required'})
            return
        
        # Get all reactions for this message
        reactions = MessageReaction.query.filter_by(message_id=message_id).all()
        
        # Group reactions by type
        reaction_counts = {}
        user_reactions = {}
        
        for reaction in reactions:
            reaction_type = reaction.reaction_type
            if reaction_type not in reaction_counts:
                reaction_counts[reaction_type] = []
            
            reaction_counts[reaction_type].append({
                'user_id': reaction.user_id,
                'user_name': reaction.user.get_full_name(),
                'created_at': reaction.created_at.isoformat()
            })
            
            # Track current user's reactions
            if reaction.user_id == current_user.id:
                user_reactions[reaction_type] = reaction.id
        
        emit('message_reactions', {
            'message_id': message_id,
            'reaction_counts': reaction_counts,
            'user_reactions': user_reactions
        })
        
    except Exception as e:
        print(f"Error getting reactions: {e}")
        emit('error', {'message': 'Failed to get reactions'})

@socketio.on('edit_message')
def handle_edit_message(data):
    """Handle editing a message."""
    try:
        message_id = data.get('message_id')
        new_content = data.get('content', '').strip()
        
        if not message_id or not new_content:
            emit('error', {'message': 'Message ID and content are required'})
            return
        
        # Get the message
        message = ChatMessage.query.get(message_id)
        if not message:
            emit('error', {'message': 'Message not found'})
            return
        
        # Check if user can edit this message
        if not message.can_edit(current_user.id):
            emit('error', {'message': 'You cannot edit this message'})
            return
        
        # Edit the message
        message.edit_message(new_content, current_user.id)
        db.session.commit()
        
        # Emit message edited event
        emit('message_edited', {
            'message_id': message_id,
            'content': message.content,
            'is_edited': message.is_edited,
            'edited_at': message.updated_at.isoformat(),
            'edited_by': current_user.get_full_name()
        }, room=message.room)
        
    except Exception as e:
        print(f"Error editing message: {e}")
        emit('error', {'message': 'Failed to edit message'})

@socketio.on('delete_message')
def handle_delete_message(data):
    """Handle deleting a message."""
    try:
        message_id = data.get('message_id')
        
        if not message_id:
            emit('error', {'message': 'Message ID is required'})
            return
        
        # Get the message
        message = ChatMessage.query.get(message_id)
        if not message:
            emit('error', {'message': 'Message not found'})
            return
        
        # Check if user can delete this message
        if not message.can_delete(current_user.id):
            emit('error', {'message': 'You cannot delete this message'})
            return
        
        # Soft delete the message
        message.soft_delete(current_user.id)
        db.session.commit()
        
        # Emit message deleted event
        emit('message_deleted', {
            'message_id': message_id,
            'deleted_by': current_user.get_full_name(),
            'deleted_at': message.deleted_at.isoformat()
        }, room=message.room)
        
    except Exception as e:
        print(f"Error deleting message: {e}")
        emit('error', {'message': 'Failed to delete message'})

@socketio.on('get_message_edit_history')
def handle_get_message_edit_history(data):
    """Handle getting edit history for a message."""
    try:
        message_id = data.get('message_id')
        
        if not message_id:
            emit('error', {'message': 'Message ID is required'})
            return
        
        # Get the message
        message = ChatMessage.query.get(message_id)
        if not message:
            emit('error', {'message': 'Message not found'})
            return
        
        # Get edit history
        edit_history = message.get_edit_history()
        
        emit('message_edit_history', {
            'message_id': message_id,
            'edit_history': edit_history,
            'is_edited': message.is_edited,
            'original_content': message.original_content
        })
        
    except Exception as e:
        print(f"Error getting edit history: {e}")
        emit('error', {'message': 'Failed to get edit history'})

# Threaded Replies Event Handlers
@socketio.on('send_thread_reply')
def handle_send_thread_reply(data):
    """Handle sending a reply in a thread."""
    try:
        content = data.get('content', '').strip()
        parent_message_id = data.get('parent_message_id')
        room = data.get('room', 'general')
        
        if not content:
            emit('error', {'message': 'Message content is required'})
            return
        
        if not parent_message_id:
            emit('error', {'message': 'Parent message ID is required'})
            return
        
        # Verify parent message exists
        parent_message = ChatMessage.query.get(parent_message_id)
        if not parent_message:
            emit('error', {'message': 'Parent message not found'})
            return
        
        # Create the reply message
        reply_message = ChatMessage(
            sender_id=current_user.id,
            content=content,
            room=room,
            parent_message_id=parent_message_id
        )
        db.session.add(reply_message)
        db.session.commit()
        
        # Extract and process mentions
        mentions = extract_mentions(content)
        for mention_username in mentions:
            mentioned_user = User.query.filter_by(username=mention_username).first()
            if mentioned_user:
                mention = ChatMention(
                    message_id=reply_message.id,
                    mentioned_user_id=mentioned_user.id
                )
                db.session.add(mention)
        
        db.session.commit()
        
        # Emit the reply to the room
        emit('thread_reply_sent', {
            'message_id': reply_message.id,
            'parent_message_id': parent_message_id,
            'sender_id': current_user.id,
            'sender_name': current_user.get_full_name(),
            'content': reply_message.content,
            'created_at': reply_message.created_at.isoformat(),
            'room': room
        }, room=room)
        
        # Send notifications to mentioned users
        for mention_username in mentions:
            mentioned_user = User.query.filter_by(username=mention_username).first()
            if mentioned_user and mentioned_user.id != current_user.id:
                notification = Notification(
                    user_id=mentioned_user.id,
                    type='mention',
                    title=f'You were mentioned by {current_user.get_full_name()}',
                    message=f'{current_user.get_full_name()} mentioned you in a thread reply: {content[:50]}...',
                    related_id=reply_message.id
                )
                db.session.add(notification)
        
        db.session.commit()
        
    except Exception as e:
        print(f"Error sending thread reply: {e}")
        emit('error', {'message': 'Failed to send thread reply'})

@socketio.on('get_thread_replies')
def handle_get_thread_replies(data):
    """Handle getting all replies in a thread."""
    try:
        parent_message_id = data.get('parent_message_id')
        
        if not parent_message_id:
            emit('error', {'message': 'Parent message ID is required'})
            return
        
        parent_message = ChatMessage.query.get(parent_message_id)
        if not parent_message:
            emit('error', {'message': 'Parent message not found'})
            return
        
        replies = parent_message.get_thread_replies()
        
        # Format replies for frontend
        formatted_replies = []
        for reply in replies:
            formatted_replies.append({
                'id': reply.id,
                'sender_id': reply.sender_id,
                'sender_name': reply.sender.get_full_name(),
                'content': reply.get_display_content(),
                'created_at': reply.created_at.isoformat(),
                'is_edited': reply.is_edited,
                'is_deleted': reply.is_deleted
            })
        
        emit('thread_replies_loaded', {
            'parent_message_id': parent_message_id,
            'replies': formatted_replies,
            'total_replies': len(formatted_replies)
        })
        
    except Exception as e:
        print(f"Error getting thread replies: {e}")
        emit('error', {'message': 'Failed to get thread replies'})

@socketio.on('pin_message')
def handle_pin_message(data):
    """Handle pinning/unpinning a message."""
    try:
        message_id = data.get('message_id')
        pin_action = data.get('action', 'pin')  # 'pin' or 'unpin'
        
        if not message_id:
            emit('error', {'message': 'Message ID is required'})
            return
        
        message = ChatMessage.query.get(message_id)
        if not message:
            emit('error', {'message': 'Message not found'})
            return
        
        # Toggle pin status
        if pin_action == 'pin':
            message.is_pinned = True
            action_text = 'pinned'
        else:
            message.is_pinned = False
            action_text = 'unpinned'
        
        db.session.commit()
        
        # Emit pin status change to the room
        emit('message_pin_status_changed', {
            'message_id': message_id,
            'is_pinned': message.is_pinned,
            'action': pin_action,
            'pinned_by': current_user.get_full_name()
        }, room=message.room)
        
        # Create notification for the message sender (if different from current user)
        if message.sender_id != current_user.id:
            notification = Notification(
                user_id=message.sender_id,
                type='message_pinned',
                title=f'Your message was {action_text}',
                message=f'{current_user.get_full_name()} {action_text} your message: {message.content[:50]}...',
                related_id=message.id
            )
            db.session.add(notification)
            db.session.commit()
            
    except Exception as e:
        print(f"Error pinning/unpinning message: {e}")
        emit('error', {'message': 'Failed to pin/unpin message'})

@socketio.on('get_pinned_messages')
def handle_get_pinned_messages(data):
    """Handle getting all pinned messages in a room."""
    try:
        room = data.get('room', 'general')
        
        pinned_messages = ChatMessage.query.filter_by(
            room=room, 
            is_pinned=True,
            is_deleted=False
        ).order_by(ChatMessage.created_at.desc()).all()
        
        # Format pinned messages for frontend
        formatted_messages = []
        for message in pinned_messages:
            formatted_messages.append({
                'id': message.id,
                'sender_id': message.sender_id,
                'sender_name': message.sender.get_full_name(),
                'content': message.get_display_content(),
                'created_at': message.created_at.isoformat(),
                'is_edited': message.is_edited,
                'pinned_at': message.updated_at.isoformat()
            })
        
        emit('pinned_messages_loaded', {
            'room': room,
            'messages': formatted_messages,
            'total_pinned': len(formatted_messages)
        })
        
    except Exception as e:
        print(f"Error getting pinned messages: {e}")
        emit('error', {'message': 'Failed to get pinned messages'}) 

# Group Management Socket Events
@socketio.on('join_group')
def handle_join_group(data):
    """Handle joining a group chat room."""
    group_id = data.get('group_id')
    if not group_id:
        emit('error', {'message': 'Group ID is required'})
        return
    
    # Check if user is member of the group
    from .models import ChatGroupMember
    member = ChatGroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not member:
        emit('error', {'message': 'You are not a member of this group'})
        return
    
    # Join the group room
    room = f'group_{group_id}'
    join_room(room)
    
    emit('user_joined_group', {
        'user_id': current_user.id,
        'username': current_user.username,
        'full_name': current_user.get_full_name(),
        'group_id': group_id
    }, room=room)
    
    print(f'User {current_user.username} joined group {group_id}')


@socketio.on('leave_group')
def handle_leave_group(data):
    """Handle leaving a group chat room."""
    group_id = data.get('group_id')
    if not group_id:
        emit('error', {'message': 'Group ID is required'})
        return
    
    room = f'group_{group_id}'
    leave_room(room)
    
    emit('user_left_group', {
        'user_id': current_user.id,
        'username': current_user.username,
        'group_id': group_id
    }, room=room)
    
    print(f'User {current_user.username} left group {group_id}')


@socketio.on('send_group_message')
def handle_send_group_message(data):
    """Handle sending a message to a group."""
    content = data.get('content', '').strip()
    group_id = data.get('group_id')
    
    if not content or not group_id:
        emit('error', {'message': 'Content and group ID are required'})
        return
    
    # Check if user is member of the group
    from .models import ChatGroupMember, ChatGroup
    member = ChatGroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not member:
        emit('error', {'message': 'You are not a member of this group'})
        return
    
    # Check if group allows messages
    group = ChatGroup.query.get(group_id)
    if not group or group.is_archived:
        emit('error', {'message': 'Group is not available'})
        return
    
    # Create the message
    message = ChatMessage(
        sender_id=current_user.id,
        content=content,
        room=f'group_{group_id}',
        group_id=group_id
    )
    db.session.add(message)
    db.session.commit()
    
    # Extract and process mentions
    mentions = extract_mentions(content)
    for username in mentions:
        user = User.query.filter_by(username=username).first()
        if user:
            mention = ChatMention(
                message_id=message.id,
                mentioned_user_id=user.id
            )
            db.session.add(mention)
    
    db.session.commit()
    
    # Prepare message data
    message_data = {
        'id': message.id,
        'sender_id': message.sender_id,
        'sender_name': current_user.get_full_name(),
        'content': message.content,
        'message_type': message.message_type,
        'file_url': message.file_url,
        'file_name': message.file_name,
        'file_size': message.file_size,
        'is_pinned': message.is_pinned,
        'created_at': message.created_at.isoformat(),
        'mentions': mentions,
        'group_id': group_id
    }
    
    # Emit to group room
    room = f'group_{group_id}'
    emit('new_group_message', message_data, room=room)
    
    # Send notifications to mentioned users
    for username in mentions:
        user = User.query.filter_by(username=username).first()
        if user and user.id != current_user.id:
            emit('user_mentioned', {
                'mentioned_by': current_user.get_full_name(),
                'message_content': content,
                'group_name': group.name,
                'group_id': group_id
            }, room=f'user_{user.id}')
    
    print(f'Group message sent to group {group_id}')


@socketio.on('group_typing_start')
def handle_group_typing_start(data):
    """Handle typing start in a group."""
    group_id = data.get('group_id')
    if not group_id:
        emit('error', {'message': 'Group ID is required'})
        return
    
    # Check if user is member of the group
    from .models import ChatGroupMember
    member = ChatGroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not member:
        emit('error', {'message': 'You are not a member of this group'})
        return
    
    room = f'group_{group_id}'
    emit('group_user_typing_start', {
        'user_id': current_user.id,
        'username': current_user.username,
        'full_name': current_user.get_full_name(),
        'group_id': group_id
    }, room=room, include_self=False)


@socketio.on('group_typing_stop')
def handle_group_typing_stop(data):
    """Handle typing stop in a group."""
    group_id = data.get('group_id')
    if not group_id:
        emit('error', {'message': 'Group ID is required'})
        return
    
    # Check if user is member of the group
    from .models import ChatGroupMember
    member = ChatGroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not member:
        emit('error', {'message': 'You are not a member of this group'})
        return
    
    room = f'group_{group_id}'
    emit('group_user_typing_stop', {
        'user_id': current_user.id,
        'username': current_user.username,
        'group_id': group_id
    }, room=room, include_self=False)


@socketio.on('group_member_joined')
def handle_group_member_joined(data):
    """Handle when a new member joins a group."""
    group_id = data.get('group_id')
    user_id = data.get('user_id')
    
    if not group_id or not user_id:
        emit('error', {'message': 'Group ID and user ID are required'})
        return
    
    # Check if current user is admin of the group
    from .models import ChatGroupMember
    admin_member = ChatGroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not admin_member or admin_member.role != 'admin':
        emit('error', {'message': 'Only admins can add members'})
        return
    
    # Get the new member
    user = User.query.get(user_id)
    if not user:
        emit('error', {'message': 'User not found'})
        return
    
    room = f'group_{group_id}'
    emit('group_member_joined', {
        'user_id': user_id,
        'username': user.username,
        'full_name': user.get_full_name(),
        'group_id': group_id,
        'added_by': current_user.get_full_name()
    }, room=room)
    
    print(f'User {user.username} joined group {group_id}')


@socketio.on('group_member_left')
def handle_group_member_left(data):
    """Handle when a member leaves a group."""
    group_id = data.get('group_id')
    user_id = data.get('user_id')
    
    if not group_id or not user_id:
        emit('error', {'message': 'Group ID and user ID are required'})
        return
    
    # Check if current user is admin or the leaving user
    from .models import ChatGroupMember
    admin_member = ChatGroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not (admin_member and admin_member.role == 'admin') and current_user.id != user_id:
        emit('error', {'message': 'Insufficient permissions'})
        return
    
    # Get the leaving member
    user = User.query.get(user_id)
    if not user:
        emit('error', {'message': 'User not found'})
        return
    
    room = f'group_{group_id}'
    emit('group_member_left', {
        'user_id': user_id,
        'username': user.username,
        'full_name': user.get_full_name(),
        'group_id': group_id,
        'removed_by': current_user.get_full_name()
    }, room=room)
    
    print(f'User {user.username} left group {group_id}')


@socketio.on('group_invitation_sent')
def handle_group_invitation_sent(data):
    """Handle when an invitation is sent to a group."""
    group_id = data.get('group_id')
    invited_user_id = data.get('invited_user_id')
    
    if not group_id or not invited_user_id:
        emit('error', {'message': 'Group ID and invited user ID are required'})
        return
    
    # Check if current user is admin of the group
    from .models import ChatGroupMember
    admin_member = ChatGroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not admin_member or admin_member.role != 'admin':
        emit('error', {'message': 'Only admins can send invitations'})
        return
    
    # Get the invited user
    user = User.query.get(invited_user_id)
    if not user:
        emit('error', {'message': 'User not found'})
        return
    
    # Get group info
    from .models import ChatGroup
    group = ChatGroup.query.get(group_id)
    if not group:
        emit('error', {'message': 'Group not found'})
        return
    
    # Notify the invited user
    emit('group_invitation_received', {
        'group_id': group_id,
        'group_name': group.name,
        'group_description': group.description,
        'invited_by': current_user.get_full_name(),
        'invited_by_id': current_user.id
    }, room=f'user_{invited_user_id}')
    
    print(f'Invitation sent to user {user.username} for group {group_id}')


@socketio.on('group_invitation_accepted')
def handle_group_invitation_accepted(data):
    """Handle when a group invitation is accepted."""
    group_id = data.get('group_id')
    user_id = data.get('user_id')
    
    if not group_id or not user_id:
        emit('error', {'message': 'Group ID and user ID are required'})
        return
    
    # Check if current user is the one accepting
    if current_user.id != user_id:
        emit('error', {'message': 'Unauthorized'})
        return
    
    # Get group info
    from .models import ChatGroup
    group = ChatGroup.query.get(group_id)
    if not group:
        emit('error', {'message': 'Group not found'})
        return
    
    room = f'group_{group_id}'
    emit('group_invitation_accepted', {
        'user_id': user_id,
        'username': current_user.username,
        'full_name': current_user.get_full_name(),
        'group_id': group_id,
        'group_name': group.name
    }, room=room)
    
    print(f'User {current_user.username} accepted invitation to group {group_id}')


@socketio.on('group_invitation_declined')
def handle_group_invitation_declined(data):
    """Handle when a group invitation is declined."""
    group_id = data.get('group_id')
    user_id = data.get('user_id')
    
    if not group_id or not user_id:
        emit('error', {'message': 'Group ID and user ID are required'})
        return
    
    # Check if current user is the one declining
    if current_user.id != user_id:
        emit('error', {'message': 'Unauthorized'})
        return
    
    # Get group info
    from .models import ChatGroup
    group = ChatGroup.query.get(group_id)
    if not group:
        emit('error', {'message': 'Group not found'})
        return
    
    # Notify group admins
    from .models import ChatGroupMember
    admin_members = ChatGroupMember.query.filter_by(
        group_id=group_id,
        role='admin',
        is_active=True
    ).all()
    
    for admin in admin_members:
        emit('group_invitation_declined', {
            'user_id': user_id,
            'username': current_user.username,
            'full_name': current_user.get_full_name(),
            'group_id': group_id,
            'group_name': group.name
        }, room=f'user_{admin.user_id}')
    
    print(f'User {current_user.username} declined invitation to group {group_id}')


@socketio.on('group_updated')
def handle_group_updated(data):
    """Handle when group information is updated."""
    group_id = data.get('group_id')
    
    if not group_id:
        emit('error', {'message': 'Group ID is required'})
        return
    
    # Check if current user is admin of the group
    from .models import ChatGroupMember
    admin_member = ChatGroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not admin_member or admin_member.role != 'admin':
        emit('error', {'message': 'Only admins can update group information'})
        return
    
    # Get group info
    from .models import ChatGroup
    group = ChatGroup.query.get(group_id)
    if not group:
        emit('error', {'message': 'Group not found'})
        return
    
    room = f'group_{group_id}'
    emit('group_updated', {
        'group_id': group_id,
        'name': group.name,
        'description': group.description,
        'is_public': group.is_public,
        'allow_guest_messages': group.allow_guest_messages,
        'is_archived': group.is_archived,
        'updated_by': current_user.get_full_name()
    }, room=room)
    
    print(f'Group {group_id} updated by {current_user.username}')


@socketio.on('group_member_role_updated')
def handle_group_member_role_updated(data):
    """Handle when a member's role is updated."""
    group_id = data.get('group_id')
    user_id = data.get('user_id')
    new_role = data.get('role')
    
    if not group_id or not user_id or not new_role:
        emit('error', {'message': 'Group ID, user ID, and role are required'})
        return
    
    # Check if current user is admin of the group
    from .models import ChatGroupMember
    admin_member = ChatGroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not admin_member or admin_member.role != 'admin':
        emit('error', {'message': 'Only admins can update member roles'})
        return
    
    # Get the member to update
    member = ChatGroupMember.query.filter_by(
        group_id=group_id,
        user_id=user_id,
        is_active=True
    ).first()
    
    if not member:
        emit('error', {'message': 'Member not found'})
        return
    
    # Get user info
    user = User.query.get(user_id)
    if not user:
        emit('error', {'message': 'User not found'})
        return
    
    room = f'group_{group_id}'
    emit('group_member_role_updated', {
        'user_id': user_id,
        'username': user.username,
        'full_name': user.get_full_name(),
        'group_id': group_id,
        'old_role': member.role,
        'new_role': new_role,
        'updated_by': current_user.get_full_name()
    }, room=room)
    
    print(f'User {user.username} role updated to {new_role} in group {group_id}')


@socketio.on('group_muted')
def handle_group_muted(data):
    """Handle when a group is muted/unmuted by a member."""
    group_id = data.get('group_id')
    is_muted = data.get('is_muted', True)
    
    if not group_id:
        emit('error', {'message': 'Group ID is required'})
        return
    
    # Check if current user is member of the group
    from .models import ChatGroupMember
    member = ChatGroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not member:
        emit('error', {'message': 'You are not a member of this group'})
        return
    
    action = 'muted' if is_muted else 'unmuted'
    print(f'User {current_user.username} {action} group {group_id}')


@socketio.on('group_reported')
def handle_group_reported(data):
    """Handle when a group is reported."""
    group_id = data.get('group_id')
    report_type = data.get('report_type')
    description = data.get('description')
    
    if not group_id or not report_type or not description:
        emit('error', {'message': 'Group ID, report type, and description are required'})
        return
    
    # Check if current user is member of the group
    from .models import ChatGroupMember
    member = ChatGroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not member:
        emit('error', {'message': 'You are not a member of this group'})
        return
    
    # Get group info
    from .models import ChatGroup
    group = ChatGroup.query.get(group_id)
    if not group:
        emit('error', {'message': 'Group not found'})
        return
    
    print(f'Group {group_id} reported by {current_user.username} for {report_type}') 