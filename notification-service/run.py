from src.api import app

if __name__ == '__main__':
    #app.run(debug=True)
    app.run(host='0.0.0.0', port=8000, debug=True)