import pymysql.cursors


def obtener_conexion():
    return pymysql.connect(host='localhost',
                           port=3306,
                           user='root',
                           password='',
                           database='db_sistema_tickets_ti',
                           cursorclass=pymysql.cursors.DictCursor)