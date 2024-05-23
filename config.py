from datetime import timedelta

DIALECT = 'mysql'
DRIVER = 'pymysql'
USERNAME = 'root'
PASSWORD = 'Ttangtao123~'
HOST = '127.0.0.1'
PORT = '3306'
DATABASE = 'ray'
SQLALCHEMY_DATABASE_URI = "{}+{}://{}:{}@{}:{}/{}?charset=utf8".format(DIALECT, DRIVER, USERNAME, PASSWORD, HOST, PORT,
                                                                       DATABASE)
JWT_TOKEN_LOCATION = ["cookies"]
JWT_COOKIE_SECURE = False
JWT_SECRET_KEY = 'wjl'
JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
