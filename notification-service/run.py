from src.api.notification_service_webapi import app
import sys

if __name__ == '__main__':
    #app.run(debug=True)
    port = 8000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    app.run(host='0.0.0.0', port=port, debug=True)