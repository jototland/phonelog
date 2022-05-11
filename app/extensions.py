from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect

socketio = SocketIO()
csrf = CSRFProtect()
