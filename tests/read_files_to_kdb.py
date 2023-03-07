# we use qpython to connect to a local instance of kdb+ and send queries to it


import qpython


def main():
    q = qpython.qconnection.QConnection(host='localhost', port=5000, pandas=True)
    with q:
        q.send()